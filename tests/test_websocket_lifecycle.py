"""Failures and cancellation must reach the browser through the real WS endpoint."""
import asyncio
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture')
    monkeypatch.setenv('REQUIRE_AUTH', 'true')
    from core import session as sessions
    from tools import google_workspace
    import server
    monkeypatch.setattr(sessions, 'SESSIONS_DIR', tmp_path)
    monkeypatch.setattr(google_workspace, 'TOKEN', tmp_path / 'absent-token.json')
    monkeypatch.setattr(server, 'session_manager', sessions.SessionManager())
    monkeypatch.setattr(server.speaker, 'api_key', '')
    return server


def test_provider_failure_is_visible_and_same_socket_can_retry(gateway, monkeypatch):
    attempts = []
    from unittest.mock import Mock
    log = Mock()
    monkeypatch.setattr(gateway.audit_logger, 'log_event', log)
    async def reply(**kwargs):
        attempts.append(kwargs['user_input'])
        if len(attempts) == 1:
            raise ValueError('private-provider-payload')
        return 'Recovered reply'
    monkeypatch.setattr(gateway, 'agent', SimpleNamespace(chat_async=reply))
    with TestClient(gateway.app) as client, client.websocket_connect(f'/ws?token={gateway.OWNER_TOKEN}') as ws:
        turn = {'type': 'chat', 'text': 'hello', 'session_id': 'failure-test', 'voice': False}
        ws.send_json(turn)
        result = ws.receive_json()
        assert result['type'] == 'error' and result['session_id'] == 'failure-test'
        assert 'private-provider-payload' not in str(result)
        event = log.call_args.kwargs
        assert event['event_type'] == 'TURN_FAILED'
        assert event['error_type'] == 'ValueError'
        assert event['reference'] == result['reference']
        assert any(location.startswith('test_websocket_lifecycle.py:') for location in event['locations'])
        assert 'private-provider-payload' not in str(event)
        ws.send_json({'type': 'ping'})
        assert ws.receive_json()['type'] == 'pong'
        ws.send_json(turn)
        assert ws.receive_json()['text'] == 'Recovered reply'


def test_cancel_is_received_while_turn_is_running(gateway, monkeypatch):
    async def reply(session, on_thought, **kwargs):
        session.reset_cancellation()
        on_thought('Started')
        for _ in range(200):
            if session.is_cancelled:
                return 'Stopped before next action'
            await asyncio.sleep(.01)
        raise AssertionError('Cancel was blocked behind the chat task')
    monkeypatch.setattr(gateway, 'agent', SimpleNamespace(chat_async=reply))
    with TestClient(gateway.app) as client, client.websocket_connect(f'/ws?token={gateway.OWNER_TOKEN}') as ws:
        ws.send_json({'type': 'chat', 'text': 'test', 'session_id': 'stop-test', 'voice': False})
        assert ws.receive_json()['type'] == 'thought'
        ws.send_json({'type': 'cancel', 'session_id': 'stop-test'})
        results = [ws.receive_json(), ws.receive_json()]
        assert {r['type'] for r in results} == {'response', 'task_cancelled'}
        assert next(r for r in results if r['type'] == 'response')['text'] == 'Stopped before next action'


@pytest.mark.parametrize('text_first', [False, True])
def test_voice_failure_keeps_text_reply(gateway, monkeypatch, text_first):
    async def reply(**kwargs):
        return 'The text answer is still available'
    def voice_failure(*args, **kwargs):
        raise RuntimeError('voice provider unavailable')
    monkeypatch.setattr(gateway, 'agent', SimpleNamespace(chat_async=reply))
    monkeypatch.setattr(gateway.speaker, 'api_key', 'fixture')
    monkeypatch.setattr(gateway.speaker, 'generate_speech', voice_failure)
    with TestClient(gateway.app) as client, client.websocket_connect(f'/ws?token={gateway.OWNER_TOKEN}') as ws:
        ws.send_json({'type': 'chat', 'text': 'test', 'voice': True, 'text_first': text_first})
        results = [ws.receive_json() for _ in range(3 if text_first else 2)]
        reply = next(r for r in results if r['type'] == 'response')
        assert reply['text'] == 'The text answer is still available'
        assert all(r['type'] != 'error' for r in results)
        if text_first:
            assert results[0]['type'] == 'response'
            assert results[-1]['type'] == 'reply_audio' and results[-1]['audio_id'] is None


def test_new_text_can_finish_while_previous_speech_is_pending(gateway, monkeypatch):
    release = Event()
    async def reply(session, user_input, **kwargs):
        session.add_message('user', user_input)
        return 'Reply to ' + user_input
    def voice_wait(*args, **kwargs):
        assert release.wait(3)
        return None
    monkeypatch.setattr(gateway, 'agent', SimpleNamespace(chat_async=reply))
    monkeypatch.setattr(gateway.speaker, 'api_key', 'fixture')
    monkeypatch.setattr(gateway.speaker, 'generate_speech', voice_wait)
    with TestClient(gateway.app) as client, client.websocket_connect(f'/ws?token={gateway.OWNER_TOKEN}') as ws:
        ws.send_json({'type': 'chat', 'text': 'first', 'voice': True, 'text_first': True})
        assert ws.receive_json()['text'] == 'Reply to first'
        assert ws.receive_json()['type'] == 'audio_state'
        ws.send_json({'type': 'chat', 'text': 'second', 'voice': False, 'text_first': True})
        try:
            assert ws.receive_json()['text'] == 'Reply to second'
        finally:
            release.set()
        assert ws.receive_json()['type'] == 'reply_audio'


def test_disconnect_cancels_pending_approval(gateway, monkeypatch):
    finished = Event()
    requests = []
    async def reply(session, on_approval_needed, **kwargs):
        req = gateway.approval_manager.create_request(
            session_id=session.id, tool='fixture', args={}, policy_level='CONFIRM', summary='Fixture approval')
        requests.append(req)
        on_approval_needed(req.to_dict())
        try:
            await req.event.wait()
            assert req.status == 'CANCELLED'
            assert session.is_cancelled
            return 'Cancelled'
        finally:
            finished.set()
    monkeypatch.setattr(gateway, 'agent', SimpleNamespace(chat_async=reply))
    with TestClient(gateway.app) as client:
        with client.websocket_connect(f'/ws?token={gateway.OWNER_TOKEN}') as ws:
            ws.send_json({'type': 'chat', 'text': 'test approval', 'voice': False})
            assert ws.receive_json()['type'] == 'approval_required'
        assert finished.wait(2)
        assert requests[0].status == 'CANCELLED'
