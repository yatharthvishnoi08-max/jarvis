@echo off
title JARVIS Interface v3 - Gateway Server
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Starting JARVIS Interface v3 Core Gateway...
start "" "http://localhost:8000"
python server.py
pause
