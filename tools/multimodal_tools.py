"""
J.A.R.V.I.S. Multimodal & Vision Perception Tools.
Enables visual understanding, screen perception, and image analysis powered by Gemini Vision.
"""

import os
import io
import time
import base64
from pathlib import Path
from typing import Optional
from PIL import Image, ImageGrab
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SCREENSHOTS_DIR = BASE_DIR / "memory" / "screenshots"

def _get_vision_client():
    """Retrieves client configured for Gemini Vision with automatic failover."""
    try:
        from core.client import get_client
        return get_client()
    except Exception:
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured in .env")
        base_url = os.getenv("API_BASE_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/openai/"
        model = os.getenv("MODEL_NAME", "").strip() or "gemini-3.5-flash-lite"
        client = OpenAI(api_key=gemini_key, base_url=base_url)
        return client, model

def analyze_image(image_path: str, prompt: str = "Analyze this image and describe key details, text, and elements.") -> str:
    """
    Analyzes any local image file (PNG, JPG, WebP) using Gemini Vision.
    Can extract text, describe UI diagrams, debug visual screenshots, and analyze documents.
    """
    try:
        path = Path(image_path).resolve()
        if not path.exists() or not path.is_file():
            return f"ERROR: Image file not found at '{image_path}'."

        with open(path, "rb") as f:
            encoded_bytes = base64.b64encode(f.read()).decode("utf-8")

        # Determine MIME type
        ext = path.suffix.lower()
        mime_type = "image/png"
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".webp":
            mime_type = "image/webp"

        client, model = _get_vision_client()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_bytes}"}}
                    ]
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR analyzing image with Gemini Vision: {str(e)}"

def _ensure_input_desktop():
    """Attaches the current Windows thread to the active user desktop station if on Windows."""
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hDesk = user32.OpenInputDesktop(0, False, 0x1ff)
            if hDesk:
                user32.SetThreadDesktop(hDesk)
        except Exception:
            pass

def capture_screen(save_path: Optional[str] = None) -> str:
    """
    Captures a high-resolution screenshot of the host's primary monitor display.
    Saves the image to the memory/screenshots folder or a specified custom path.
    """
    try:
        _ensure_input_desktop()
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        target_path = Path(save_path) if save_path else SCREENSHOTS_DIR / f"screen_{int(time.time())}.png"
        target_path.parent.mkdir(parents=True, exist_ok=True)

        screenshot = ImageGrab.grab()
        screenshot.save(target_path, format="PNG")
        return f"SUCCESS: Screen captured and saved to '{target_path}' (Resolution: {screenshot.width}x{screenshot.height})."
    except Exception as e:
        return f"ERROR capturing screen: {str(e)}. (Note: Ensure the host display is active and not locked)."

def analyze_screen(prompt: str = "Describe what is currently visible on the screen, identify any errors, active windows, and notable elements.") -> str:
    """
    Captures the live user screen and instantly analyzes it using Gemini Vision.
    Allows JARVIS to see what the user is working on, diagnose software errors, and provide context-aware visual assistance.
    """
    try:
        _ensure_input_desktop()
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = SCREENSHOTS_DIR / f"live_capture_{int(time.time())}.png"

        try:
            screenshot = ImageGrab.grab()
            screenshot.save(temp_path, format="PNG")
        except Exception as e:
            return f"ERROR capturing live screen: {str(e)}"

        # Run vision analysis on the captured screen
        analysis = analyze_image(str(temp_path), prompt=prompt)
        return f"Live Screen Analysis (Captured at {time.strftime('%H:%M:%S')}):\n\n{analysis}"
    except Exception as e:
        return f"ERROR during screen perception: {str(e)}"
