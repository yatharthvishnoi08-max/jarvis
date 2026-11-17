import os
import json
import asyncio
import socket
import psutil
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from core.agent import JarvisAgent
from core.speaker import ElevenLabsSpeaker
from tools.meta_tools import list_employees, read_memory, EMPLOYEES_DIR

BASE_DIR = Path(__file__).resolve().parent
AUDIO_FILE = BASE_DIR / "audio_cache" / "latest_speech.mp3"
HTML_FILE = BASE_DIR / "web" / "index.html"

app = FastAPI(title="JARVIS Remote Interface")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core agent and speaker
agent = JarvisAgent()
speaker = ElevenLabsSpeaker()

def get_lan_ips():
    """Returns local network IPs of the laptop."""
    try:
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
    except Exception:
        return ["localhost"]

@app.get("/", response_class=HTMLResponse)
async def get_index():
    if not HTML_FILE.exists():
        return HTMLResponse("<h1>Error: web/index.html not found</h1>", status_code=404)
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))

@app.get("/api/audio/latest")
async def get_latest_audio():
    if AUDIO_FILE.exists():
        return FileResponse(AUDIO_FILE, media_type="audio/mpeg")
    return {"error": "No audio generated yet"}

@app.get("/api/system/stats")
async def get_stats():
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("C:\\").percent
    }

@app.get("/api/team")
async def get_team():
    employees = []
    for file in sorted(EMPLOYEES_DIR.glob("*.md")):
        first_line = file.read_text(encoding="utf-8").splitlines()[0] if file.stat().st_size > 0 else ""
        employees.append({"name": file.stem, "description": first_line})
    return {"employees": employees}

@app.get("/api/memory")
async def get_memory_content():
    return {"memory": read_memory()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            if msg_type == "get_stats":
                await websocket.send_json({
                    "type": "stats",
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent
                })

            elif msg_type == "chat":
                user_text = data.get("text", "")
                wants_voice = data.get("voice", True)

                # Callbacks for tool execution updates
                def on_tool_start(fn_name, args):
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "tool_start",
                            "tool": fn_name,
                            "args": args
                        }),
                        loop
                    )

                def on_tool_end(fn_name, result):
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "tool_end",
                            "tool": fn_name
                        }),
                        loop
                    )

                # Run ReAct in executor thread to keep WebSocket responsive
                response = await loop.run_in_executor(
                    None,
                    agent.chat,
                    user_text,
                    on_tool_start,
                    on_tool_end
                )

                audio_url = None
                if wants_voice and speaker.api_key:
                    # Synthesize audio
                    await loop.run_in_executor(None, speaker.speak, response)
                    if AUDIO_FILE.exists():
                        audio_url = "/api/audio/latest"

                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "audio_url": audio_url
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket Error]: {e}")

if __name__ == "__main__":
    import uvicorn
    ips = get_lan_ips()
    primary_ip = ips[0] if ips else "localhost"
    print("\n" + "="*60)
    print("🚀 JARVIS WEB SERVER ONLINE")
    print(f"👉 Local Access:   http://localhost:8000")
    print(f"📱 Phone/Tablet:   http://{primary_ip}:8000")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
