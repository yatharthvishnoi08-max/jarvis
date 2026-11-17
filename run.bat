@echo off
title JARVIS - Nous Hermes 3
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
