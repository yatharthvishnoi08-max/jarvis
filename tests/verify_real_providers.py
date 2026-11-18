import os
import json
import asyncio
import urllib.request
import ssl
from pathlib import Path
from dotenv import load_dotenv
import websockets

load_dotenv()
TOKEN = os.getenv("JARVIS_AUTH_TOKEN")
if not TOKEN:
    raise SystemExit("JARVIS_AUTH_TOKEN not found in .env")

CERTS_DIR = Path(__file__).resolve().parent.parent / "certs"

async def test_real_providers():
    print("[Test] Starting live provider verification on Windows...")
    
    # 1. Verify REST API / telemetry
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/system/telemetry",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    with urllib.request.urlopen(req) as resp:
        telemetry = json.loads(resp.read().decode())
        print(f"[Test] Telemetry OK - Active Model: {telemetry.get('active_model')}, Voice Configured: {telemetry.get('voice_configured')}")
        assert telemetry.get("voice_configured") is True, "ElevenLabs API key not configured"

    # 2. Test CA Certificate download endpoint
    ca_req = urllib.request.Request("http://127.0.0.1:8000/jarvis-ca.crt")
    with urllib.request.urlopen(ca_req) as resp:
        ca_data = resp.read()
        assert b"BEGIN CERTIFICATE" in ca_data, "CA certificate invalid"
        print(f"[Test] CA Certificate download endpoint verified ({len(ca_data)} bytes)")

    # 3. Test HTTPS endpoint with SSL context
    ctx = ssl.create_default_context(cafile=str(CERTS_DIR / "ca.crt"))
    https_req = urllib.request.Request(
        "https://127.0.0.1:8443/api/auth/verify",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    with urllib.request.urlopen(https_req, context=ctx) as resp:
        auth_res = json.loads(resp.read().decode())
        print(f"[Test] HTTPS /api/auth/verify verified: {auth_res}")
        assert auth_res.get("status") == "authenticated"

    # 4. Create Session A
    create_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/sessions",
        data=json.dumps({"title": "Test Session A"}).encode("utf-8"),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(create_req) as resp:
        sess_a = json.loads(resp.read().decode())["session"]
        session_a_id = sess_a["id"]
        print(f"[Test] Created Session A: {session_a_id}")

    # 5. Connect WebSocket to Session A
    ws_url = f"ws://127.0.0.1:8000/ws?token={TOKEN}"
    print("[Test] Connecting WebSocket to send prompt: 'Remember mango as the word for this chat'...")
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "chat",
            "session_id": session_a_id,
            "text": "Remember mango as the word for this chat.",
            "voice": True,
            "text_first": True
        }))

        # Read responses until complete turn
        first_reply = None
        audio_id_first = None
        while True:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            if mtype == "approval_required":
                req_id = msg["request"]["id"]
                print(f"[Test] Approval required for {msg['request']['tool']} - rejecting to preserve session isolation")
                await ws.send(json.dumps({
                    "type": "approval_decision",
                    "request_id": req_id,
                    "decision": "reject"
                }))
            elif mtype == "response":
                first_reply = msg.get("text", "")
                print(f"[Test] Session A First Reply: {first_reply[:80]}...")
            elif mtype == "reply_audio":
                audio_id_first = msg.get("audio_id")
                print(f"[Test] Session A First Audio ID: {audio_id_first}")
                break
            elif mtype == "error":
                raise RuntimeError(f"WebSocket error: {msg}")

    print("[Test] Disconnected WebSocket to test reconnect persistence.")
    await asyncio.sleep(1)

    # 6. Reconnect WebSocket to Session A and query the word
    print("[Test] Reconnecting WebSocket to Session A to ask: 'What word did I give you?'...")
    reply_text = None
    reply_audio_id = None
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "chat",
            "session_id": session_a_id,
            "text": "What word did I give you?",
            "voice": True,
            "text_first": True
        }))

        while True:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            if mtype == "approval_required":
                req_id = msg["request"]["id"]
                print(f"[Test] Recall turn: approval required for {msg['request']['tool']} - rejecting to answer from chat context")
                await ws.send(json.dumps({
                    "type": "approval_decision",
                    "request_id": req_id,
                    "decision": "reject"
                }))
            elif mtype == "response":
                reply_text = msg.get("text", "")
                print(f"[Test] Session A Recall Reply: {reply_text}")
            elif mtype == "reply_audio":
                reply_audio_id = msg.get("audio_id")
                print(f"[Test] Session A Recall Audio ID: {reply_audio_id}")
                break
            elif mtype == "error":
                raise RuntimeError(f"WebSocket error: {msg}")

    # Verify mango in response
    assert reply_text is not None, "Did not receive recall reply text"
    assert "mango" in reply_text.lower(), f"Expected 'mango' in recall reply, got: '{reply_text}'"
    print("[Test] PASS: Model successfully recalled 'mango' after reconnect!")

    # Verify ElevenLabs audio is playable
    assert reply_audio_id is not None, "Did not receive audio_id from ElevenLabs"
    audio_req = urllib.request.Request(f"http://127.0.0.1:8000/api/audio/{reply_audio_id}")
    with urllib.request.urlopen(audio_req) as resp:
        content_type = resp.headers.get("Content-Type")
        audio_data = resp.read()
        assert resp.status == 200
        assert "audio/mpeg" in content_type
        assert len(audio_data) > 1000, f"Audio file is too small ({len(audio_data)} bytes)"
        print(f"[Test] PASS: ElevenLabs returned valid playable audio ({len(audio_data)} bytes, {content_type})")

    # 7. Create Session B to verify session isolation
    create_b_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/sessions",
        data=json.dumps({"title": "Test Session B"}).encode("utf-8"),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(create_b_req) as resp:
        sess_b = json.loads(resp.read().decode())["session"]
        session_b_id = sess_b["id"]
        print(f"[Test] Created Session B: {session_b_id}")

    # Query in Session B
    reply_b_text = None
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "chat",
            "session_id": session_b_id,
            "text": "What word did I give you?",
            "voice": False,
            "text_first": True
        }))

        while True:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            if mtype == "approval_required":
                req_id = msg["request"]["id"]
                await ws.send(json.dumps({
                    "type": "approval_decision",
                    "request_id": req_id,
                    "decision": "reject"
                }))
            elif mtype == "response":
                reply_b_text = msg.get("text", "")
                print(f"[Test] Session B Reply: {reply_b_text}")
                break
            elif mtype == "error":
                raise RuntimeError(f"WebSocket error: {msg}")

    # Verify mango does NOT carry over to Session B
    assert reply_b_text is not None
    assert "mango" not in reply_b_text.lower(), f"Isolation failure: 'mango' leaked into Session B! Reply: {reply_b_text}"
    print("[Test] PASS: Session isolation verified - 'mango' did not carry over to Session B!")

    # 8. Test WSS (Secure WebSocket) over HTTPS
    wss_url = f"wss://127.0.0.1:8443/ws?token={TOKEN}"
    print("[Test] Testing Secure WebSocket (WSS) over HTTPS port 8443...")
    async with websockets.connect(wss_url, ssl=ctx) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
        pong = json.loads(resp)
        assert pong.get("type") == "pong"
        print("[Test] PASS: Secure WebSocket (WSS) ping/pong verified over HTTPS port 8443!")

    print("\n" + "="*50)
    print("ALL WINDOWS REAL-PROVIDER VERIFICATIONS PASSED!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_real_providers())
