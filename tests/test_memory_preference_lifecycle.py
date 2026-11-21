"""
Test a benign remembered preference across a new chat, restart simulation, and correction.
"""
import pytest
from tools import memory_store
from tools.meta_tools import log_learned_rule, read_memory
from core.agent import JarvisAgent
from core.session import Session

def test_remembered_preference_lifecycle(tmp_path, monkeypatch):
    test_db = tmp_path / "memories.sqlite3"
    monkeypatch.setattr(memory_store, "DATABASE", test_db)
    monkeypatch.setattr(memory_store, "LEGACY_FILE", tmp_path / "learned_rules.md")

    # 1. Add benign remembered preference
    pref_cat = "user_preference"
    pref_text = "Always format calendar times in 24-hour notation."
    res = log_learned_rule(pref_cat, pref_text)
    assert "SUCCESS: Saved memory" in res

    # 2. Verify it is in memory store
    memories = memory_store.list_memories()
    assert len(memories) == 1
    mem_id = memories[0]["id"]
    assert memories[0]["rule"] == pref_text
    assert memories[0]["version"] == 1

    # 3. Verify read_memory includes it
    mem_text = read_memory()
    assert pref_text in mem_text

    # 4. Restart simulation: re-instantiate JarvisAgent and verify system prompt includes it
    agent_after_restart = JarvisAgent()
    sys_prompt = agent_after_restart.build_system_prompt()
    assert pref_text in sys_prompt

    # 5. Apply correction (edit memory with optimistic version check)
    corrected_text = "Prefer 12-hour AM/PM notation for user output."
    updated = memory_store.change_memory(
        mem_id,
        action="edit",
        category="user_preference",
        rule=corrected_text,
        version=1
    )
    assert updated["rule"] == corrected_text
    assert updated["version"] == 2

    # 6. Verify correction reflected in system prompt of a new session
    agent_corrected = JarvisAgent()
    new_prompt = agent_corrected.build_system_prompt()
    assert corrected_text in new_prompt
    assert pref_text not in new_prompt
