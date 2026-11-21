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
