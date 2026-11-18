"""
High-Fidelity Voice Listener Module for JARVIS.
Supports:
1. Wispr Flow Voice Interface (Cloud API via WISPR_FLOW_API_KEY)
2. Local Neural Whisper (via faster-whisper base.en — 100% free, offline, zero API keys required)
3. Ring-buffer Voice Activity Detection (VAD) with 500ms pre-roll to prevent cutting off the start of speech.
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
        self.api_key = (
            api_key or
            os.getenv("WISPR_FLOW_API_KEY") or
            os.getenv("WISPR_API_KEY") or
            os.getenv("FLOW_API_KEY") or ""
        ).strip()
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
                    text = data.get("text") or data.get("transcription") or ""
                    return text.strip() if text else None
                elif resp.status_code == 401:
                    print(f"[Wispr Flow Error]: Authentication failed (HTTP 401). Check WISPR_FLOW_API_KEY.")
                    return None
            except Exception:
                continue

        return None


class LocalWhisperTranscriber:
    """Local, offline neural Whisper transcription using faster-whisper (0 API keys required)."""

    def __init__(self, model_size: str = "base.en"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                # int8 quantization on CPU for low latency and high accuracy
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception as e:
                print(f"[Local Whisper Load Error]: {e}")
        return self._model

    def transcribe_audio_array(self, audio_float: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        model = self._get_model()
        if model is None:
            return None
        try:
            segments, info = model.transcribe(audio_float, beam_size=1)
            text = " ".join(s.text for s in segments).strip()
            return text if text else None
        except Exception as e:
            print(f"[Local Whisper Error]: {e}")
            return None

    def transcribe_wav(self, wav_bytes: bytes) -> Optional[str]:
        try:
            sr, data = wav.read(io.BytesIO(wav_bytes))
            if data.dtype == np.int16:
                audio = data.astype(np.float32) / 32768.0
            else:
                audio = data.astype(np.float32)
            return self.transcribe_audio_array(audio, sample_rate=sr)
        except Exception:
            return None


class VoiceListener:
    """
    Intelligent Audio Capture and Voice Activity Detection (VAD) system.
    Automatically routes audio to Wispr Flow (if key configured) or Local Neural Whisper (zero key required).
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.chunk_duration = 0.1  # 100ms chunks
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        
        # Audio Ring Buffer: 500ms pre-roll to prevent cutting off the first word
        self.pre_roll_chunks = 5
        self.pre_roll_buffer: deque[np.ndarray] = deque(maxlen=self.pre_roll_chunks)

        # Transcribers
        self.wispr_engine = WisprFlowTranscriber()
        if self.wispr_engine.is_configured():
            self.wispr_engine.warmup()

        self.local_whisper = LocalWhisperTranscriber(model_size="base.en")

    @property
    def engine_name(self) -> str:
        """Returns the active speech recognition engine name."""
        load_dotenv(BASE_DIR / ".env", override=False)
        self.wispr_engine.api_key = (
            os.getenv("WISPR_FLOW_API_KEY") or
            os.getenv("WISPR_API_KEY") or
            os.getenv("FLOW_API_KEY") or ""
        ).strip()
        
        if self.wispr_engine.is_configured():
            return "Wispr Flow (Cloud API)"
        return "Local Neural Whisper (Offline, Free, High-Accuracy)"

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
        - Transcribes with Local Whisper or Wispr Flow.
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

        # Assemble audio into float32 array and 16-bit PCM WAV
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

        # 1. Primary Cloud: Wispr Flow (if key configured)
        if self.wispr_engine.is_configured():
            text = self.wispr_engine.transcribe(wav_bytes)
            if text:
                return text

        # 2. Local Neural Whisper (0 API keys required, completely offline)
        local_text = self.local_whisper.transcribe_audio_array(full_audio, sample_rate=self.sample_rate)
        if local_text:
            return local_text

        # 3. Fallback: SpeechRecognition
        return self._fallback_transcribe(wav_bytes)

    def transcribe_wav(self, wav_bytes: bytes) -> Optional[str]:
        """
        Transcribes WAV bytes using Wispr Flow (if key configured),
        Local Whisper (zero keys needed), or fallback.
        """
        load_dotenv(BASE_DIR / ".env", override=False)
        self.wispr_engine.api_key = (
            os.getenv("WISPR_FLOW_API_KEY") or
            os.getenv("WISPR_API_KEY") or
            os.getenv("FLOW_API_KEY") or ""
        ).strip()

        # 1. Wispr Flow REST API
        if self.wispr_engine.is_configured():
            text = self.wispr_engine.transcribe(wav_bytes)
            if text:
                return text

        # 2. Local Neural Whisper
        local_text = self.local_whisper.transcribe_wav(wav_bytes)
        if local_text:
            return local_text

        # 3. Fallback: SpeechRecognition
        return self._fallback_transcribe(wav_bytes)

    def _fallback_transcribe(self, wav_bytes: bytes) -> Optional[str]:
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                    return text.strip() if text else None
        except Exception:
            return None
