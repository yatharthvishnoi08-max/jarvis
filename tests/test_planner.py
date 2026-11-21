import asyncio
import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from tools import planner


def test_planner_dates_and_retries(monkeypatch, tmp_path):
    monkeypatch.setattr(planner, "DATABASE", tmp_path / "tasks.db")
    planner.add_task("Call the dentist", "today")
    assert "Already" in planner.add_task("call the dentist", "today")
    planner.add_task("Pay bill", (date.today() - timedelta(days=1)).isoformat())
    planner.add_task("Read article")
    planner.add_task("Print tickets", "tomorrow")
    with pytest.raises(ValueError):
        planner.add_task("Bad date", "not a date")
    daily = planner.list_tasks()
    assert "Call the dentist" in daily and "overdue" in daily
    assert "Print tickets" not in daily and "Read article" not in daily
    assert len(planner.list_tasks("all").splitlines()) == 4
    planner.complete_task(1)
    assert "Call the dentist" not in planner.list_tasks()
    assert "Already completed" in planner.complete_task(1)


def test_planner_shared_across_chats(monkeypatch, tmp_path):
    from core import session
    from core.agent import JarvisAgent
    from core.approvals import approval_manager

    monkeypatch.setattr(planner, "DATABASE", tmp_path / "planner.db")
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture")
    agent = JarvisAgent()
    actions = iter([("add_task", {"title": "Return library book", "due": "today"}),
                    ("list_tasks", {"view": "today"})])

    def model(**request):
        last = request["messages"][-1]
        if last["role"] == "tool":
            reply = SimpleNamespace(content=last["content"], tool_calls=None)
        else:
            name, args = next(actions)
            call = SimpleNamespace(id="call1", function=SimpleNamespace(name=name, arguments=json.dumps(args)))
            reply = SimpleNamespace(content="", tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=reply)])

    monkeypatch.setattr(agent.client.chat.completions, "create", model)
    approved = []

    def approve(req):
        approved.append(req["tool"])
        approval_manager.decide(req["id"], "approve")

    async def conversation():
        await agent.chat_async(session.Session(), "Add my book return for today", on_approval_needed=approve)
        return await agent.chat_async(session.Session(), "What's due today?", on_approval_needed=approve)

    assert "Return library book" in asyncio.run(conversation())
    assert approved == ["add_task"]
