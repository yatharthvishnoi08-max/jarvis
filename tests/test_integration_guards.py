"""Regression checks for the merged local-access and visual-input paths."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_remote_websocket_still_requires_token_in_local_mode(monkeypatch):
    import server
    monkeypatch.setenv('REQUIRE_AUTH', 'false')
    with TestClient(server.app, client=('198.51.100.5', 50000)) as client:
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect('/ws'):
                pass
        assert rejected.value.code == 1008
        with client.websocket_connect('/ws?token=' + server.OWNER_TOKEN) as ws:
            ws.send_json({'type': 'ping'})
            assert ws.receive_json()['type'] == 'pong'


def test_local_websocket_accepts_ipv6_and_rejects_foreign_origin(monkeypatch):
    import server
    monkeypatch.setenv('REQUIRE_AUTH', 'false')
    with TestClient(server.app, client=('::1', 50000), base_url='http://[::1]:8000') as client:
        with client.websocket_connect('/ws', headers={'origin': 'http://[::1]:8000'}) as ws:
            ws.send_json({'type': 'ping'})
            assert ws.receive_json()['type'] == 'pong'
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect('/ws', headers={'origin':'https://untrusted.example'}):
                pass
        assert rejected.value.code == 1008


@pytest.mark.parametrize('coordinates,click_result,expected', [
    ({'x':120, 'y':200, 'found':True, 'confidence':.95}, 'SUCCESS: clicked', 'SUCCESS:'),
    ({'x':120, 'y':200, 'found':True, 'confidence':.95}, 'ERROR: WINDOW_MISMATCH', 'ERROR: WINDOW_MISMATCH'),
    ({'x':9999, 'y':200, 'found':True, 'confidence':.95}, None, 'ERROR:'),
    ({'x':120, 'y':200, 'found':True, 'confidence':.1}, None, 'ERROR:'),
])
def test_visual_click_passes_target_and_never_masks_rejection(tmp_path, monkeypatch, coordinates, click_result, expected):
    from tools import computer_use_tools as computer, multimodal_tools as vision
    from PIL import ImageGrab
    monkeypatch.setattr(computer, '_enforce_desktop_and_target', lambda _: (True, 'OK'))
    monkeypatch.setattr(vision, '_ensure_input_desktop', lambda: None)
    monkeypatch.setattr(computer, 'SCREENSHOTS_DIR', tmp_path)
    monkeypatch.setattr(ImageGrab, 'grab', lambda: SimpleNamespace(size=(800,600), save=lambda path, **kwargs: path.write_bytes(b'fixture')))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(coordinates)))]))))
    monkeypatch.setattr(vision, '_get_vision_client', lambda: (client, 'fixture'))
    click = Mock(return_value=click_result)
    monkeypatch.setattr(computer, 'mouse_click', click)
    result = computer.click_screen_element('Calculator', 'Equals')
    assert result.startswith(expected)
    if click_result is None:
        click.assert_not_called()
    else:
        assert click.call_args.kwargs['target_window'] == 'Calculator'


def test_app_alias_is_used_for_launch(monkeypatch):
    from tools import computer_use_tools as computer
    monkeypatch.setattr(computer, 'is_desktop_available', lambda: (True, 'OK'))
    monkeypatch.setattr(computer, '_bring_app_window_to_foreground', lambda *args, **kwargs: True)
    monkeypatch.setattr(computer, 'verify_foreground_window', lambda _: (True, 'OK'))
    launch = Mock()
    monkeypatch.setattr(computer.subprocess, 'Popen', launch)
    assert computer.open_app('calculator').startswith('SUCCESS:')
    assert '"calc"' in launch.call_args.args[0]
