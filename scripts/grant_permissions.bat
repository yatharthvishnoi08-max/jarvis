@echo off
setlocal
title J.A.R.V.I.S. Permissions Setup
cd /d "%~dp0"

echo Requesting Administrator privileges to configure Windows Firewall and Permissions...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"\"%~dp0configure_permissions.ps1\"\" %*'"

pause
