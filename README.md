# 🤖 JARVIS Interface v3 (Secure Owner-Only Autonomous Operating System)

A secure, private, owner-only autonomous AI system designed for Windows OS control, specialized employee agent orchestration, real-time tool approval enforcement, low-latency ElevenLabs voice output, and an installable React/TypeScript PWA interface accessible from Windows, Mac, and Mobile.

---

## 🌟 What's New in Interface v3

1. **Production React + TypeScript + Vite PWA**:
   - Polished Iron Man/JARVIS HUD aesthetic (Obsidian surfaces, electric Cyan energy highlights, amber/red warning indicators).
   - Dynamic central **Animated JARVIS Orb** with 7 reactive states: `idle`, `listening`, `thinking`, `acting`, `speaking`, `disconnected`, and `error`.
   - Multi-device responsive design with desktop multi-panel workspace and bottom tab bar navigation for mobile devices.
   - PWA installable on iPhone (Safari), Android (Chrome), and Mac/Windows.

2. **Enterprise Security & Owner Authentication**:
   - **Bearer Token Auth**: Owner authentication enforced on all REST endpoints and WebSockets (`JARVIS_AUTH_TOKEN`).
   - **Rate Limiting & Request Limits**: Built-in sliding-window rate limiter and 10MB payload cap.
   - **Origin Allowlist**: Explicit CORS protection against unauthorized websites.
   - **Secret Redaction**: Automatic real-time redaction of API keys, tokens, and credentials in logs, events, and API payloads.
   - **Per-Conversation Sessions**: Complete session isolation with local persistent storage in `memory/sessions/`.

3. **Tool Policy & Approval System**:
   - **READ (Auto-Executed)**: Telemetry, directory listing, ordinary file reading.
   - **CONFIRM (Requires User Approval)**: PowerShell commands, file creation/modification, memory & SOP edits.
   - **CRITICAL (High-Impact Confirmation Card)**: File deletion, software installation (`winget`, `pip`, `npm`), registry edits, admin elevation.
   - **BLOCKED (Immediately Intercepted & Logged)**: Disk formatting (`diskpart`, `format`), broad recursive deletions on root, credential dumping, security tampering.
   - **Approval Cards**: Live approval cards on UI with TTL countdown, formatted diff/command previews, and single-use Approve/Reject decisions.
   - **Emergency Stop**: One-click instant cancellation halting all running tool loops, pending approvals, and audio streams.

4. **Enhanced ElevenLabs Voice**:
   - Unique audio output ID per task/message (`aud_...`).
   - Session & task association.
   - Automatic cache cleanup maintaining the latest 50 audio files.
   - Voice selection switcher (George, Adam, Rachel, Charlie, or custom) with replay controls.

---

## 🚀 Launching on Windows

### Option 1: Web Interface Server (Recommended)
Double-click [`run_web.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run_web.bat) or run:
```powershell
cd C:\Users\asha0\.gemini\antigravity\scratch\jarvis
.\run_web.bat
```
- Starts the FastAPI + Uvicorn server on `0.0.0.0:8000`.
- Automatically opens your default browser at `http://localhost:8000`.

### Option 2: Ambient Hands-Free Voice Mode
Double-click [`run_handsfree.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run_handsfree.bat) for continuous ambient voice listening on your laptop microphone.

### Option 3: Terminal CLI Mode
Double-click [`run.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run.bat) for hybrid text/voice interaction in PowerShell.

---

## 📱 Connecting From Mac, Phone, and Remote Devices

### 1. Over Private Local Wi-Fi (LAN)
1. Ensure your phone or Mac is connected to the same Wi-Fi network as the Windows laptop.
2. In your laptop terminal or Web UI **Settings**, find your local IP address (e.g. `192.168.0.140`).
3. Open Safari or Chrome on your phone or Mac and go to:
   ```
   http://192.168.0.140:8000
   ```
4. Enter your `JARVIS_AUTH_TOKEN` (found in `.env`) when prompted.
5. Tap **Add to Home Screen** in Safari / Chrome to install JARVIS as a native standalone PWA!

### 2. Over Private Tailscale Network (Secure Remote Access from Anywhere)
Tailscale enables end-to-end encrypted private networking without opening ports on your router:
1. Install Tailscale on the Windows laptop from [tailscale.com](https://tailscale.com) or via winget:
   ```powershell
   winget install Tailscale.Tailscale
   ```
2. Log in and note your laptop's Tailscale 100.x.x.x IP address.
3. Install Tailscale on your phone or Mac and sign into the same account.
4. From your phone or Mac anywhere in the world, access:
   ```
   http://100.x.x.x:8000
   ```

---

## 🧪 Automated Testing

### Backend Unit Tests:
```powershell
cd C:\Users\asha0\.gemini\antigravity\scratch\jarvis
.\.venv\Scripts\pytest.exe -v
```

### Live Server End-to-End Tests:
```powershell
cd C:\Users\asha0\.gemini\antigravity\scratch\jarvis
.\.venv\Scripts\python.exe tests/test_live_server.py
```

### Frontend TypeScript & Production Build Verification:
```powershell
cd C:\Users\asha0\.gemini\antigravity\scratch\jarvis\frontend
npm run lint
npm run build
```

---

## 📂 Architecture & Directory Structure

```
jarvis/
├── .env                       # Local secrets & API keys (Never committed)
├── .env.example               # Safe template with placeholder values
├── .gitignore                 # Excludes secrets, venv, cache, builds
├── README.md                  # Complete technical guide & documentation
├── SOUL.md                    # Core persona & executive directives
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python backend dependencies
├── run.bat                    # Hybrid CLI launcher
├── run_handsfree.bat          # Ambient voice loop launcher
├── run_web.bat                # Web HUD gateway launcher
├── server.py                  # Secure FastAPI + WebSocket gateway
├── agents/                    # Employee agent guidelines
│   ├── central_brain.md       # CEO Orchestrator persona
│   └── employees/             # Specialized employee SOPs
│       ├── coder.md
│       ├── os_operator.md
│       └── reviewer.md
├── core/                      # Engine core modules
│   ├── agent.py               # ReAct loop with policy enforcement
│   ├── approvals.py           # Tool policy classifier & approval lifecycle
│   ├── audit.py               # Audit logger with secret redaction
│   ├── auth.py                # Owner token auth & rate limiting
│   ├── client.py              # LLM client connector
│   ├── listener.py            # Local speech recognition & VAD
│   ├── session.py             # Per-conversation session isolation
│   └── speaker.py             # ElevenLabs TTS & cache manager
├── frontend/                  # React + TypeScript + Vite PWA source
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx            # Main layout & auth gate
│       ├── components/        # JarvisOrb, TelemetryBar, LeftSidebar, ChatArea, Composer, etc.
│       ├── stores/            # Zustand stores (Auth, Jarvis, Audio, Telemetry, Activity)
│       └── types/             # TypeScript definitions
├── memory/                    # Persistent learned rules & session history
│   ├── learned_rules.md       # Host facts & user preferences
│   └── sessions/              # Isolated session JSON records
├── tests/                     # Test suites
│   ├── test_backend.py        # Unit test suite
│   └── test_live_server.py    # End-to-end live gateway tests
└── web_dist/                  # Compiled production PWA bundle
```
