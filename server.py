import os
import json
import time
import socket
import asyncio
import psutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Security,
    Depends,
    Request,
    status
)
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from openai import APIStatusError, APITimeoutError

from core.auth import verify_token, redact_secrets, global_rate_limiter, OWNER_TOKEN, is_auth_required
from core.audit import audit_logger
from core.approvals import approval_manager
from core.session import session_manager, Session
from core.speaker import ElevenLabsSpeaker
from core.agent import JarvisAgent
from core.client import ModelConfigurationError
from tools import planner
from tools.meta_tools import EMPLOYEES_DIR, MEMORY_FILE, read_memory, update_employee_sop, log_learned_rule

BASE_DIR = Path(__file__).resolve().parent
WEB_DIST_DIR = BASE_DIR / "web_dist"
LEGACY_HTML = BASE_DIR / "web" / "index.html"
START_TIME = time.time()

# Allowed origins: Localhost, LAN, Tailscale (both HTTP and HTTPS)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:8443",
    "https://127.0.0.1:8443",
    "https://localhost:8000",
    "https://127.0.0.1:8000",
]
env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else DEFAULT_ALLOWED_ORIGINS

app = FastAPI(title="JARVIS Interface v3 Core Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|100\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize core agent and speaker
agent = JarvisAgent()
speaker = ElevenLabsSpeaker()
security = HTTPBearer(auto_error=False)

def authenticate_request(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    if not is_auth_required():
        return True
    if not credentials or not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing owner authorization token."
        )
    return True

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_and_audit_middleware(request: Request, call_next):
    # Check max content length (10MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"error": "Payload exceeds 10MB limit."}
        )

    client_ip = request.client.host if request.client else "unknown"
    if not global_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Rate limit exceeded."}
        )

    response = await call_next(request)
    return response

def get_lan_and_tailscale_ips() -> Dict[str, List[str]]:
    lan_ips = []
    tailscale_ips = []
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip.startswith("100."):
                tailscale_ips.append(ip)
            elif not ip.startswith("127."):
                lan_ips.append(ip)
    except Exception:
        pass
    return {"lan": lan_ips or ["127.0.0.1"], "tailscale": tailscale_ips}

# ----------------- REST ENDPOINTS -----------------

@app.get("/api/auth/status")
async def get_auth_status():
    """Public endpoint returning whether authentication is required for this gateway."""
    required = is_auth_required()
    return {
        "auth_required": required,
        "token": OWNER_TOKEN if not required else None
    }

@app.get("/api/auth/verify")
async def verify_auth(auth: bool = Depends(authenticate_request)):
    required = is_auth_required()
    return {
        "status": "authenticated",
        "role": "owner",
        "auth_required": required,
        "token": OWNER_TOKEN if not required else None
    }

class LoginRequest(BaseModel):
    token: str


class ConversationTurn(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=16000)


@app.post("/api/chat")
async def basic_chat(turn: ConversationTurn, auth: bool = Depends(authenticate_request)):
    text = turn.text.strip()
    if not text or not session_manager.valid_id(turn.session_id):
        raise HTTPException(422, "Enter a message and a valid conversation ID.")
    session = session_manager.get_or_create_session(turn.session_id)
    async with session.turn_lock:
        history = [{"role": m["role"], "content": m["content"]} for m in session.messages
                   if m["role"] in ("user", "assistant") and m.get("content") and not m.get("tool_calls")]
        prompt = [{"role": "system", "content": "You are Jarvis, a thoughtful personal assistant. Answer directly. You are in conversation mode. For actions on a device, direct the owner to the agent workspace."},
                  *history[-40:], {"role": "user", "content": text}]
        try:
            client = agent.client.with_options(timeout=90, max_retries=0)
            result = await asyncio.wait_for(asyncio.to_thread(
                client.chat.completions.create, model=agent.model_name, messages=prompt
            ), timeout=95)
            answer = (result.choices[0].message.content or "").strip()
        except ModelConfigurationError:
            raise HTTPException(503, "The gateway needs a model API key. Configure OPENROUTER_API_KEY on the host and restart Jarvis.")
        except (asyncio.TimeoutError, APITimeoutError):
            raise HTTPException(504, "The model took too long. Please try again.")
        except APIStatusError as exc:
            hints = {401: "Check the model API key.", 403: "Check access to the configured model.",
                     404: "Check the configured model name.", 402: "Check the provider balance.",
                     429: "The model is busy. Try again shortly."}
            raise HTTPException(502, hints.get(exc.status_code, "The model provider rejected the request."))
        except Exception:
            raise HTTPException(502, "Could not get a reply from the configured model. Check the gateway's model connection.")
        if not answer:
            raise HTTPException(502, "The model returned an empty reply. Please try again.")
        user = session.add_message("user", text)
        reply = session.add_message("assistant", answer)
        return {"user": user, "reply": reply}


