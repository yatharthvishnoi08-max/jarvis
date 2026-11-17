# 🤖 JARVIS Agent System

Autonomous, multi-agent AI assistant for Windows OS control, self-improving workflows, two-way hands-free voice, and **Remote Web Interface for Phone, Tablet & Other Devices**.

---

## 🌐 Remote Web Interface (Access from Phone / Tablet)
No terminal needed. You can control your laptop from your phone, tablet, or another computer on the same Wi-Fi.

### How to Start the Web Server:
Double-click [`run_web.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run_web.bat) or run:
```powershell
cd C:\Users\asha0\.gemini\antigravity\scratch\jarvis
.\.venv\Scripts\python.exe server.py
```

### URLs to Open:
- **On this laptop**: Open [`http://localhost:8000`](http://localhost:8000)
- **From your Phone / Tablet / Another Device**: Open `http://<YOUR_LAPTOP_IP>:8000`  
  *(For example: `http://192.168.0.140:8000`)*

---

## 📱 Features of the Web Interface
1. **Iron Man HUD Aesthetic**: Sleek Obsidian & glowing Cyan theme with an animated Arc-Reactor status indicator.
2. **Mobile Microphone Support**: Tap the microphone icon on your phone to speak. Your phone transcribes your speech and sends it directly to your laptop's JARVIS.
3. **Voice Audio Playback**: Plays ElevenLabs speech directly through your phone or computer speakers.
4. **Live System Telemetry**: Real-time CPU, RAM, and Disk utilization gauges.
5. **Real-Time Tool Execution Feed**: Watch JARVIS run PowerShell commands, open files, and tune employee SOPs in real time.
6. **Employees & Memory Drawer**: Inspect active agents (`os_operator`, `coder`, `reviewer`) and read/edit persistent learned rules.

---

## 💻 Alternative Terminal Launchers
- [`run.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run.bat): Interactive hybrid terminal mode (type or speak).
- [`run_handsfree.bat`](file:///C:/Users/asha0/.gemini/antigravity/scratch/jarvis/run_handsfree.bat): Continuous hands-free audio loop on laptop.
