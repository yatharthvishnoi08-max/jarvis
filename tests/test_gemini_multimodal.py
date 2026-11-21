"""
Tests for Google Gemini Brain Integration, Smart Failover, and Expanded Tool Suite.
"""

import os
from pathlib import Path
import pytest
from core.client import get_client, get_active_provider, SmartLLMClient
from core.approvals import classify_tool_call, POLICY_READ, POLICY_CONFIRM
from core.agent import TOOL_SCHEMAS, TOOL_FUNCTIONS
from tools.system_tools import get_battery_status, get_clipboard, set_clipboard, find_files, manage_application
from tools.multimodal_tools import capture_screen

BASE_DIR = Path(__file__).resolve().parent.parent

def test_active_provider_gemini():
    provider = get_active_provider()
    assert provider == "gemini", "Default active provider should be 'gemini'"

def test_smart_client_initialization():
    client, model_name = get_client()
    assert isinstance(client, SmartLLMClient)
    assert model_name in ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.6-flash"]
    assert len(client.fallback_models) >= 2
    assert client.backup_model == "meta-llama/llama-3.3-70b-instruct"

def test_total_registered_tools_count():
    assert len(TOOL_SCHEMAS) >= 33, f"Expected at least 33 tools, found {len(TOOL_SCHEMAS)}"
    assert len(TOOL_FUNCTIONS) >= 33, f"Expected at least 33 tool functions, found {len(TOOL_FUNCTIONS)}"
    
    # Check new tools are registered in schemas
    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    expected_new = [
        "analyze_image", "capture_screen", "analyze_screen",
        "get_battery_status", "get_clipboard", "set_clipboard",
        "control_media", "manage_application", "find_files"
    ]
    for tool_name in expected_new:
        assert tool_name in schema_names, f"Tool '{tool_name}' must be present in TOOL_SCHEMAS"
        assert tool_name in TOOL_FUNCTIONS, f"Tool '{tool_name}' must be present in TOOL_FUNCTIONS"

def test_approvals_policy_classification():
    pol, _ = classify_tool_call("get_battery_status", {})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("analyze_image", {"image_path": "test.png"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("find_files", {"pattern": "*.py"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("manage_application", {"action": "list"})
    assert pol == POLICY_READ

    pol, _ = classify_tool_call("manage_application", {"action": "close", "name": "notepad"})
    assert pol == POLICY_CONFIRM

def test_battery_status_execution():
    res = get_battery_status()
    assert ("Battery Level:" in res) or ("No battery detected" in res)

def test_find_files_execution():
    res = find_files("*.ico", str(BASE_DIR))
    assert "jarvis.ico" in res

def test_clipboard_operations():
    test_str = "JARVIS_TEST_CLIPBOARD_STRING"
    set_res = set_clipboard(test_str)
    assert "SUCCESS" in set_res
    get_res = get_clipboard()
    assert test_str in get_res
