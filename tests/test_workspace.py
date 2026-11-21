import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient
from tools import google_workspace as google


def test_threads_and_calendar(monkeypatch):
    monkeypatch.setattr(google.Credentials, "from_authorized_user_file", lambda *_: SimpleNamespace(valid=True))

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, params, timeout):
            msg = {"internalDate": "20", "labelIds": ["INBOX"], "payload": {"headers": [{"name": "Subject", "value": "Review proposal"}]}}
            if url.endswith("threads"):
                payload = {"threads": [{"id": "open"}, {"id": "answered"}]}
            elif url.endswith("open"):
                payload = {"messages": [msg]}
            elif url.endswith("answered"):
                payload = {"messages": [msg, {**msg, "internalDate": "21", "labelIds": ["SENT"]}]}
            else:
                assert params["singleEvents"] == "true"
                payload = {"items": [{"id": "day", "summary": "Workshop", "start": {"date": "2026-11-24"}}]}
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)

    monkeypatch.setattr(google, "AuthorizedSession", lambda _: Session())
    result = google.read_workspace()
    assert [row["id"] for row in result["inbox"]] == ["open"]
    assert result["events"][0]["start"] == "2026-11-24"


def test_disconnected_workspace_is_private(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture")
    monkeypatch.setattr(google, "TOKEN", tmp_path / "absent.json")
    import server

    with TestClient(server.app) as client:
        assert client.get("/api/workspace").status_code == 401
        data = client.get("/api/workspace", headers={"Authorization": f"Bearer {server.OWNER_TOKEN}"}).json()
        assert data["state"] == "disconnected" and data["inbox"] == []


def test_briefing_handles_one_version_and_detects_overlap(tmp_path, monkeypatch):
    from tools import planner, briefing
    monkeypatch.setattr(planner, "DATABASE", tmp_path / "tasks.sqlite3")
    planner.add_task("Review plan", "today")
    events = [{"id":k, "title":k, "start":"2026-11-24T15:00:00+05:30", "end":"2026-11-24T16:00:00+05:30"} for k in ["a","b"]]
    mail = {"id":"thread", "version":"1", "title":"Please confirm by today"}
    snapshot = {"state":"connected", "inbox":[mail], "events":events}
    rows = briefing.items(snapshot)
    assert {r["kind"] for r in rows} == {"email","task","conflict"}
    assert rows[0]["kind"] == "email"
    planner.handle_decision(rows[0]["id"])
    assert "email" not in [r["kind"] for r in briefing.items(snapshot)]
    mail["version"]="2"
    assert "email" in [r["kind"] for r in briefing.items(snapshot)]
