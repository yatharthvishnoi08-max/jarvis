"""Use real chat/session routes with deterministic model and voice providers."""
from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_phone_chat_restores_context_and_playback(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-provider-key")
    from core import session as sessions
    import server

    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(server, "session_manager", sessions.SessionManager())
    token = server.OWNER_TOKEN
    headers = {"Authorization": f"Bearer {token}"}
    histories = []
    release_voice = Event()

    def complete(*, messages, **kwargs):
        history = [m["content"] for m in messages if m["role"] == "user"]
        histories.append(history)
        message = SimpleNamespace(content=history[0], tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def synthesize(text, session_id, message_id):
        assert release_voice.wait(timeout=3), "text was held until voice completed"
        return {"audio_id": "aud_example"}

    monkeypatch.setattr(server.agent.client.chat.completions, "create", complete)
    monkeypatch.setattr(server.speaker, "api_key", "fixture")
    monkeypatch.setattr(server.speaker, "generate_speech", synthesize)
    ws_url = f"/ws?token={token}"
    turn = {"type": "chat", "session_id": "default", "text_first": True}
    with TestClient(server.app) as app:
        assert app.get("/api/sessions/default", headers=headers).status_code == 404
        with app.websocket_connect(ws_url) as ws:
            ws.send_json({**turn, "text": "mango", "voice": True})
            reply = ws.receive_json()
            assert reply["type"] == "response" and reply["text"] == "mango"
            assert reply["voice_pending"] is True
            release_voice.set()
            voice_state = ws.receive_json()
            assert voice_state["type"] == "audio_state"
            assert voice_state["session_id"] == "default" and voice_state["message_id"] == reply["message_id"]
            audio = ws.receive_json()
            assert audio["type"] == "reply_audio" and audio["message_id"] == reply["message_id"]

        monkeypatch.setattr(server, "session_manager", sessions.SessionManager())
        restored = app.get("/api/sessions/default", headers=headers).json()
        assert restored["messages"][-1]["audio_id"] == audio["audio_id"]
        with app.websocket_connect(ws_url) as ws:
            ws.send_json({**turn, "text": "What word?", "voice": False})
            assert ws.receive_json()["text"] == "mango"
            fresh = app.post("/api/sessions", headers=headers, json={}).json()["session"]["id"]
            ws.send_json({**turn, "session_id": fresh, "text": "pear", "voice": False})
            assert ws.receive_json()["text"] == "pear"
        assert histories == [["mango"], ["mango", "What word?"], ["pear"]]


def test_runtime_identifies_voice_build_without_credentials(monkeypatch):
    import server
    monkeypatch.setenv('JARVIS_AUTH_REQUIRED', 'true')
    with TestClient(server.app) as app:
        response = app.get('/api/runtime', headers={'Authorization': 'Bearer ' + server.OWNER_TOKEN})
        assert response.status_code == 200
        assert response.json()['release'] == 'wake-2026.11.21.1'
        assert set(response.json()) == {'release', 'hostname', 'interface', 'wake_word'}
        assert app.get('/').headers['cache-control'] == 'no-store'
