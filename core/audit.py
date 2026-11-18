import json
import time
from pathlib import Path
from typing import Dict, Any, List
from core.auth import redact_secrets

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_FILE = BASE_DIR / "memory" / "audit.jsonl"
AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

class AuditLogger:
    def __init__(self, log_path: Path = AUDIT_FILE):
        self.log_path = log_path

    def log_event(
        self,
        event_type: str,
        session_id: str = "global",
        action: str = "",
        tool: str = "",
        args: Any = None,
        policy: str = "INFO",
        status: str = "SUCCESS",
        detail: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Logs an event into audit history with redacted secrets."""
        entry = {
            "timestamp": int(time.time()),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "session_id": session_id,
            "action": action,
            "tool": tool,
            "args": args if isinstance(args, (dict, list, str, int, float, bool)) else str(args),
            "policy": policy,
            "status": status,
            "detail": redact_secrets(detail),
            **kwargs
        }

        # Clean args of secrets
        if isinstance(entry["args"], dict):
            entry["args"] = {k: redact_secrets(str(v)) for k, v in entry["args"].items()}
        elif isinstance(entry["args"], str):
            entry["args"] = redact_secrets(entry["args"])

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[Audit Log Error]: {e}")

        return entry

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads the latest N audit events."""
        if not self.log_path.exists():
            return []
        try:
            lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
            events = []
            for line in reversed(lines[-limit:]):
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
            return events
        except Exception as e:
            print(f"[Audit Read Error]: {e}")
            return []

audit_logger = AuditLogger()
