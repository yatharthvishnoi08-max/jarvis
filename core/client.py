import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class ModelConfigurationError(ValueError):
    pass


def model_name() -> str:
    return os.getenv("MODEL_NAME", "nousresearch/hermes-3-llama-3.1-70b").strip()


def get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1").strip()
    
    if not api_key:
        raise ModelConfigurationError(
            "\n[!] MISSING API KEY:\n"
            f"Please open '{BASE_DIR / '.env'}' and set your OPENROUTER_API_KEY.\n"
            "You can generate an OpenRouter key at: https://openrouter.ai/keys\n"
            "Or if you want to use local Ollama, set API_BASE_URL=http://localhost:11434/v1 and set any dummy key."
        )
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "https://github.com/nousresearch/hermes",
            "X-Title": "Personal-JARVIS"
        }
    )
    return client, model_name()
