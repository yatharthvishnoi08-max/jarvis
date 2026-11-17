@echo off
title JARVIS - Web Interface Server
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python server.py
pause