@app.post("/api/sessions/{session_id}/replies/{message_id}/speech")
async def speak_reply(session_id: str, message_id: str, auth: bool = Depends(authenticate_request)):
    session = session_manager.get_session(session_id)
    reply = next((m for m in session.messages if m["id"] == message_id and m["role"] == "assistant"), None) if session else None
    if not reply:
        raise HTTPException(404, "Reply not found.")
    path = speaker.get_audio_path(reply["audio_id"]) if reply.get("audio_id") else None
    if not path or not path.is_file():
        if not speaker.api_key:
            raise HTTPException(503, "ElevenLabs voice is not configured on this gateway.")
        meta = await asyncio.to_thread(speaker.generate_speech, reply["content"], session_id, message_id)
        if not meta:
            raise HTTPException(502, "ElevenLabs could not generate this reply.")
        reply["audio_id"] = meta["audio_id"]
        if session_manager.get_session(session_id) is session:
            session.save()
        path = speaker.get_audio_path(meta["audio_id"])
    if not path or not path.is_file():
        raise HTTPException(502, "The generated audio could not be loaded.")
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    if verify_token(req.token):
        return {"status": "authenticated", "token": req.token}
    raise HTTPException(status_code=401, detail="Invalid owner authentication token.")

@app.get("/api/system/telemetry")
async def get_telemetry(auth: bool = Depends(authenticate_request)):
    ips = get_lan_and_tailscale_ips()
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    # Use the host's system volume on Windows, macOS, Linux, or a future
    # container deployment instead of assuming the gateway always runs on C:.
    disk_root = Path.home().anchor or os.path.abspath(os.sep)
    disk = psutil.disk_usage(disk_root)

    return {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_mb": ram.used // (1024**2),
        "ram_total_mb": ram.total // (1024**2),
        "disk_percent": disk.percent,
        "disk_free_gb": disk.free // (1024**3),
        "disk_total_gb": disk.total // (1024**3),
        "uptime_seconds": int(time.time() - START_TIME),
        "hostname": socket.gethostname(),
        "network": ips,
        "active_model": agent.model_name,
        "voice_configured": bool(speaker.api_key)
    }

# Owner planner. Chat tools and the dashboard share one store.
class PlannerItem(BaseModel):
    title: str
    due: Optional[str] = None


@app.get("/api/planner")
def read_planner(auth: bool = Depends(authenticate_request)):
    return {"tasks": planner.open_tasks()}


@app.post("/api/planner")
def create_planner_item(item: PlannerItem, auth: bool = Depends(authenticate_request)):
    try:
        return {"message": planner.add_task(item.title, item.due)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/planner/{task_id}/complete")
def finish_planner_item(task_id: int, auth: bool = Depends(authenticate_request)):
    return {"message": planner.complete_task(task_id)}


# Sessions
@app.get("/api/sessions")
async def list_sessions(auth: bool = Depends(authenticate_request)):
    return {"sessions": session_manager.list_sessions()}

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Session"

@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest, auth: bool = Depends(authenticate_request)):
    sess = session_manager.get_or_create_session()
    if req.title:
        sess.title = req.title
        sess.save()
    return {"session": {"id": sess.id, "title": sess.title, "messages": sess.messages}}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, auth: bool = Depends(authenticate_request)):
    sess = session_manager.get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"id": sess.id, "title": sess.title, "messages": sess.messages}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, auth: bool = Depends(authenticate_request)):
    sess = session_manager.get_session(session_id)
    if sess and sess.turn_lock.locked():
        raise HTTPException(status_code=409, detail="Wait for the current reply before deleting this chat.")
    success = session_manager.delete_session(session_id)
    return {"deleted": success}

