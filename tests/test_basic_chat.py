from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_basic_chat_without_socket_or_tools(tmp_path, monkeypatch):
    import server
    from core import session
    monkeypatch.setenv("OPENROUTER_API_KEY", "local-test")
    monkeypatch.setattr(server, "session_manager", session.SessionManager())
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    answers = iter(["Hello!", "", "Still here."])
    histories = []

    def complete(*, model, messages):
        histories.append([m["content"] for m in messages[1:]])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(answers)))])

    monkeypatch.setattr(server.agent, "client", SimpleNamespace(with_options=lambda **kw:
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))))
    with TestClient(server.app) as app:
        body = {"session_id": "chat_test", "text": "Hi"}
        assert app.post("/api/chat", json=body).status_code == 401
        app.headers["Authorization"] = "Bearer " + server.OWNER_TOKEN
        assert app.post("/api/chat", json=body).json()["reply"]["content"] == "Hello!"
        body["text"] = "Hello again"
        assert app.post("/api/chat", json=body).status_code == 502
        assert app.post("/api/chat", json=body).json()["reply"]["content"] == "Still here."
        assert histories[1] == histories[2] == ["Hi", "Hello!", "Hello again"]
        assert len(app.get("/api/sessions/chat_test").json()["messages"]) == 4
