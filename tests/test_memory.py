import sqlite3
import pytest
from fastapi.testclient import TestClient
from tools import memory_store as memory, meta_tools


@pytest.fixture(autouse=True)
def isolated_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "DATABASE", tmp_path / 'memories.sqlite3')
    monkeypatch.setattr(memory, "LEGACY_FILE", tmp_path / 'learned_rules.md')


def test_legacy_import_preserves_file_and_does_not_repeat():
    original = '# Learned rules\n\n- **[USER_PREF]** (2026-11-21 12:00): Keep replies short\n'
    memory.LEGACY_FILE.write_text(original)
    rows = memory.list_memories()
    assert len(rows) == 1 and rows[0]['rule'] == 'Keep replies short'
    memory.change_memory(rows[0]['id'], 1, action='archive')
    assert memory.list_memories() == []
    assert memory.LEGACY_FILE.read_text() == original
    assert len(memory.list_memories(True)) == 1


def test_chat_and_ui_share_corrections_expiry_and_undo(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture')
    import server
    from core.agent import JarvisAgent
    headers = {'Authorization': f'Bearer {server.OWNER_TOKEN}'}
    assert meta_tools.log_learned_rule('USER_PREF', 'Use detailed answers').startswith('SUCCESS')
    with TestClient(server.app) as client:
        assert client.get('/api/memory').status_code == 401
        record = client.get('/api/memory', headers=headers).json()['records'][0]
        url = f"/api/memory/{record['id']}"
        assert client.put(url, json={'version': 1, 'action': 'archive'}).status_code == 401
        corrected = {'version': 1, 'category': 'USER_PREF', 'rule': 'Use brief answers'}
        assert client.put(url, headers=headers, json=corrected).status_code == 200
        assert client.put(url, headers=headers, json=corrected).status_code == 409
        prompt = JarvisAgent().build_system_prompt('How should you write your answers?')
        assert 'Use brief answers' in prompt and 'Use detailed answers' not in prompt
        assert client.put(url, headers=headers, json={'version': 2, 'action': 'undo'}).status_code == 200
        assert 'Use detailed answers' in meta_tools.read_memory('answers')
        assert client.put(url, headers=headers, json={'version': 3, 'action': 'archive'}).status_code == 200
        assert 'Use detailed answers' not in meta_tools.read_memory('answers')
        assert client.put(url, headers=headers, json={'version': 4, 'action': 'restore'}).status_code == 200
        assert 'Use detailed answers' in meta_tools.read_memory('answers')
        assert client.put(url, headers=headers, json={**corrected, 'version': 5, 'expires_at': '2000-01-01T00:00:00Z'}).status_code == 200
        assert 'Use brief answers' not in meta_tools.read_memory('answers')
        assert client.get('/api/memory', headers=headers).json()['records'][0]['expired'] is True


def test_validation_duplicates_and_failed_write_are_not_success(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture')
    import server
    headers = {'Authorization': f'Bearer {server.OWNER_TOKEN}'}
    with TestClient(server.app, raise_server_exceptions=False) as client:
        assert client.post('/api/memory', headers=headers, json={'category':'X', 'rule':' '}).status_code == 422
        assert client.post('/api/memory', headers=headers, json={'category':'X', 'rule':'A', 'expires_at':'2026-11-21T09:00'}).status_code == 422
        for _ in range(2):
            assert client.post('/api/memory', headers=headers, json={'category':'X', 'rule':'A'}).status_code == 200
        assert len(memory.list_memories()) == 1
        def disk_failure(*args, **kwargs):
            raise sqlite3.OperationalError('disk full')
        monkeypatch.setattr(memory, 'add_memory', disk_failure)
        assert client.post('/api/memory', headers=headers, json={'category':'X', 'rule':'B'}).status_code == 500
        assert meta_tools.log_learned_rule('X', 'B').startswith('ERROR')
        assert len(memory.list_memories()) == 1
