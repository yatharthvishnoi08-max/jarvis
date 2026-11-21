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
    assert len(record.messages) == 1
    assert record.messages[0]['content'] == 'Remember the project'
    assert not list(tmp_path.glob("*.tmp"))


def test_session_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    record = session.Session("unicode")
    record.add_message("user", "Tomorrow’s plan 🗓")
    restored = session.Session.load("unicode")
    assert restored.messages == record.messages


def test_resume_after_partial_tool_batch_preserves_known_result(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    record = session.Session("interrupted")
    calls = [{"id": value, "type": "function", "function": {"name": "fixture", "arguments": "{}"},
              "extra_content": {"google": {"thought_signature": "fixture-signature"}}} for value in ('done', 'unknown')]
    record.add_message('assistant', '', tool_calls=calls)
    record.add_message('tool', 'Verified result', tool_call_id='done')
    record.add_message('assistant', 'Operation stopped')
    record.add_message('user', 'Continue after checking the screen')
    restored = session.Session.load('interrupted')
    original = list(restored.messages)
    history = restored.model_history()
    assert history[0]['tool_calls'] == calls
    assert history[1]['content'] == 'Verified result'
    assert history[2]['tool_call_id'] == 'unknown'
    assert 'outcome is unknown' in history[2]['content']
    assert history[3]['content'] == 'Operation stopped'
    assert restored.messages == original


def test_completed_tool_history_is_unchanged_and_orphans_are_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SESSIONS_DIR", tmp_path)
    record = session.Session('completed')
    record.add_message('tool', 'Orphan from incomplete old save', tool_call_id='missing')
    record.add_message('assistant', '', tool_calls=[{'id': 'real', 'type': 'function', 'function': {'name': 'fixture', 'arguments': '{}'}}])
    record.add_message('tool', 'Actual evidence', tool_call_id='real')
    record.add_message('assistant', 'Finished')
    history = record.model_history()
    assert [m['role'] for m in history] == ['assistant', 'tool', 'assistant']
    assert history[1]['content'] == 'Actual evidence'
