"""Exercise the production activation path with injected OS boundaries."""
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def activation(monkeypatch):
    from tools import computer_use_tools as computer
    window = SimpleNamespace(_hWnd=123, left=100, top=50, width=400, height=600)
    windows = SimpleNamespace(getActiveWindow=Mock(return_value=window))
    mouse = SimpleNamespace(FAILSAFE=True, click=Mock())
    monkeypatch.setitem(sys.modules, 'pygetwindow', windows)
    monkeypatch.setattr(computer, 'pyautogui', mouse, raising=False)
    monkeypatch.setattr(computer, 'PYAUTOGUI_AVAILABLE', True)
    monkeypatch.setattr(computer, '_enforce_desktop_and_target', Mock(return_value=(True, 'OK')))
    monkeypatch.setattr(computer, 'verify_foreground_window', Mock(return_value=(True, 'VERIFIED')))
    return computer, windows, mouse, window


def test_activation_uses_actual_foreground_window_and_reverifies(activation):
    computer, windows, mouse, _ = activation
    assert computer._activate_window_input('Calculator') == (True, 'VERIFIED')
    mouse.click.assert_called_once_with(250, 65)
    computer.verify_foreground_window.assert_called_once_with('Calculator')
    assert mouse.FAILSAFE is True


@pytest.mark.parametrize('failure', ['locked', 'focus_changed', 'different_handle', 'missing_window', 'failsafe'])
def test_activation_never_reports_success_on_guard_or_input_failure(activation, failure):
    computer, windows, mouse, window = activation
    if failure == 'locked':
        computer._enforce_desktop_and_target.return_value = (False, 'DESKTOP_UNAVAILABLE')
    elif failure == 'focus_changed':
        computer._enforce_desktop_and_target.side_effect = [(True, 'OK'), (False, 'WINDOW_MISMATCH')]
    elif failure == 'different_handle':
        windows.getActiveWindow.side_effect = [window, SimpleNamespace(_hWnd=999)]
    elif failure == 'missing_window':
        windows.getActiveWindow.return_value = None
    else:
        mouse.click.side_effect = RuntimeError('fixture failsafe')
    ok, reason = computer._activate_window_input('Calculator')
    assert not ok and reason
    if failure != 'failsafe':
        mouse.click.assert_not_called()
