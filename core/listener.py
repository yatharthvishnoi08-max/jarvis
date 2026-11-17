import time
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import speech_recognition as sr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_CACHE = BASE_DIR / "audio_cache"
AUDIO_CACHE.mkdir(exist_ok=True)

class VoiceListener:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()
        self.chunk_duration = 0.1  # 100ms chunks
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.ambient_threshold = 0.015

    def calibrate_ambient_noise(self, duration: float = 0.8):
        """Measures background noise level to dynamically set sensitivity."""
        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            rms = np.sqrt(np.mean(recording**2))
            # Set threshold above ambient noise, with a sensible floor
            self.ambient_threshold = max(float(rms * 1.8), 0.015)
        except Exception:
            self.ambient_threshold = 0.02

    def listen(self, silence_limit: float = 1.3, max_duration: float = 20.0) -> str | None:
        """
        Listens to microphone with automatic voice-activity detection.
        Starts recording when user speaks, stops after silence_limit seconds of silence.
        Returns transcribed text or None.
        """
        self.calibrate_ambient_noise()

        recorded_chunks = []
        is_speaking = False
        silence_start = None
        start_time = time.time()

        # Open input stream
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
                while True:
                    # Timeout if user doesn't say anything for 15s
                    elapsed = time.time() - start_time
                    if not is_speaking and elapsed > 15.0:
                        return None
                    if is_speaking and elapsed > max_duration:
                        break

                    chunk, _ = stream.read(self.chunk_samples)
                    rms = np.sqrt(np.mean(chunk**2))

                    if rms > self.ambient_threshold:
                        # Voice detected
                        if not is_speaking:
                            is_speaking = True
                        recorded_chunks.append(chunk)
                        silence_start = None
                    else:
                        # Silence detected
                        if is_speaking:
                            recorded_chunks.append(chunk)
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= silence_limit:
                                # User stopped speaking
                                break

        except Exception as e:
            print(f"[Mic Error]: {e}")
            return None

        if not recorded_chunks:
            return None

        # Concatenate audio chunks
        full_audio = np.concatenate(recorded_chunks, axis=0)

        # Convert float32 [-1.0, 1.0] to int16 for WAV
        int16_audio = (full_audio * 32767).astype(np.int16)
        temp_wav = AUDIO_CACHE / "user_input.wav"
        wav.write(str(temp_wav), self.sample_rate, int16_audio)

        # Transcribe with SpeechRecognition (Google Free Engine)
        try:
            with sr.AudioFile(str(temp_wav)) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                return text.strip()
        except sr.UnknownValueError:
            return None  # Inaudible / unintelligible
        except sr.RequestError as e:
            print(f"[Transcription API Error]: {e}")
            return None
        except Exception as e:
            print(f"[Transcription Error]: {e}")
            return None
