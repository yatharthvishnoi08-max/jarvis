import asyncio
import copy
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock
import httpx
import pytest
from openai import APITimeoutError, BadRequestError
from core.client import SmartChatCompletions, request_timeout
from core.context_window import model_window


def client(side_effect):
    create=Mock(side_effect=side_effect)
    return NS(chat=NS(completions=NS(create=create))), create


def timeout(): return APITimeoutError(request=httpx.Request('POST','https://fixture.invalid'))


def test_timeout_falls_back_without_replaying_any_tools():
    primary, call=client([timeout(), 'recovered'])
    brain=SmartChatCompletions(primary,'first',['second'])
    assert brain.create(messages=[{'role':'user','content':'Draft only'}]) == 'recovered'
    assert [c.kwargs['model'] for c in call.call_args_list] == ['first','second']


def test_signed_tool_chain_retries_same_model_and_does_not_cross_provider():
    primary, call=client([timeout(), 'recovered']); backup, backup_call=client(['wrong'])
    messages=[{'role':'assistant','content':'','tool_calls':[{'extra_content':{'google':{'thought_signature':'opaque'}}}]}]
    brain=SmartChatCompletions(primary,'first',['second'],backup,'free:free')
    assert brain.create(messages=messages)=='recovered'
    assert [c.kwargs['model'] for c in call.call_args_list]==['first','first']
    backup_call.assert_not_called()


def test_invalid_request_is_not_retried_and_failure_is_bounded():
    response=httpx.Response(400,request=httpx.Request('POST','https://fixture.invalid'))
    error=BadRequestError('invalid schema',response=response,body=None)
    primary, call=client([error]);brain=SmartChatCompletions(primary,'first',['second'])
    with pytest.raises(BadRequestError): brain.create(messages=[])
    assert call.call_count==1
    primary, call=client(timeout());backup, backup_call=client(timeout())
    with pytest.raises(APITimeoutError): SmartChatCompletions(primary,'first',['a','b','c'],backup,'free:free').create(messages=[])
    assert call.call_count==2 and backup_call.call_count==1


def test_context_keeps_current_tool_chain_and_saved_history_unchanged():
    messages=[{'role':'system','content':'Persona'}]
    for i in range(30): messages.extend([{'role':'user','content':f'old {i}'},{'role':'assistant','content':'old output '*1500}])
    call={'id':'current','type':'function','function':{'name':'read_file','arguments':'{}'},'extra_content':{'google':{'thought_signature':'opaque-signature'}}}
    messages += [{'role':'user','content':'Current request'}, {'role':'assistant','content':'','tool_calls':[call]}, {'role':'tool','tool_call_id':'current','content':'x'*25000}]
    original=copy.deepcopy(messages); selected=model_window(messages)
    assert messages==original
    assert len(json.dumps(selected)) < 24000
    assert selected[-3]['content']=='Current request'
    assert selected[-2]['tool_calls']==[call]
    assert selected[-1]['tool_call_id']=='current' and 'middle omitted' in selected[-1]['content']
    assert 'older turns' in selected[0]['content']


def test_small_history_remains_exact_and_current_request_is_not_cut():
    messages=[{'role':'user','content':'hello'},{'role':'assistant','content':'hi'},{'role':'user','content':'follow-up'}]
    assert model_window(messages)==messages
    assert model_window([{'role':'user','content':'x'*30000}])[-1]['content']=='x'*30000


def test_provider_timeout_returns_safe_reply_and_next_turn_works(tmp_path,monkeypatch):
    from core import agent as module, session as sessions
    monkeypatch.setattr(sessions,'SESSIONS_DIR',tmp_path)
    monkeypatch.setattr(module.audit_logger,'log_event',Mock())
    monkeypatch.setattr(module.trace_store,'record_trace',Mock())
    agent=module.JarvisAgent(); agent.build_system_prompt=lambda *args:'Fixture'
    raw, call=client([timeout(),NS(choices=[NS(message=NS(content='Here is the draft.',tool_calls=[]))])]);agent.client=raw
    session=sessions.Session('safe-error')
    answer=asyncio.run(agent.chat_async(session,'Draft a message, do not send'))
    assert 'took too long' in answer and 'No computer actions' in answer
    assert 'Inference Error' not in answer and 'fixture.invalid' not in answer
    assert asyncio.run(agent.chat_async(session,'Try the draft again'))=='Here is the draft.'


def test_failure_after_action_does_not_repeat_it_and_warns_about_partial_work(tmp_path,monkeypatch):
    from core import agent as module, session as sessions
    monkeypatch.setattr(sessions,'SESSIONS_DIR',tmp_path)
    monkeypatch.setattr(module.audit_logger,'log_event',Mock())
    monkeypatch.setattr(module.trace_store,'record_trace',Mock())
    action=Mock(return_value='SUCCESS: inspected fixture')
    monkeypatch.setitem(module.TOOL_FUNCTIONS,'get_system_stats',action)
    tc=NS(id='one',function=NS(name='get_system_stats',arguments='{}'))
    raw, _=client([NS(choices=[NS(message=NS(content=None,tool_calls=[tc]))]),timeout()])
    agent=module.JarvisAgent();agent.build_system_prompt=lambda *args:'Fixture';agent.client=raw
    answer=asyncio.run(agent.chat_async(sessions.Session('partial-error'),'Inspect test system'))
    assert action.call_count==1
    assert 'Some actions were already attempted' in answer
    assert 'No computer actions' not in answer
