import pytest
from core import session


def test_failed_session_save_keeps_previous_history(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    record = session.Session("durable")
    record.add_message("user", "Remember the project")
    before = (tmp_path / "durable.json").read_text()

    def fail(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(session.os, "replace", fail)
    with pytest.raises(OSError):
        record.add_message("assistant", "New response")
    assert (tmp_path / "durable.json").read_text() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_session_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    record = session.Session("unicode")
    record.add_message("user", "Tomorrow’s plan 🗓")
    restored = session.Session.load("unicode")
    assert restored.messages == record.messages
