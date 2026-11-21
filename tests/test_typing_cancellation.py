"""No physical input: inject the OS boundary and stop a real worker mid-input."""
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.execution_control import cancellation_requested, run_tool
from tools import computer_use_tools as computer


@pytest.fixture
def keyboard(monkeypatch):
    device = SimpleNamespace(FAILSAFE=False, typewrite=Mock(), hotkey=Mock(), press=Mock())
    monkeypatch.setattr(computer, 'pyautogui', device, raising=False)
    monkeypatch.setattr(computer, 'PYAUTOGUI_AVAILABLE', True)
    monkeypatch.setattr(computer, 'is_desktop_available', Mock(return_value=(True, 'OK')))
    monkeypatch.setattr(computer, 'verify_foreground_window', Mock(return_value=(True, 'OK')))
    return device


def test_stop_interrupts_worker_before_remaining_text_or_enter(keyboard):
    started, release, cancelled = Event(), Event(), Event()

    def first_batch(*args, **kwargs):
        started.set()
        assert release.wait(2)

    keyboard.typewrite.side_effect = first_batch
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(run_tool, computer.keyboard_type,
                             dict(target_window='Notepad', text='x' * 1000, press_enter=True),
                             cancelled.is_set)
        try:
            assert started.wait(2)
            cancelled.set()
        finally:
            release.set()
        assert 'cancelled' in result.result(timeout=2)
        keyboard.typewrite.assert_called_once()
        assert len(keyboard.typewrite.call_args.args[0]) <= 8
        keyboard.press.assert_not_called()
        keyboard.hotkey.assert_not_called()
        assert pool.submit(cancellation_requested).result() is False


def test_focus_change_stops_remaining_text_and_enter(keyboard):
    computer.verify_foreground_window.side_effect = [(True, 'OK'), (True, 'OK'), (False, 'WINDOW_MISMATCH')]
    result = computer.keyboard_type('Notepad', 'a' * 100, press_enter=True)
    assert 'WINDOW_MISMATCH' in result and 'partial' in result
    keyboard.typewrite.assert_called_once()
    keyboard.press.assert_not_called()


def test_failsafe_or_partial_input_error_never_retries_as_paste(keyboard):
    keyboard.typewrite.side_effect = RuntimeError('failsafe')
    assert 'ERROR' in computer.keyboard_type('Notepad', 'hello', press_enter=True)
    keyboard.hotkey.assert_not_called()
    keyboard.press.assert_not_called()
    assert keyboard.FAILSAFE


def test_typing_preserves_all_text_then_enter(keyboard):
    text = 'First line\nSecond line\t1000'
    assert 'SUCCESS' in computer.keyboard_type('Notepad', text, press_enter=True)
    assert ''.join(call.args[0] for call in keyboard.typewrite.call_args_list) == text
    keyboard.press.assert_called_once_with('enter')


def test_cancelled_worker_never_starts_and_context_resets_on_error():
    fn = Mock()
    assert 'cancelled' in run_tool(fn, {}, lambda: True)
    fn.assert_not_called()
    assert not cancellation_requested()
    fn.side_effect = RuntimeError('fixture')
    with pytest.raises(RuntimeError):
        run_tool(fn, {}, lambda: False)
    assert not cancellation_requested()


def test_unicode_uses_one_paste_and_restores_clipboard(keyboard, monkeypatch):
    clipboard = SimpleNamespace(paste=Mock(return_value='prior clipboard'), copy=Mock())
    monkeypatch.setitem(sys.modules, 'pyperclip', clipboard)
    monkeypatch.setattr(computer.time, 'sleep', lambda _: None)
    assert 'SUCCESS' in computer.keyboard_type('Notepad', 'Café ₹25', press_enter=True)
    keyboard.typewrite.assert_not_called()
    keyboard.hotkey.assert_called_once_with('ctrl', 'v')
    assert [call.args[0] for call in clipboard.copy.call_args_list] == ['Café ₹25', 'prior clipboard']
    keyboard.press.assert_called_once_with('enter')
