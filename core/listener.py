"""
High-Fidelity Voice Listener Module for JARVIS.
Integrates Wispr Flow (https://platform-api.wisprflow.ai) as the primary neural
speech-to-text engine with auto-editing, punctuation, and dictionary context,
backed by robust energy-based ring-buffer Voice Activity Detection (VAD).
"""

from __future__ import annotations

import os
import io
import time
import base64
import json
from collections import deque
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

AUDIO_CACHE = BASE_DIR / "audio_cache"
AUDIO_CACHE.mkdir(exist_ok=True)

# Primary Wispr Flow API Endpoints
WISPR_FLOW_ENDPOINTS = [
    "https://platform-api.wisprflow.ai/api/v1/dash/api",
    "https://api.flowvoice.ai/api/v1/dash/api"
]
WISPR_FLOW_WARMUP = "https://platform-api.wisprflow.ai/api/v1/dash/warmup_dash"


class WisprFlowTranscriber:
    """Official Wispr Flow REST API client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("WISPR_FLOW_API_KEY") or os.getenv("WISPR_API_KEY") or os.getenv("FLOW_API_KEY") or "").strip()
        self._warmed = False

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def warmup(self):
        """Pre-warm connection pool to eliminate cold-start latency."""
        if not self._warmed and self.is_configured():
            try:
                with httpx.Client(timeout=3.0) as client:
                    client.get(WISPR_FLOW_WARMUP)
                self._warmed = True
            except Exception:
                pass

    def transcribe(self, wav_bytes: bytes, language: str = "en") -> Optional[str]:
        """
        Transcribes 16kHz mono WAV audio using Wispr Flow Voice Interface.
        Returns cleaned, punctuated text with filler words removed.
        """
        if not self.is_configured():
            return None

        audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        payload = {
            "audio": audio_b64,
            "language": [language],
            "context": {
                "app": {
                    "name": "JARVIS",
                    "type": "ai"
                },
                "dictionary_context": [
                    "JARVIS", "Iron Man", "OpenRouter", "Hermes",
                    "ElevenLabs", "Tailscale", "PowerShell", "FastAPI"
                ],
                "textbox_contents": {
                    "before_text": "",
                    "after_text": ""
                }
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for endpoint in WISPR_FLOW_ENDPOINTS:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    # Wispr Flow returns {"id": ..., "text": ..., "detected_language": ...}
                    text = data.get("text") or data.get("transcription") or ""
                    return text.strip() if text else None
                elif resp.status_code == 401:
                    print(f"[Wispr Flow Error]: Authentication failed (HTTP 401). Check WISPR_FLOW_API_KEY.")
                    return None
                else:
                    print(f"[Wispr Flow Warning]: Endpoint {endpoint} returned HTTP {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                continue

        return None


class VoiceListener:
    """
    Intelligent Audio Capture and Voice Activity Detection (VAD) system.
    Feeds high-fidelity 16kHz audio into Wispr Flow, with fallback support.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.chunk_duration = 0.1  # 100ms chunks
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        
        # Audio Ring Buffer: 500ms pre-roll to prevent cutting off the first word
        self.pre_roll_chunks = 5
        self.pre_roll_buffer: deque[np.ndarray] = deque(maxlen=self.pre_roll_chunks)

        # Wispr Flow engine
        self.wispr_engine = WisprFlowTranscriber()
        if self.wispr_engine.is_configured():
            self.wispr_engine.warmup()

    @property
    def engine_name(self) -> str:
        """Returns the active speech recognition engine name."""
        # Reload env in case user updated .env at runtime
        load_dotenv(BASE_DIR / ".env", override=False)
        self.wispr_engine.api_key = (
            os.getenv("WISPR_FLOW_API_KEY") or
            os.getenv("WISPR_API_KEY") or
            os.getenv("FLOW_API_KEY") or ""
        ).strip()
        
        if self.wispr_engine.is_configured():
            return "Wispr Flow"
        return "Google Speech (Fallback — set WISPR_FLOW_API_KEY in .env)"

    def listen(
        self,
        silence_limit: float = 1.8,
        max_duration: float = 30.0,
        status_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Captures microphone input using energy-based ring-buffer VAD.
        - Preserves sentence start via 500ms pre-roll.
        - Dynamically tracks noise floor without blocking speech onset.
        - Transcribes with Wispr Flow.
        """
        self.pre_roll_buffer.clear()
        recorded_chunks: List[np.ndarray] = []
        is_speaking = False
        speech_onset_chunks = 0
        silence_start: Optional[float] = None
        start_time = time.time()

        # Dynamic noise floor estimation
        noise_floor = 0.012
        recent_energies: deque[float] = deque(maxlen=15)

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
                while True:
                    elapsed = time.time() - start_time
                    if not is_speaking and elapsed > 15.0:
                        # 15s timeout if no speech at all
                        return None
                    if is_speaking and elapsed > max_duration:
                        # Maximum utterance length reached
                        break

                    chunk, _ = stream.read(self.chunk_samples)
                    rms = float(np.sqrt(np.mean(chunk**2)))

                    # Update noise floor during quiet periods
                    if not is_speaking:
                        recent_energies.append(rms)
                        if len(recent_energies) >= 5:
                            # 20th percentile as estimated background floor
                            noise_floor = max(float(np.percentile(recent_energies, 20)), 0.008)

                    speech_threshold = max(noise_floor * 2.2, 0.016)

                    if rms > speech_threshold:
                        speech_onset_chunks += 1
                        silence_start = None

                        # Require at least 2 consecutive above-threshold chunks (200ms) to trigger voice
                        if not is_speaking and speech_onset_chunks >= 2:
                            is_speaking = True
                            if status_callback:
                                status_callback("recording")
                            # Flush pre-roll buffer to include the start of the first word
                            recorded_chunks.extend(list(self.pre_roll_buffer))

                        if is_speaking:
                            recorded_chunks.append(chunk)
                    else:
                        speech_onset_chunks = 0
                        if is_speaking:
                            recorded_chunks.append(chunk)
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= silence_limit:
                                # User finished speaking
                                break
                        else:
                            # Keep sliding pre-roll
                            self.pre_roll_buffer.append(chunk)

        except Exception as e:
            print(f"[Mic Capture Error]: {e}")
            return None

        # Minimum speech requirement (at least 4 chunks = 400ms) to ignore random pops
        if not recorded_chunks or len(recorded_chunks) < 4:
            return None

        # Assemble audio into 16-bit PCM WAV
        full_audio = np.concatenate(recorded_chunks, axis=0)
        int16_audio = np.clip(full_audio * 32767.0, -32768, 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wav.write(wav_buffer, self.sample_rate, int16_audio)
        wav_bytes = wav_buffer.getvalue()

        # Cache last recording for debugging/auditing
        try:
            temp_wav = AUDIO_CACHE / "user_input.wav"
            temp_wav.write_bytes(wav_bytes)
        except Exception:
            pass

        if status_callback:
            status_callback("transcribing")

        return self.transcribe_wav(wav_bytes)

    def transcribe_wav(self, wav_bytes: bytes) -> Optional[str]:
        """
        Transcribes WAV bytes using Wispr Flow, falling back seamlessly if unconfigured.
        """
        # Reload env in case key was added
        load_dotenv(BASE_DIR / ".env", override=False)
        self.wispr_engine.api_key = (
            os.getenv("WISPR_FLOW_API_KEY") or
            os.getenv("WISPR_API_KEY") or
            os.getenv("FLOW_API_KEY") or ""
        ).strip()

        # 1. Primary: Wispr Flow REST API
        if self.wispr_engine.is_configured():
            text = self.wispr_engine.transcribe(wav_bytes)
            if text:
                return text

        # 2. Secondary: wisprflow_sdk (local desktop client session if active)
        try:
            import wisprflow_sdk
            # Write temporary WAV for SDK
            temp_wav = AUDIO_CACHE / "wispr_tmp.wav"
            temp_wav.write_bytes(wav_bytes)
            client = wisprflow_sdk.WisprClient()
            res = client.transcribe(str(temp_wav))
            if res and hasattr(res, "final") and res.final:
                try:
                    temp_wav.unlink()
                except Exception:
                    pass
                return res.final.strip()
        except Exception:
            pass

        # 3. Fallback: SpeechRecognition (Google Free Engine)
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                    return text.strip() if text else None
        except Exception as e:
            return None
