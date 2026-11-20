@echo off
setlocal enabledelayedexpansion
title J.A.R.V.I.S. Desktop
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe!
    echo Please install dependencies first.
    pause
    exit /b 1
)

:: Check if launched with --console or --debug
set "USE_CONSOLE=0"
for %%a in (%*) do (
    if "%%a"=="--console" set "USE_CONSOLE=1"
    if "%%a"=="--debug" set "USE_CONSOLE=1"
)

if "!USE_CONSOLE!"=="1" (
    echo [JARVIS App]: Launching in interactive console mode...
    .venv\Scripts\python.exe desktop_app.py %*
) else (
    start "" .venv\Scripts\pythonw.exe desktop_app.py %*
)
