@echo off
title JARVIS - Hands-Free Voice Mode
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py --hands-free
pause
