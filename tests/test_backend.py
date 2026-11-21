import os
import time
import pytest
from core.auth import verify_token, redact_secrets, OWNER_TOKEN, RateLimiter
from core.approvals import (
    classify_tool_call,
    approval_manager,
    POLICY_READ,
    POLICY_CONFIRM,
    POLICY_CRITICAL,
    POLICY_BLOCKED
)
from core.session import session_manager, Session
from core.speaker import clean_text_for_speech, ElevenLabsSpeaker

def test_auth_verification():
    assert verify_token(OWNER_TOKEN) is True
    assert verify_token("invalid_token_12345") is False
    assert verify_token("") is False
    assert verify_token(None) is False

def test_secret_redaction():
    fake_key = "sk-or-v1-0123456789abcdef0123456789abcdef"
    fake_bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    raw_text = f"My key is {fake_key} and authorization is {fake_bearer}"
    redacted = redact_secrets(raw_text)
    assert fake_key not in redacted
    assert "[REDACTED_OPENROUTER_KEY]" in redacted or "[REDACTED" in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted or "[REDACTED" in redacted

def test_tool_policies():
    # READ policies
    p, _ = classify_tool_call("get_system_stats", {})
    assert p == POLICY_READ
    p, _ = classify_tool_call("read_file", {"path": "C:\\test.txt"})
    assert p == POLICY_READ

    # CONFIRM policies
    p, _ = classify_tool_call("execute_powershell", {"command": "Get-Process"})
    assert p == POLICY_CONFIRM
    p, _ = classify_tool_call("write_file", {"path": "C:\\my_script.py", "content": "print(1)"})
    assert p == POLICY_CONFIRM

    # CRITICAL policies
    p, _ = classify_tool_call("execute_powershell", {"command": "Remove-Item -Path C:\\junk.txt"})
    assert p == POLICY_CRITICAL
    p, _ = classify_tool_call("execute_powershell", {"command": "winget install python"})
    assert p == POLICY_CRITICAL

    # BLOCKED policies
    p, _ = classify_tool_call("execute_powershell", {"command": "diskpart"})
    assert p == POLICY_BLOCKED
    p, _ = classify_tool_call("execute_powershell", {"command": "format C:"})
    assert p == POLICY_BLOCKED
    p, _ = classify_tool_call("execute_powershell", {"command": "Remove-Item -Recurse C:\\"})
    assert p == POLICY_BLOCKED

def test_approvals_lifecycle():
    req = approval_manager.create_request(
        session_id="test_sess",
        tool="write_file",
        args={"path": "test.txt", "content": "hello"},
        policy_level=POLICY_CONFIRM,
        summary="Write test file"
    )
    assert req.status == "PENDING"
    assert req.single_use is True

    # Test approve
    success, msg = approval_manager.decide(req.id, "approve")
    assert success is True
    assert req.status == "APPROVED"

    # Single-use check: second attempt should fail
    success2, msg2 = approval_manager.decide(req.id, "approve")
    assert success2 is False

def test_session_isolation_and_cancellation():
    sess1 = session_manager.get_or_create_session("session_alpha")
    sess2 = session_manager.get_or_create_session("session_beta")

    sess1.add_message("user", "Hello Alpha")
    sess2.add_message("user", "Hello Beta")

    assert len(sess1.messages) >= 1
    assert "Alpha" in sess1.messages[-1]["content"]
    assert "Beta" in sess2.messages[-1]["content"]

    # Test cancellation
    sess1.cancel()
    assert sess1.is_cancelled is True
    assert sess2.is_cancelled is False

def test_clean_text_for_speech():
    raw_markdown = "Here is the code: ```python\nprint('hello')\n```. Check out [Google](https://google.com)."
    clean = clean_text_for_speech(raw_markdown)
    assert "```" not in clean
    assert "print('hello')" not in clean
    assert "https://google.com" not in clean
    assert "Google" in clean

def test_rate_limiter():
    limiter = RateLimiter(max_requests=3, window_seconds=10)
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is False
    assert limiter.is_allowed("client_2") is True

def test_ca_certificate_endpoint():
    from fastapi.testclient import TestClient
    import server
    with TestClient(server.app) as client:
        res = client.get("/ca.crt")
        assert res.status_code == 200
        assert "application/x-x509-ca-cert" in res.headers.get("content-type", "")
        assert b"BEGIN CERTIFICATE" in res.content

def test_auth_status_never_exposes_token(monkeypatch):
    from fastapi.testclient import TestClient
    import server
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    with TestClient(server.app) as client:
        res = client.get("/api/auth/status")
        assert res.status_code == 200
        data = res.json()
        assert "token" not in data
        assert OWNER_TOKEN not in res.text

def test_seamless_local_auth_restrictions(monkeypatch):
    from fastapi.testclient import TestClient
    from starlette.requests import Request
    import server

    # 1. When REQUIRE_AUTH=false and loopback request
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    with TestClient(server.app) as client:
        # Loopback with valid local Host succeeds
        res = client.get("/api/system/telemetry")
        assert res.status_code == 200

    # 2. Remote IP must NOT bypass auth even if REQUIRE_AUTH=false
    # Simulate non-loopback client
    req_remote = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/api/system/telemetry",
        "headers": [(b"host", b"192.168.1.30:8000")],
        "client": ("192.168.1.150", 52140)
    })
    assert server.is_local_request(req_remote) is False
    with pytest.raises(Exception) as excinfo:
        server.authenticate_request(req_remote, None)
    assert excinfo.value.status_code == 401

    # 3. Non-local Host header rejected
    req_bad_host = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/api/system/telemetry",
        "headers": [(b"host", b"evil.com")],
        "client": ("127.0.0.1", 52140)
    })
    assert server.is_local_request(req_bad_host) is False


