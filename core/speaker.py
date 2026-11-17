import os
import re
import time
import json
import uuid
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

AUDIO_CACHE = BASE_DIR / "audio_cache"
AUDIO_CACHE.mkdir(exist_ok=True)
INDEX_FILE = AUDIO_CACHE / "index.json"

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George (British Butler)

POPULAR_VOICES = [
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "description": "Classy British Butler (Classic JARVIS)"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "description": "Deep & Grounded (American)"},
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "Calm, Professional Female Assistant"},
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "description": "Casual Australian / Conversational"}
]

def clean_text_for_speech(text: str) -> str:
    """Strips markdown code blocks, URLs, and formatting so speech sounds natural."""
    if not text:
        return ""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", " [code block omitted] ", text)
    # Remove inline code
    text = re.sub(r"`[^`]*`", "", text)
    # Remove markdown links [title](url) -> title
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove markdown symbols
    text = re.sub(r"[#*_~>]+", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

class ElevenLabsSpeaker:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip()
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5").strip()
        self._pygame_initialized = False
        self._index: Dict[str, Any] = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        if INDEX_FILE.exists():
            try:
                return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_index(self):
        try:
            INDEX_FILE.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Audio Index Save Error]: {e}")

    def cleanup_cache(self, max_files: int = 50):
        """Purges old audio files when cache exceeds max_files."""
        try:
            mp3_files = sorted(AUDIO_CACHE.glob("*.mp3"), key=lambda f: f.stat().st_mtime)
            if len(mp3_files) > max_files:
                for f in mp3_files[:-max_files]:
                    try:
                        f.unlink()
                        if f.stem in self._index:
                            del self._index[f.stem]
                    except Exception:
                        pass
                self._save_index()
        except Exception as e:
            print(f"[Audio Cleanup Error]: {e}")

    def set_voice(self, voice_id: str):
        """Changes the active voice ID."""
        self.voice_id = voice_id.strip()

    def get_voices(self) -> List[Dict[str, Any]]:
        """Returns standard voices and marks active voice."""
        voices = []
        for v in POPULAR_VOICES:
            voices.append({
                **v,
                "is_active": (v["id"] == self.voice_id)
            })
        return voices

    def generate_speech(
        self,
        text: str,
        session_id: str = "global",
        message_id: str = "msg"
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesizes text using ElevenLabs and caches it with a unique audio_id.
        Returns audio metadata dict or None.
        """
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not self.api_key:
            return None

        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text:
            return None

        # Truncate length for audio generation
        if len(cleaned_text) > 800:
            cleaned_text = cleaned_text[:800] + "... and more detailed in the console."

        audio_id = f"aud_{uuid.uuid4().hex[:12]}"
        output_file = AUDIO_CACHE / f"{audio_id}.mp3"

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

            with urllib.request.urlopen(req, timeout=25) as resp:
                audio_bytes = resp.read()
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)

            # Register in index
            meta = {
                "audio_id": audio_id,
                "file_path": str(output_file),
                "session_id": session_id,
                "message_id": message_id,
                "voice_id": self.voice_id,
                "created_at": int(time.time()),
                "text_snippet": cleaned_text[:60]
            }
            self._index[audio_id] = meta
            self._save_index()
            self.cleanup_cache()

            # Also maintain legacy latest_speech.mp3 for backward compatibility
            try:
                legacy_file = AUDIO_CACHE / "latest_speech.mp3"
                with open(legacy_file, "wb") as f:
                    f.write(audio_bytes)
            except Exception:
                pass

            return meta

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            print(f"[ElevenLabs HTTP Error {e.code}]: {err_msg}")
            return None
        except Exception as e:
            print(f"[ElevenLabs Synthesis Error]: {e}")
            return None

    def get_audio_path(self, audio_id: str) -> Optional[Path]:
        """Returns the Path to an audio file by ID."""
        file_path = AUDIO_CACHE / f"{audio_id}.mp3"
        if file_path.exists():
            return file_path
        if audio_id == "latest":
            latest = AUDIO_CACHE / "latest_speech.mp3"
            if latest.exists():
                return latest
        return None

    def speak(self, text: str):
        """Legacy local audio playback using pygame (used by run_handsfree.bat)."""
        meta = self.generate_speech(text)
        if meta and meta.get("file_path"):
            try:
                import pygame
                if not self._pygame_initialized:
                    pygame.mixer.init()
                    self._pygame_initialized = True
                pygame.mixer.music.load(meta["file_path"])
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            except Exception as e:
                print(f"[Pygame Playback Error]: {e}")