@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str, auth: bool = Depends(authenticate_request)):
    sess = session_manager.get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    sess.cancel()
    approval_manager.cancel_session_approvals(session_id)
    audit_logger.log_event("SESSION_CANCELLED", session_id=session_id, action="cancel")
    return {"status": "cancelled", "session_id": session_id}

@app.post("/api/emergency-stop")
async def emergency_stop(auth: bool = Depends(authenticate_request)):
    for sess in session_manager._active_sessions.values():
        sess.cancel()
        approval_manager.cancel_session_approvals(sess.id)
    audit_logger.log_event("GLOBAL_EMERGENCY_STOP", action="emergency_stop", policy="CRITICAL", status="STOPPED")
    return {"status": "emergency_stop_triggered"}

# Approvals
@app.get("/api/approvals")
async def get_approvals(session_id: Optional[str] = None, auth: bool = Depends(authenticate_request)):
    return {"pending_approvals": approval_manager.get_pending_requests(session_id)}

class DecisionRequest(BaseModel):
    decision: str  # "approve" or "reject"

@app.post("/api/approvals/{request_id}/decide")
async def decide_approval(request_id: str, req: DecisionRequest, auth: bool = Depends(authenticate_request)):
    success, msg = approval_manager.decide(request_id, req.decision)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "decided", "decision": req.decision, "message": msg}

# Team & Memory
@app.get("/api/team")
async def get_team(auth: bool = Depends(authenticate_request)):
    employees = []
    for file in sorted(EMPLOYEES_DIR.glob("*.md")):
        content = file.read_text(encoding="utf-8")
        first_line = content.splitlines()[0] if content else ""
        employees.append({"name": file.stem, "summary": first_line, "sop": content})
    return {"employees": employees}

class UpdateSOPRequest(BaseModel):
    rule: str

@app.post("/api/team/{name}")
async def update_team_member(name: str, req: UpdateSOPRequest, auth: bool = Depends(authenticate_request)):
    res = update_employee_sop(name, req.rule)
    return {"result": res}

@app.get("/api/memory")
async def get_memory(auth: bool = Depends(authenticate_request)):
    return {"memory": read_memory()}

class LogMemoryRequest(BaseModel):
    category: str
    rule: str

@app.post("/api/memory")
async def add_memory_rule(req: LogMemoryRequest, auth: bool = Depends(authenticate_request)):
    res = log_learned_rule(req.category, req.rule)
    return {"result": res}

# Activity / Audit
@app.get("/api/activity")
async def get_activity(limit: int = 40, auth: bool = Depends(authenticate_request)):
    return {"activity": audit_logger.get_recent_events(limit)}

# OpenJarvis Learning & Traces
@app.get("/api/traces")
async def get_traces(limit: int = 30, auth: bool = Depends(authenticate_request)):
    from learning.traces import trace_store
    return {"traces": trace_store.list_traces(limit=limit)}

class TraceFeedbackRequest(BaseModel):
    score: float  # 1.0 (positive), -1.0 (negative)
    notes: Optional[str] = None

@app.post("/api/traces/{trace_id}/feedback")
async def update_trace_feedback(trace_id: str, req: TraceFeedbackRequest, auth: bool = Depends(authenticate_request)):
    from learning.traces import trace_store
    success = trace_store.update_feedback(trace_id, req.score, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Trace not found.")
    return {"status": "feedback_recorded", "trace_id": trace_id, "score": req.score}

@app.post("/api/learning/evolve")
async def evolve_learning(auth: bool = Depends(authenticate_request)):
    from learning.evolver import AgentConfigEvolver
    evolver = AgentConfigEvolver()
    result = evolver.analyze_feedback_and_evolve()
    return result

# OpenJarvis Skills Catalog
@app.get("/api/skills")
async def get_skills(auth: bool = Depends(authenticate_request)):
    from skills.manager import skill_manager
    return {"skills": skill_manager.list_skills()}

# OpenJarvis Daily Morning Digest
@app.get("/api/digest")
async def get_daily_digest(location: str = "auto", auth: bool = Depends(authenticate_request)):
    from agents.morning_digest import generate_morning_digest
    digest = generate_morning_digest(location=location)
    return digest

# Audio & Voices
@app.get("/api/voices")
async def get_voices(auth: bool = Depends(authenticate_request)):
    return {"voices": speaker.get_voices(), "active_voice_id": speaker.voice_id}

class VoiceSelectRequest(BaseModel):
    voice_id: str

@app.post("/api/voices/select")
async def select_voice(req: VoiceSelectRequest, auth: bool = Depends(authenticate_request)):
    speaker.set_voice(req.voice_id)
    return {"status": "voice_updated", "voice_id": speaker.voice_id}

@app.get("/api/audio/{audio_id}")
async def get_audio(audio_id: str):
    path = speaker.get_audio_path(audio_id)
    if path and path.exists():
        return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})
    raise HTTPException(status_code=404, detail="Audio file not found")

