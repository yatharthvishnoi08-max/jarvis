"""
Unit and Functional Tests for J.A.R.V.I.S. Computer Use & OS Automation Tools.
Separates mocked unit tests from opt-in live smoke tests to prevent unprompted mouse/OS changes.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from core.agent import TOOL_SCHEMAS, TOOL_FUNCTIONS
from core.approvals import classify_tool_call, POLICY_READ, POLICY_CRITICAL
from tools.computer_use_tools import (
    WINDOWS_SETTINGS_MAP,
    get_mouse_position,
    configure_laptop_permissions,
    open_windows_settings,
    open_app,
    focus_window,
    mouse_move,
    mouse_click,
    mouse_scroll,
    mouse_drag,
    keyboard_type,
    keyboard_press,
    keyboard_hotkey,
    click_screen_element,
    is_desktop_available,
    verify_foreground_window,
)

def test_total_tools_count_50():
    assert len(TOOL_SCHEMAS) == 50, f"Expected 50 tool schemas, got {len(TOOL_SCHEMAS)}"
    assert len(TOOL_FUNCTIONS) == 50, f"Expected 50 tool functions, got {len(TOOL_FUNCTIONS)}"

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

def test_target_window_required_in_schemas():
    tools_with_target = [
        "mouse_click", "mouse_move", "mouse_scroll", "mouse_drag",
        "keyboard_type", "keyboard_press", "keyboard_hotkey", "click_screen_element"
    ]
    for s in TOOL_SCHEMAS:
        fn_name = s["function"]["name"]
        if fn_name in tools_with_target:
            props = s["function"]["parameters"]["properties"]
            req = s["function"]["parameters"]["required"]
            assert "target_window" in props, f"'{fn_name}' parameter schema must define target_window"
            assert "target_window" in req, f"'{fn_name}' must require target_window"

def test_get_mouse_position():
    with patch("pyautogui.position", return_value=(200, 300)), patch("pyautogui.size", return_value=(1920, 1080)):
        res = get_mouse_position()
        assert "Mouse Position: (200, 300)" in res
        assert "1920x1080" in res

def test_windows_settings_uri_map():
    assert "microphone" in WINDOWS_SETTINGS_MAP
    assert WINDOWS_SETTINGS_MAP["microphone"] == "ms-settings:privacy-microphone"
    assert "camera" in WINDOWS_SETTINGS_MAP
    assert "apps" in WINDOWS_SETTINGS_MAP
    assert "security" in WINDOWS_SETTINGS_MAP

def test_configure_laptop_permissions_mocked():
    with patch("subprocess.run", return_value=MagicMock(stdout="SUCCESS", stderr="", returncode=0)):
        res = configure_laptop_permissions()
        assert "Windows Laptop Permissions Configuration:" in res

def test_approvals_policies():
    pol, _ = classify_tool_call("mouse_click", {"target_window": "calc", "x": 100, "y": 100})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("keyboard_type", {"target_window": "calc", "text": "hello"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("open_windows_settings", {"page": "microphone"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("click_screen_element", {"target_window": "calc", "target_description": "Start button"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("run_elevated_command", {"command": "net start"})
    assert pol == POLICY_CRITICAL

def test_interactive_spawner_functions_defined():
    from tools.computer_use_tools import _launch_interactive_app, _bring_app_window_to_foreground, COMMON_APP_MAP
    assert callable(_launch_interactive_app)
    assert callable(_bring_app_window_to_foreground)
    assert "telegram" in COMMON_APP_MAP
    assert "chrome" in COMMON_APP_MAP

def test_input_tools_reject_empty_target_window():
    with patch("pyautogui.moveTo") as mock_move, \
         patch("pyautogui.click") as mock_click, \
         patch("pyautogui.typewrite") as mock_type:

        assert "ERROR: An explicit target_window is required" in mouse_move("", 100, 100)
        assert "ERROR: An explicit target_window is required" in mouse_click("   ", 100, 100)
        assert "ERROR: An explicit target_window is required" in keyboard_type("", "test")
        assert "ERROR: An explicit target_window is required" in keyboard_press("", "enter")
        assert "ERROR: An explicit target_window is required" in keyboard_hotkey("", ["ctrl", "c"])
        assert "ERROR: An explicit target_window is required" in mouse_scroll("", 5)
        assert "ERROR: An explicit target_window is required" in mouse_drag("", 0, 0, 10, 10)
        assert "ERROR: An explicit target_window is required" in click_screen_element("", "button")

        mock_move.assert_not_called()
        mock_click.assert_not_called()
        mock_type.assert_not_called()

def test_mocked_locked_desktop_prevents_os_input():
    with patch("tools.computer_use_tools.is_desktop_available", return_value=(False, "Desktop locked")), \
         patch("pyautogui.moveTo") as mock_move, \
         patch("pyautogui.click") as mock_click, \
         patch("pyautogui.typewrite") as mock_type:

        res1 = mouse_move("calc", 100, 100)
        assert "ERROR: Desktop unavailable" in res1

        res2 = mouse_click("calc", 100, 100)
        assert "ERROR: Desktop unavailable" in res2

        res3 = keyboard_type("calc", "123")
        assert "ERROR: Desktop unavailable" in res3

        mock_move.assert_not_called()
        mock_click.assert_not_called()
        mock_type.assert_not_called()

def test_mocked_wrong_foreground_prevents_os_input():
    with patch("tools.computer_use_tools.is_desktop_available", return_value=(True, "DESKTOP_AVAILABLE")), \
         patch("tools.computer_use_tools.verify_foreground_window", return_value=(False, "WINDOW_MISMATCH: Foreground is Notepad")), \
         patch("pyautogui.moveTo") as mock_move, \
         patch("pyautogui.click") as mock_click, \
         patch("pyautogui.typewrite") as mock_type:

        res1 = mouse_move("calc", 100, 100)
        assert "ERROR: Foreground window verification failed" in res1

        res2 = mouse_click("calc", 100, 100)
        assert "ERROR: Foreground window verification failed" in res2

        res3 = keyboard_type("calc", "123")
        assert "ERROR: Foreground window verification failed" in res3

        mock_move.assert_not_called()
        mock_click.assert_not_called()
        mock_type.assert_not_called()

def test_open_app_and_focus_window_reject_empty_target():
    assert "ERROR: An explicit target application is required" in open_app("")
    assert "ERROR: An explicit target application is required" in open_app("   ")
    assert "ERROR: An explicit window title keyword is required" in focus_window("")
    assert "ERROR: An explicit window title keyword is required" in focus_window("   ")

def test_open_app_fails_when_foreground_verification_fails():
    with patch("tools.computer_use_tools.is_desktop_available", return_value=(True, "DESKTOP_AVAILABLE")), \
         patch("tools.computer_use_tools._launch_interactive_app", return_value=(True, "Dispatched")), \
         patch("tools.computer_use_tools._bring_app_window_to_foreground", return_value=True), \
         patch("tools.computer_use_tools.verify_foreground_window", return_value=(False, "WINDOW_MISMATCH")):

        res = open_app("calc")
        assert "ERROR: Launched 'calc', but failed to become visible foreground window" in res

def test_focus_window_fails_when_foreground_verification_fails():
    with patch("tools.computer_use_tools.is_desktop_available", return_value=(True, "DESKTOP_AVAILABLE")), \
         patch("tools.computer_use_tools._bring_app_window_to_foreground", return_value=False), \
         patch("tools.computer_use_tools.verify_foreground_window", return_value=(False, "WINDOW_MISMATCH")):

        res = focus_window("nonexistent_app_window")
        assert "ERROR: Failed to bring window matching 'nonexistent_app_window' to visible foreground" in res

def test_pyautogui_failsafe_intact():
    import pyautogui
    assert pyautogui.FAILSAFE is True
    with patch("pyautogui.moveTo") as mock_move, \
         patch("tools.computer_use_tools.is_desktop_available", return_value=(True, "OK")), \
         patch("tools.computer_use_tools.verify_foreground_window", return_value=(True, "VERIFIED")):
        mouse_move("test_window", 10, 10, duration=0.01)
        assert pyautogui.FAILSAFE is True
        mock_move.assert_called_once()

def test_is_desktop_available_real():
    available, msg = is_desktop_available()
    assert isinstance(available, bool)
    assert isinstance(msg, str)

def test_is_desktop_available_mocked_locked():
    with patch("ctypes.windll.user32.OpenInputDesktop", return_value=0):
        available, msg = is_desktop_available()
        assert available is False
        assert "DESKTOP_UNAVAILABLE" in msg

def test_verify_foreground_window_mismatch():
    matched, msg = verify_foreground_window("non_existent_application_xyz_9999")
    assert matched is False
    assert "WINDOW_MISMATCH" in msg

def test_verify_foreground_window_mock_match():
    def mock_get_window_text_w(hwnd, buff, length):
        buff.value = "Calculator"
        return len(buff.value)

    def mock_get_class_name_w(hwnd, buff, length):
        buff.value = "ApplicationFrameWindow"
        return len(buff.value)

    with patch("ctypes.windll.user32.GetForegroundWindow", return_value=12345), \
         patch("ctypes.windll.user32.GetWindowTextLengthW", return_value=10), \
         patch("ctypes.windll.user32.GetWindowTextW", side_effect=mock_get_window_text_w), \
         patch("ctypes.windll.user32.GetClassNameW", side_effect=mock_get_class_name_w), \
         patch("ctypes.windll.user32.GetWindowThreadProcessId", return_value=0):
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

# --- OPT-IN LIVE SMOKE TESTS (Only run when JARVIS_LIVE_SMOKE=1) ---
@pytest.mark.skipif(not os.getenv("JARVIS_LIVE_SMOKE"), reason="Set JARVIS_LIVE_SMOKE=1 to run live host interaction smoke tests")
def test_live_smoke_open_calc_and_type():
    res_open = open_app("calc")
    assert "SUCCESS" in res_open
    res_type = keyboard_type("calc", "17*23=")
    assert "SUCCESS" in res_type
