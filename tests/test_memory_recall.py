import pytest
from tools import memory_store as memory
from tools.memory_recall import recall, MAX_CONTEXT_CHARS


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, 'DATABASE', tmp_path / 'memories.sqlite3')
    monkeypatch.setattr(memory, 'LEGACY_FILE', tmp_path / 'absent.md')


def test_relevant_context_excludes_other_projects_and_keeps_core():
    core = memory.add_memory('USER_PREF', 'Keep answers concise.', pinned=True)
    atlas = memory.add_memory('PROJECT', 'Atlas proposal review is with Priya on Friday.')
    unrelated = memory.add_memory('PERSONAL', 'My favourite dessert is mango ice cream.')
    result = recall('Prepare for the Atlas review')
    assert {r['id'] for r in result['selected']} == {core['id'], atlas['id']}
    assert 'mango' not in result['context']
    assert [r['id'] for r in recall('hello')['selected']] == [core['id']]
    assert unrelated['id'] not in {r['id'] for r in result['selected']}


def test_corrections_expiry_and_archives_do_not_recall_stale_facts():
    record = memory.add_memory('PROJECT', 'Atlas deadline is Monday.')
    memory.change_memory(record['id'], 1, category='PROJECT', rule='Atlas deadline is Tuesday.')
    assert 'Tuesday' in recall('Atlas deadline')['context']
    assert 'Monday' not in recall('Atlas deadline')['context']
    memory.change_memory(record['id'], 2, action='archive')
    memory.add_memory('PROJECT', 'Atlas deadline is yesterday.', expires_at='2000-01-01T00:00:00Z')
    assert recall('Atlas deadline')['selected'] == []


def test_context_is_bounded_and_long_record_excerpt_contains_match():
    for n in range(20):
        memory.add_memory('USER_PREF', f'Preference {n} ' + 'concise ' * 200, pinned=True)
    for n in range(20):
        memory.add_memory('PROJECT', f'Project {n} ' + 'ordinary content ' * 150 + 'Atlas deadline Friday ' + 'detail ' * 50)
    result = recall('Atlas deadline')
    assert len(result['context']) <= MAX_CONTEXT_CHARS
    assert any(r['kind'] == 'Relevant' and 'Atlas deadline' in r['excerpt'] for r in result['selected'])
    assert sum(r['kind'] == 'Relevant' for r in result['selected']) <= 6


def test_recent_context_helps_followups_but_current_topic_ranks_first():
    atlas = memory.add_memory('PROJECT', 'Atlas review with Priya.')
    nova = memory.add_memory('PROJECT', 'Nova budget with Sam.')
    result = recall('What about the Nova budget?', 'We were talking about the Atlas review.')
    assert result['selected'][0]['id'] == nova['id']
    assert atlas['id'] in {r['id'] for r in recall('And tomorrow?', 'Atlas review')['selected']}


def test_prompt_and_authenticated_preview_use_selected_context(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture')
    from core.agent import JarvisAgent
    from fastapi.testclient import TestClient
    import server
    memory.add_memory('PROJECT', 'Atlas deadline Friday.')
    memory.add_memory('PERSONAL', 'Favourite dessert mango.')
    prompt = JarvisAgent().build_system_prompt('Atlas deadline')
    assert 'Atlas deadline Friday' in prompt and 'Favourite dessert mango' not in prompt
    headers = {'Authorization': f'Bearer {server.OWNER_TOKEN}'}
    with TestClient(server.app) as client:
        assert client.post('/api/memory/recall', json={'query':'Atlas'}).status_code == 401
        result = client.post('/api/memory/recall', headers=headers, json={'query':'Atlas'}).json()
        assert len(result['selected']) == 1