@app.get("/jarvis-ca.crt")
@app.get("/ca.crt")
async def download_ca_certificate():
    ca_path = BASE_DIR / "certs" / "ca.crt"
    if ca_path.exists():
        return FileResponse(
            ca_path,
            media_type="application/x-x509-ca-cert",
            filename="jarvis-ca.crt",
            headers={"Content-Disposition": 'attachment; filename="jarvis-ca.crt"'}
        )
    raise HTTPException(status_code=404, detail="Root CA certificate not found on server.")

# ----------------- AUTHENTICATED WEBSOCKET -----------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Verify auth token before accepting the socket. A rejected handshake is
    # clearer to clients and avoids accidentally accepting the same socket twice.
    token = websocket.query_params.get("token")
    if is_auth_required() and (not token or not verify_token(token)):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "time": int(time.time())})

            elif msg_type == "get_telemetry":
                await websocket.send_json({
                    "type": "telemetry",
                    "cpu_percent": psutil.cpu_percent(),
                    "ram_percent": psutil.virtual_memory().percent
                })

            elif msg_type == "approval_decision":
                req_id = data.get("request_id")
                decision = data.get("decision", "reject")
                approval_manager.decide(req_id, decision)
                await websocket.send_json({"type": "approval_acknowledged", "request_id": req_id, "decision": decision})

            elif msg_type == "cancel":
                sess_id = data.get("session_id", "default")
                sess = session_manager.get_or_create_session(sess_id)
                sess.cancel()
                approval_manager.cancel_session_approvals(sess_id)
                await websocket.send_json({"type": "task_cancelled", "session_id": sess_id})

            elif msg_type == "chat":
                session_id = data.get("session_id", "default")
                text = data.get("text", "").strip()
                wants_voice = data.get("voice", True)
                text_first = data.get("text_first") is True

                if not text:
                    continue

                session = session_manager.get_or_create_session(session_id)

                async def process_chat(sess, user_text, voice, send_text_first):
                    # Callbacks for streaming events to the UI
                    def on_thought(thought_text):
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({
                                "type": "thought",
                                "session_id": sess.id,
                                "text": thought_text
                            }),
                            loop
                        )

                    def on_tool_start(fn_name, args):
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({
                                "type": "tool_start",
                                "session_id": sess.id,
                                "tool": fn_name,
                                "args": args
                            }),
                            loop
                        )

                    def on_tool_end(fn_name, result):
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({
                                "type": "tool_end",
                                "session_id": sess.id,
                                "tool": fn_name,
                                "result": result[:200]
                            }),
                            loop
                        )

                    def on_approval_needed(req_dict):
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({
                                "type": "approval_required",
                                "session_id": sess.id,
                                "request": req_dict
                            }),
                            loop
                        )

                    # Run ReAct in executor thread to prevent blocking
                    async with sess.turn_lock:
                        response_text = await agent.chat_async(
                            session=sess, user_input=user_text, on_thought=on_thought,
                            on_tool_start=on_tool_start, on_tool_end=on_tool_end,
                            on_approval_needed=on_approval_needed
                        )
                        reply = sess.messages[-1] if sess.messages else {}
                        if reply.get("role") != "assistant" or reply.get("tool_calls"):
                            reply = sess.add_message("assistant", response_text)
                    response = {"type": "response", "session_id": sess.id,
                                "message_id": reply["id"], "text": response_text}
                    if send_text_first:
                        await websocket.send_json(response)

                    audio_meta = None
                    if voice and speaker.api_key and not sess.is_cancelled:
                        await websocket.send_json({"type": "audio_state", "state": "generating"})
                        audio_meta = await loop.run_in_executor(
                            None,
                            lambda: speaker.generate_speech(response_text, session_id=sess.id, message_id=reply["id"])
                        )

                    audio_id = audio_meta["audio_id"] if audio_meta else None
                    audio_url = f"/api/audio/{audio_id}" if audio_id else None

                    if audio_id and session_manager.get_session(sess.id) is sess:
                        reply["audio_id"] = audio_id
                        sess.save()
                    audio_fields = {"audio_id": audio_id, "audio_url": audio_url}
                    if not send_text_first:
                        await websocket.send_json({**response, **audio_fields})
                    elif voice and not sess.is_cancelled:
                        await websocket.send_json({"type": "reply_audio", "session_id": sess.id,
                                                   "message_id": reply["id"], **audio_fields})

                # Spawn as a background task on the loop so the websocket receive loop stays unblocked
                # to process approval decisions, cancellations, and pings concurrently.
                asyncio.create_task(process_chat(session, text, wants_voice, text_first))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        safe_error = redact_secrets(str(e))
        print(f"[WebSocket Error]: {safe_error}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "JARVIS hit an internal error. Check the gateway console for details."
            })
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass

