<#
.SYNOPSIS
    J.A.R.V.I.S. Windows System Permissions & Security Configuration Script.
.DESCRIPTION
    Configures native Windows permissions for J.A.R.V.I.S.:
    - Windows Firewall rules for HTTP (8000) and HTTPS (8443)
    - Windows Microphone consent for desktop applications
    - PowerShell execution policy (RemoteSigned)
    - Long path support in Windows registry
    - Optional automatic Windows Startup registration
#>

[CmdletBinding()]
param(
    [switch]$EnableStartup,
    [switch]$DisableStartup
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Get-Item $PSScriptRoot).Parent.FullName
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$BatchLauncher = Join-Path $ProjectDir "run_app.bat"
$SilentLauncher = Join-Path $ProjectDir "run_app_silent.vbs"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       J.A.R.V.I.S. Windows Native Permissions Setup     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project Directory: $ProjectDir" -ForegroundColor Gray

# 1. Check Administrator Privileges
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Host "[NOTICE] Running without elevation. Elevating to Administrator..." -ForegroundColor Yellow
    try {
        $ArgList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        if ($EnableStartup) { $ArgList += " -EnableStartup" }
        if ($DisableStartup) { $ArgList += " -DisableStartup" }
        Start-Process powershell.exe -Verb RunAs -ArgumentList $ArgList
        exit 0
    } catch {
        Write-Host "[ERROR] Administrator access was denied. Some firewall rules cannot be applied." -ForegroundColor Red
    }
}

# 2. PowerShell Execution Policy
Write-Host "`n[1/5] Configuring PowerShell Execution Policy..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
    Write-Host "  -> CurrentUser execution policy set to RemoteSigned." -ForegroundColor Green
} catch {
    Write-Host "  -> Warning setting execution policy: $_" -ForegroundColor DarkYellow
}

# 3. Windows Microphone Privacy Permissions
Write-Host "`n[2/5] Configuring Windows Microphone Privacy Permissions..." -ForegroundColor Yellow
try {
    $ConsentStore = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    if (-not (Test-Path $ConsentStore)) {
        New-Item -Path $ConsentStore -Force | Out-Null
    }
    Set-ItemProperty -Path $ConsentStore -Name "Value" -Value "Allow" -Force

    $NonPackaged = "$ConsentStore\NonPackaged"
    if (-not (Test-Path $NonPackaged)) {
        New-Item -Path $NonPackaged -Force | Out-Null
    }
    Set-ItemProperty -Path $NonPackaged -Name "Value" -Value "Allow" -Force
    Write-Host "  -> Microphone access granted for packaged and desktop apps." -ForegroundColor Green
} catch {
    Write-Host "  -> Warning setting microphone registry keys: $_" -ForegroundColor DarkYellow
}

# 4. Windows Defender Firewall Inbound Rules
Write-Host "`n[3/5] Configuring Windows Defender Firewall Rules..." -ForegroundColor Yellow
if ($IsAdmin) {
    try {
        # Port 8000 (HTTP API & Web HUD)
        $Rule8000 = Get-NetFirewallRule -DisplayName "JARVIS Gateway HTTP (Port 8000)" -ErrorAction SilentlyContinue
        if ($Rule8000) {
            Remove-NetFirewallRule -DisplayName "JARVIS Gateway HTTP (Port 8000)" | Out-Null
        }
        New-NetFirewallRule -DisplayName "JARVIS Gateway HTTP (Port 8000)" `
            -Direction Inbound `
            -LocalPort 8000 `
            -Protocol TCP `
            -Action Allow `
            -Profile Domain,Private `
            -Description "Allows local network access to the J.A.R.V.I.S. Mission Control API and HUD." | Out-Null
        Write-Host "  -> Allowed TCP Inbound on Port 8000 (HTTP)." -ForegroundColor Green

        # Port 8443 (HTTPS Gateway)
        $Rule8443 = Get-NetFirewallRule -DisplayName "JARVIS Gateway HTTPS (Port 8443)" -ErrorAction SilentlyContinue
        if ($Rule8443) {
            Remove-NetFirewallRule -DisplayName "JARVIS Gateway HTTPS (Port 8443)" | Out-Null
        }
        New-NetFirewallRule -DisplayName "JARVIS Gateway HTTPS (Port 8443)" `
            -Direction Inbound `
            -LocalPort 8443 `
            -Protocol TCP `
            -Action Allow `
            -Profile Domain,Private `
            -Description "Allows secure local network access to J.A.R.V.I.S. HTTPS Gateway." | Out-Null
        Write-Host "  -> Allowed TCP Inbound on Port 8443 (HTTPS)." -ForegroundColor Green

        # Python Outbound Rule
        if (Test-Path $VenvPython) {
            $RulePy = Get-NetFirewallRule -DisplayName "JARVIS Python Outbound" -ErrorAction SilentlyContinue
            if ($RulePy) {
                Remove-NetFirewallRule -DisplayName "JARVIS Python Outbound" | Out-Null
            }
            New-NetFirewallRule -DisplayName "JARVIS Python Outbound" `
                -Direction Outbound `
                -Program $VenvPython `
                -Action Allow `
                -Profile Any `
                -Description "Allows J.A.R.V.I.S. Python runtime to query LLM APIs." | Out-Null
            Write-Host "  -> Allowed Outbound network communication for JARVIS Python runtime." -ForegroundColor Green
        }
    } catch {
        Write-Host "  -> Warning configuring firewall: $_" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  -> [SKIPPED] Administrator elevation required to modify Windows Firewall." -ForegroundColor DarkYellow
}

# 5. Enable Long Path Support in Windows Registry
Write-Host "`n[4/5] Configuring Windows Long Path Support..." -ForegroundColor Yellow
if ($IsAdmin) {
    try {
        Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -Force
        Write-Host "  -> Enabled Win32 Long Paths (removes 260 character limit)." -ForegroundColor Green
    } catch {
        Write-Host "  -> Warning setting LongPathsEnabled: $_" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  -> [SKIPPED] Requires Administrator elevation." -ForegroundColor DarkYellow
}

# 6. Automatic Startup Configuration (Optional)
Write-Host "`n[5/5] Startup Configuration..." -ForegroundColor Yellow
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$WscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"
$StartupCmd = "`"$WscriptExe`" `"$SilentLauncher`""

if ($EnableStartup) {
    try {
        Set-ItemProperty -Path $RunKey -Name "JARVIS_OS" -Value $StartupCmd -Force
        Write-Host "  -> J.A.R.V.I.S. configured to start automatically on Windows login." -ForegroundColor Green
    } catch {
        Write-Host "  -> Warning enabling startup: $_" -ForegroundColor DarkYellow
    }
} elseif ($DisableStartup) {
    try {
        Remove-ItemProperty -Path $RunKey -Name "JARVIS_OS" -ErrorAction SilentlyContinue
        Write-Host "  -> J.A.R.V.I.S. automatic startup disabled." -ForegroundColor Green
    } catch {
        Write-Host "  -> Warning disabling startup: $_" -ForegroundColor DarkYellow
    }
} else {
    $CurrentStartup = Get-ItemProperty -Path $RunKey -Name "JARVIS_OS" -ErrorAction SilentlyContinue
    if ($CurrentStartup) {
        Write-Host "  -> Automatic startup is currently: ENABLED" -ForegroundColor Green
    } else {
        Write-Host "  -> Automatic startup is currently: DISABLED (use -EnableStartup to turn on)" -ForegroundColor Gray
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "       J.A.R.V.I.S. Permissions Configured Successfully!  " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
