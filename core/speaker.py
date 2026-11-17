import os
import re
import time
import json
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Audio cache folder
AUDIO_CACHE = BASE_DIR / "audio_cache"
AUDIO_CACHE.mkdir(exist_ok=True)

# Default to George (British, classy butler tone) or Adam
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

def clean_text_for_speech(text: str) -> str:
    """Strips markdown code blocks, URLs, and formatting so speech sounds natural."""
    # Remove code blocks ```...```
    text = re.sub(r"```[\s\S]*?```", " [code block omitted] ", text)
    # Remove inline code `...`
    text = re.sub(r"`[^`]*`", "", text)
    # Remove markdown links [title](url) -> title
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove standalone URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove markdown headers and list bullets
    text = re.sub(r"[#*_~>]+", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

class ElevenLabsSpeaker:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip()
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5").strip()
        self.enabled = bool(self.api_key)
        self._pygame_initialized = False

    def _init_audio(self):
        if not self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.init()
                self._pygame_initialized = True
            except Exception as e:
                print(f"[Warning] Failed to initialize audio mixer: {e}")

    def speak(self, text: str):
        """Converts text to speech using ElevenLabs and plays it."""
        # Refresh key in case user added it while running
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not self.api_key:
            return

        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text:
            return

        # Cap length for voice output if excessively long (e.g. max 600 chars)
        if len(cleaned_text) > 800:
            cleaned_text = cleaned_text[:800] + "... and more detailed in the console."

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": cleaned_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.85
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            output_file = AUDIO_CACHE / "latest_speech.mp3"
            with urllib.request.urlopen(req, timeout=20) as resp:
                audio_bytes = resp.read()
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)

            self._play_audio(output_file)

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            print(f"\n[ElevenLabs Error {e.code}]: {err_msg}")
        except Exception as e:
            print(f"\n[Voice Error]: {e}")

    def _play_audio(self, file_path: Path):
        """Plays the audio file using pygame."""
        try:
            import pygame
            self._init_audio()
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print(f"[Audio Playback Error]: {e}")
