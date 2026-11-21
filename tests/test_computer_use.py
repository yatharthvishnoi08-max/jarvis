"""
Unit and Functional Tests for J.A.R.V.I.S. Computer Use & OS Automation Tools.
"""

import pytest
from core.agent import TOOL_SCHEMAS, TOOL_FUNCTIONS
from core.approvals import classify_tool_call, POLICY_READ, POLICY_CRITICAL
from tools.computer_use_tools import (
    WINDOWS_SETTINGS_MAP,
    get_mouse_position,
    configure_laptop_permissions,
    open_windows_settings,
    open_app,
)

def test_total_tools_count_47():
    assert len(TOOL_SCHEMAS) == 47, f"Expected 47 tool schemas, got {len(TOOL_SCHEMAS)}"
    assert len(TOOL_FUNCTIONS) == 47, f"Expected 47 tool functions, got {len(TOOL_FUNCTIONS)}"

def test_computer_use_schemas_registered():
    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    expected_tools = [
        "mouse_click", "mouse_move", "mouse_scroll", "mouse_drag",
        "keyboard_type", "keyboard_press", "keyboard_hotkey",
        "get_mouse_position", "open_windows_settings", "open_app",
        "focus_window", "click_screen_element", "configure_laptop_permissions",
        "run_elevated_command"
    ]
    for tool_name in expected_tools:
        assert tool_name in schema_names, f"Tool '{tool_name}' must be in TOOL_SCHEMAS"
        assert tool_name in TOOL_FUNCTIONS, f"Tool '{tool_name}' must be in TOOL_FUNCTIONS"

def test_get_mouse_position():
    res = get_mouse_position()
    assert "Mouse Position:" in res or "Screen Resolution:" in res

def test_windows_settings_uri_map():
    assert "microphone" in WINDOWS_SETTINGS_MAP
    assert WINDOWS_SETTINGS_MAP["microphone"] == "ms-settings:privacy-microphone"
    assert "camera" in WINDOWS_SETTINGS_MAP
    assert "apps" in WINDOWS_SETTINGS_MAP
    assert "security" in WINDOWS_SETTINGS_MAP

def test_configure_laptop_permissions():
    res = configure_laptop_permissions()
    assert "Windows Laptop Permissions Configuration:" in res
    assert "Microphone privacy" in res or "PowerShell" in res

def test_approvals_policies():
    pol, _ = classify_tool_call("mouse_click", {"x": 100, "y": 100})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("keyboard_type", {"text": "hello"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("open_windows_settings", {"page": "microphone"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("click_screen_element", {"target_description": "Start button"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("run_elevated_command", {"command": "net start"})
    assert pol == POLICY_CRITICAL

def test_interactive_spawner_functions_defined():
    from tools.computer_use_tools import _launch_interactive_app, _bring_app_window_to_foreground, COMMON_APP_MAP
    assert callable(_launch_interactive_app)
    assert callable(_bring_app_window_to_foreground)
    assert "telegram" in COMMON_APP_MAP
    assert "chrome" in COMMON_APP_MAP

def test_open_app_settings_delegation():
    res = open_app("microphone settings")
    assert "SUCCESS: Opened Windows Settings" in res
    assert "privacy-microphone" in res

def test_pyautogui_failsafe_intact():
    import pyautogui
    from tools.computer_use_tools import mouse_move, mouse_click
    assert pyautogui.FAILSAFE is True
    # Test that mouse functions keep FAILSAFE enabled
    mouse_move(10, 10, duration=0.01)
    assert pyautogui.FAILSAFE is True

def test_is_desktop_available_real():
    from tools.computer_use_tools import is_desktop_available
    available, msg = is_desktop_available()
    assert isinstance(available, bool)
    assert isinstance(msg, str)

def test_is_desktop_available_mocked_locked():
    from unittest.mock import patch
    import sys
    from tools.computer_use_tools import is_desktop_available

    with patch("ctypes.windll.user32.OpenInputDesktop", return_value=0):
        available, msg = is_desktop_available()
        assert available is False
        assert "DESKTOP_UNAVAILABLE" in msg

def test_verify_foreground_window_mismatch():
    from tools.computer_use_tools import verify_foreground_window
    matched, msg = verify_foreground_window("non_existent_application_xyz_9999")
    assert matched is False
    assert "WINDOW_MISMATCH" in msg

def test_verify_foreground_window_mock_match():
    from unittest.mock import patch
    import ctypes
    from tools.computer_use_tools import verify_foreground_window

    def mock_get_window_text_w(hwnd, buff, length):
        buff.value = "Calculator"
        return len(buff.value)

    def mock_get_class_name_w(hwnd, buff, length):
        buff.value = "ApplicationFrameWindow"
        return len(buff.value)

    with patch("ctypes.windll.user32.GetForegroundWindow", return_value=12345):
        with patch("ctypes.windll.user32.GetWindowTextLengthW", return_value=10):
            with patch("ctypes.windll.user32.GetWindowTextW", side_effect=mock_get_window_text_w):
                with patch("ctypes.windll.user32.GetClassNameW", side_effect=mock_get_class_name_w):
                    with patch("ctypes.windll.user32.GetWindowThreadProcessId", return_value=0):
                        matched, msg = verify_foreground_window("calculator")
                        assert matched is True
                        assert "VERIFIED" in msg

def test_session_cancellation_lifecycle():
    from core.session import Session
    sess = Session(session_id="test_cancel_sess")
    assert sess.is_cancelled is False

    sess.cancel()
    assert sess.is_cancelled is True

    sess.reset_cancellation()
    assert sess.is_cancelled is False

def test_approval_manager_cancellation_flow():
    from core.approvals import ApprovalManager
    am = ApprovalManager()
    req = am.create_request(
        session_id="sess_test_123",
        tool="run_elevated_command",
        args={"command": "dir"},
        policy_level="CRITICAL",
        summary="Test critical action"
    )
    assert req.status == "PENDING"
    assert not req.event.is_set()

    am.cancel_session_approvals("sess_test_123")
    assert req.status == "CANCELLED"
    assert req.event.is_set()

