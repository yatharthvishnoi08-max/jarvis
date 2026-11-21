from fastapi.testclient import TestClient


def test_dashboard_and_agent_share_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture")
    from tools import planner
    import server

    monkeypatch.setattr(planner, "DATABASE", tmp_path / "planner.sqlite3")
    headers = {"Authorization": f"Bearer {server.OWNER_TOKEN}"}
    with TestClient(server.app) as client:
        assert client.get("/api/planner").status_code == 401
        planner.add_task("Review schedule", "tomorrow")
        task = client.get("/api/planner", headers=headers).json()["tasks"][0]
        assert task["title"] == "Review schedule"
        assert client.post("/api/planner", headers=headers, json={"title": " "}).status_code == 422
        assert client.post("/api/planner", headers=headers, json={"title": "Call back"}).status_code == 200
        assert "Call back" in planner.list_tasks("all")
        assert client.post(f"/api/planner/{task['id']}/complete", headers=headers).status_code == 200
        assert "Review schedule" not in planner.list_tasks("all")
