import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('tool_result,expected', [
    ("ERROR: Launched 'notepad', but failed to become visible foreground window.", 'ERROR'),
    ("SUCCESS: Opened application 'notepad' and verified visible in foreground.", 'SUCCESS'),
])
def test_agent_records_desktop_result_not_just_python_return(tmp_path, monkeypatch, tool_result, expected):
    from core import agent as module, session as sessions
    monkeypatch.setattr(sessions, 'SESSIONS_DIR', tmp_path)
    monkeypatch.setattr(module, 'classify_tool_call', lambda *args: (module.POLICY_READ, 'fixture'))
    monkeypatch.setitem(module.TOOL_FUNCTIONS, 'open_app', lambda **args: tool_result)
    audit, traces = Mock(), Mock()
    monkeypatch.setattr(module.audit_logger, 'log_event', audit)
    monkeypatch.setattr(module.trace_store, 'record_trace', traces)
    call = SimpleNamespace(id='fixture-call', function=SimpleNamespace(name='open_app', arguments=json.dumps({'target':'notepad'})))
    create = Mock(side_effect=[
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call], content=None))]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[], content='Fixture reply'))]),
    ])
    agent = module.JarvisAgent()
    agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    agent.build_system_prompt = lambda *args: 'Fixture system'
    session = sessions.Session('desktop-result')
    assert asyncio.run(agent.chat_async(session, 'Open test app')) == 'Fixture reply'
    execution = next(c.kwargs for c in audit.call_args_list if c.kwargs['event_type'] == 'TOOL_EXECUTED')
    assert execution['status'] == expected
    step = traces.call_args.args[0].steps[0]
    assert bool(step.error) == (expected == 'ERROR')
    if expected == 'ERROR':
        assert execution['detail'] == tool_result
        assert step.error == tool_result
