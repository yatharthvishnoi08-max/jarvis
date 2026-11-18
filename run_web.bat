@echo off
title JARVIS Interface v3 - Gateway Server
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
  echo Repairing missing WebSocket runtime...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo JARVIS could not install the required WebSocket runtime.
    echo Run: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
  )
)

where npm >nul 2>&1
if errorlevel 1 (
  echo Node.js is required to build the JARVIS interface.
  echo Install Node.js LTS, then run this launcher again.
  pause
  exit /b 1
)

pushd frontend
if not exist node_modules\dompurify\package.json (
  echo Installing interface dependencies...
  call npm ci
  if errorlevel 1 (
    popd
    echo Interface dependency installation failed.
    pause
    exit /b 1
  )
)
echo Building the latest JARVIS interface...
call npm run build
if errorlevel 1 (
  popd
  echo Interface build failed.
  pause
  exit /b 1
)
popd

echo Starting JARVIS Interface v3 Core Gateway...
start "" "http://localhost:8000"
python server.py
pause