# ----------------- STATIC PWA SERVING -----------------

@app.get("/{full_path:path}")
async def serve_pwa(full_path: str):
    # Check if built React PWA exists in web_dist
    if WEB_DIST_DIR.exists():
        target_file = WEB_DIST_DIR / full_path
        if full_path and target_file.is_file():
            return FileResponse(target_file)
        index_file = WEB_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    # Fallback to legacy single-page index.html if web_dist is not built yet
    if LEGACY_HTML.exists():
        return FileResponse(LEGACY_HTML)

    return HTMLResponse("<h1>JARVIS Gateway Online</h1>", status_code=200)

if __name__ == "__main__":
    import sys
    import threading
    import uvicorn
    try:
        import websockets  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing WebSocket runtime. Run: python -m pip install -r requirements.txt"
        ) from exc

    # Keep laptop awake while JARVIS server runs
    if sys.platform == "win32":
        try:
            import ctypes
            # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001) | ES_DISPLAY_REQUIRED (0x00000002)
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            print("[Power] Windows execution state: Prevented sleep while server is online.")
        except Exception as e:
            print(f"[Power Warning] Could not set execution state: {e}")

    certs_dir = BASE_DIR / "certs"
    server_key = certs_dir / "server.key"
    fullchain_crt = certs_dir / "fullchain.crt"

    # Automatically generate certs if missing
    if not server_key.exists() or not fullchain_crt.exists():
        try:
            from scripts.generate_certs import generate_certificates
            generate_certificates()
        except Exception as e:
            print(f"[Warning] Failed to generate SSL certificates: {e}")

    ips = get_lan_and_tailscale_ips()
    primary_lan = ips["lan"][0] if ips["lan"] else "localhost"
    primary_ts = ips["tailscale"][0] if ips["tailscale"] else None

    has_ssl = server_key.exists() and fullchain_crt.exists()
    http_port = int(os.getenv("PORT", "8000"))
    https_port = int(os.getenv("SSL_PORT", "8443"))

    print("\n" + "="*68)
    print("🤖 JARVIS INTERFACE v3 - SECURE GATEWAY ONLINE")
    print("🔑 Owner Auth Token: [CONFIGURED IN .env - NEVER SHARED IN LOGS]")
    print(f"👉 Local Access (HTTP):   http://localhost:{http_port}")
    if has_ssl:
        print(f"🔒 Local Access (HTTPS):  https://localhost:{https_port}")
        print(f"📱 Phone Access (HTTPS):  https://{primary_lan}:{https_port}")
        print(f"📥 Phone CA Install:      http://{primary_lan}:{http_port}/jarvis-ca.crt")
    else:
        print(f"📱 Phone Access (HTTP):   http://{primary_lan}:{http_port}")
    if primary_ts:
        print(f"🔒 Tailscale Access:      http://{primary_ts}:{http_port}")
        if has_ssl:
            print(f"🔒 Tailscale HTTPS:       https://{primary_ts}:{https_port}")
    print("="*68 + "\n")

    if has_ssl:
        def run_http():
            uvicorn.run(app, host="0.0.0.0", port=http_port, ws="websockets", log_level="warning")

        http_thread = threading.Thread(target=run_http, daemon=True)
        http_thread.start()

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=https_port,
            ws="websockets",
            ssl_keyfile=str(server_key),
            ssl_certfile=str(fullchain_crt),
            log_level="info",
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=http_port, ws="websockets")
