"""
J.A.R.V.I.S. Multi-Provider Intelligent Brain Engine.
Seamlessly unifies Google Gemini (primary) and OpenRouter (backup)
with zero-downtime automatic failover, vision perception, and tool-calling support.
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger("JARVIS.Brain")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_DEFAULT_FALLBACKS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]

OPENROUTER_DEFAULT_FALLBACKS = [
    "meta-llama/llama-3.3-70b-instruct",
    "nousresearch/hermes-3-llama-3.1-70b",
]

class SmartChatCompletions:
    """Wrapper around chat completions that handles transparent multi-model and multi-provider failover."""
    def __init__(
        self,
        primary_client: OpenAI,
        default_model: str,
        fallback_models: List[str],
        backup_client: Optional[OpenAI] = None,
        backup_model: Optional[str] = None
    ):
        self._primary_client = primary_client
        self.default_model = default_model
        self.fallback_models = fallback_models
        self._backup_client = backup_client
        self.backup_model = backup_model or "meta-llama/llama-3.3-70b-instruct"

    def create(self, *args, **kwargs) -> Any:
        requested_model = kwargs.get("model", self.default_model)
        models_to_try = [requested_model] + [m for m in self.fallback_models if m != requested_model]

        last_error = None
        # 1. Try primary models
        for model_name in models_to_try:
            try:
                call_kwargs = dict(kwargs)
                call_kwargs["model"] = model_name
                return self._primary_client.chat.completions.create(*args, **call_kwargs)
            except Exception as e:
                err_str = str(e)
                # Catch 503 (demand spike), 404 (model unavailable), 429 (free tier quota limit)
                if any(code in err_str for code in ["503", "404", "429", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                    logger.warning(
                        f"[Brain Failover]: Model '{model_name}' rate-limited or busy: {err_str[:60]}... Trying candidate."
                    )
                    last_error = e
                    continue
                raise

        # 2. If all primary candidates hit quota/availability limits and backup client is available, failover to backup provider
        if self._backup_client and self.backup_model:
            try:
                logger.warning(
                    f"[Brain Failover]: All primary models exhausted. Failing over to backup provider ({self.backup_model})."
                )
                backup_kwargs = dict(kwargs)
                backup_kwargs["model"] = self.backup_model
                # Clean any extra_content that non-Gemini providers might reject
                if "messages" in backup_kwargs:
                    clean_msgs = []
                    for m in backup_kwargs["messages"]:
                        m_copy = dict(m)
                        if "tool_calls" in m_copy and isinstance(m_copy["tool_calls"], list):
                            clean_tcs = []
                            for tc in m_copy["tool_calls"]:
                                if isinstance(tc, dict):
                                    clean_tc = {k: v for k, v in tc.items() if k != "extra_content"}
                                    clean_tcs.append(clean_tc)
                                else:
                                    clean_tcs.append(tc)
                            m_copy["tool_calls"] = clean_tcs
                        clean_msgs.append(m_copy)
                    backup_kwargs["messages"] = clean_msgs

                return self._backup_client.chat.completions.create(*args, **backup_kwargs)
            except Exception as backup_err:
                logger.error(f"[Brain Backup Error]: {backup_err}")
                raise last_error or backup_err

        if last_error:
            raise last_error

class SmartChat:
    def __init__(
        self,
        primary_client: OpenAI,
        default_model: str,
        fallback_models: List[str],
        backup_client: Optional[OpenAI] = None,
        backup_model: Optional[str] = None
    ):
        self.completions = SmartChatCompletions(
            primary_client,
            default_model,
            fallback_models,
            backup_client,
            backup_model
        )

class SmartLLMClient:
    """Transparent proxy for OpenAI client with multi-provider failover."""
    def __init__(
        self,
        primary_client: OpenAI,
        default_model: str,
        fallback_models: List[str],
        backup_client: Optional[OpenAI] = None,
        backup_model: Optional[str] = None
    ):
        self._primary_client = primary_client
        self.chat = SmartChat(
            primary_client,
            default_model,
            fallback_models,
            backup_client,
            backup_model
        )
        self.default_model = default_model
        self.fallback_models = fallback_models
        self.backup_model = backup_model

    def __getattr__(self, name: str) -> Any:
        return getattr(self._primary_client, name)

def get_active_provider() -> str:
    """Returns 'gemini', 'openrouter', or 'custom'."""
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        return "openrouter"
    return "custom"

def get_client() -> Tuple[SmartLLMClient, str]:
    """
    Initializes and returns the configured LLM client and primary model name.
    Automatically configures Google Gemini with OpenRouter backup.
    """
    provider = get_active_provider()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if provider == "gemini":
        if not gemini_key:
            raise ValueError(
                "\n[!] MISSING GEMINI API KEY:\n"
                f"Please open '{BASE_DIR / '.env'}' and set GEMINI_API_KEY."
            )

        base_url = os.getenv("API_BASE_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/openai/"
        model_name = os.getenv("MODEL_NAME", "").strip() or "gemini-flash-latest"
        fallback_models = [m for m in GEMINI_DEFAULT_FALLBACKS if m != model_name]

        primary_client = OpenAI(api_key=gemini_key, base_url=base_url, timeout=20.0)

        # Setup backup OpenRouter client if key is available
        backup_client = None
        backup_model = None
        if openrouter_key:
            backup_client = OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/open-jarvis",
                    "X-Title": "Personal-JARVIS"
                }
            )
            backup_model = "meta-llama/llama-3.3-70b-instruct"

        client = SmartLLMClient(
            primary_client,
            default_model=model_name,
            fallback_models=fallback_models,
            backup_client=backup_client,
            backup_model=backup_model
        )
        return client, model_name

    elif provider == "openrouter":
        if not openrouter_key:
            raise ValueError(
                "\n[!] MISSING OPENROUTER API KEY:\n"
                f"Please open '{BASE_DIR / '.env'}' and set OPENROUTER_API_KEY."
            )

        base_url = os.getenv("API_BASE_URL", "").strip() or "https://openrouter.ai/api/v1"
        model_name = os.getenv("MODEL_NAME", "").strip() or "meta-llama/llama-3.3-70b-instruct"
        fallback_models = [m for m in OPENROUTER_DEFAULT_FALLBACKS if m != model_name]

        primary_client = OpenAI(
            api_key=openrouter_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/open-jarvis",
                "X-Title": "Personal-JARVIS"
            }
        )
        client = SmartLLMClient(primary_client, default_model=model_name, fallback_models=fallback_models)
        return client, model_name

    else:
        # Custom or Ollama
        api_key = openrouter_key or gemini_key or "dummy-key"
        base_url = os.getenv("API_BASE_URL", "http://localhost:11434/v1")
        model_name = os.getenv("MODEL_NAME", "llama3")
        raw_client = OpenAI(api_key=api_key, base_url=base_url)
        client = SmartLLMClient(raw_client, default_model=model_name, fallback_models=[])
        return client, model_name
