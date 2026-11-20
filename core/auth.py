import os
import re
import secrets
import time
from typing import Optional, Set
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Ensure an owner token exists in environment or generate one
def get_or_create_owner_token() -> str:
    token = os.getenv("JARVIS_AUTH_TOKEN", "").strip()
    if not token:
        token = secrets.token_hex(24)
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            if "JARVIS_AUTH_TOKEN=" in content:
                content = re.sub(r"JARVIS_AUTH_TOKEN=.*", f"JARVIS_AUTH_TOKEN={token}", content)
            else:
                content += f"\n# Owner Authentication Token\nJARVIS_AUTH_TOKEN={token}\n"
            env_file.write_text(content, encoding="utf-8")
        os.environ["JARVIS_AUTH_TOKEN"] = token
    return token

OWNER_TOKEN = get_or_create_owner_token()

# Known secret patterns and environment secrets to redact
def get_secrets_to_redact() -> Set[str]:
    secrets_set = set()
    for key, val in os.environ.items():
        if any(term in key.upper() for term in ["KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH"]):
            v = val.strip()
            if len(v) >= 6:
                secrets_set.add(v)
    return secrets_set

def redact_secrets(text: str) -> str:
    """Replaces any occurrence of environment keys, tokens, and standard API key patterns with [REDACTED]."""
    if not text or not isinstance(text, str):
        return text

    # Redact registered secret values
    for secret in get_secrets_to_redact():
        if secret in text:
            text = text.replace(secret, "[REDACTED_SECRET]")

    # Redact common credential patterns (sk-or-v1-..., sk_..., Bearer tokens)
    text = re.sub(r"sk-or-v1-[a-zA-Z0-9]{32,}", "[REDACTED_OPENROUTER_KEY]", text)
    text = re.sub(r"sk_[a-zA-Z0-9]{24,}", "[REDACTED_API_KEY]", text)
    text = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer [REDACTED_TOKEN]", text)
    return text

def is_auth_required() -> bool:
    """Returns False if authentication is disabled (local/personal mode)."""
    val = os.getenv("REQUIRE_AUTH", "false").strip().lower()
    return val in ("true", "1", "yes", "on")

def verify_token(provided_token: Optional[str]) -> bool:
    """Constant-time token verification to prevent timing attacks."""
    current_token = os.getenv("JARVIS_AUTH_TOKEN", OWNER_TOKEN).strip()
    if not provided_token or not current_token:
        return False
    return secrets.compare_digest(provided_token.strip(), current_token)

# Simple sliding window rate limiter
class RateLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = {}  # ip -> list of timestamps

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        timestamps = self.clients.get(client_id, [])
        # Expire old timestamps
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        if len(valid_timestamps) >= self.max_requests:
            self.clients[client_id] = valid_timestamps
            return False
        valid_timestamps.append(now)
        self.clients[client_id] = valid_timestamps
        return True

global_rate_limiter = RateLimiter(max_requests=180, window_seconds=60)
