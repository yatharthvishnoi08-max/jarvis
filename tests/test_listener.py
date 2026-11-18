import io
import json
import numpy as np
import scipy.io.wavfile as wav
import pytest
from unittest.mock import patch, MagicMock

from core.listener import VoiceListener, WisprFlowTranscriber

def _generate_synthetic_wav(duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates synthetic 16kHz sine wave audio bytes."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    int16_audio = (sine * 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, sample_rate, int16_audio)
    return buf.getvalue()

def test_wispr_transcriber_unconfigured():
    with patch.dict("os.environ", {"WISPR_FLOW_API_KEY": ""}, clear=True):
        wt = WisprFlowTranscriber(api_key="")
        assert not wt.is_configured()
        assert wt.transcribe(b"dummy") is None

def test_wispr_transcriber_mock_success():
    wt = WisprFlowTranscriber(api_key="mock_wispr_key_123")
    assert wt.is_configured()

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "id": "wispr_tx_001",
        "text": "JARVIS, run system diagnostics.",
        "detected_language": "en"
    }

    synthetic_wav = _generate_synthetic_wav(0.5)

    with patch("httpx.Client.post", return_value=fake_resp):
        res = wt.transcribe(synthetic_wav)
        assert res == "JARVIS, run system diagnostics."

def test_voice_listener_engine_name():
    listener = VoiceListener()
    with patch.dict("os.environ", {"WISPR_FLOW_API_KEY": "wispr_test_key"}):
        listener.wispr_engine.api_key = "wispr_test_key"
        assert "Wispr Flow" in listener.engine_name

    with patch.dict("os.environ", {"WISPR_FLOW_API_KEY": ""}):
        listener.wispr_engine.api_key = ""
        assert "Fallback" in listener.engine_name

def test_voice_listener_transcribe_wav_wispr_priority():
    listener = VoiceListener()
    synthetic_wav = _generate_synthetic_wav(0.5)

    with patch.object(listener.wispr_engine, "is_configured", return_value=True):
        with patch.object(listener.wispr_engine, "transcribe", return_value="Wispr Flow Recognized"):
            result = listener.transcribe_wav(synthetic_wav)
            assert result == "Wispr Flow Recognized"

def test_pre_roll_ring_buffer():
    listener = VoiceListener()
    assert len(listener.pre_roll_buffer) == 0
    # Simulate adding chunks
    dummy_chunk = np.zeros(1600, dtype=np.float32)
    for _ in range(10):
        listener.pre_roll_buffer.append(dummy_chunk)
    # Ring buffer cap is 5
    assert len(listener.pre_roll_buffer) == listener.pre_roll_chunks
