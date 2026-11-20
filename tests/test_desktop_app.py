"""
Tests for J.A.R.V.I.S. Standalone Windows Desktop Application and Shortcuts.
"""

import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent

def test_desktop_assets_exist():
    ico_path = BASE_DIR / "assets" / "jarvis.ico"
    png_path = BASE_DIR / "assets" / "jarvis.png"
    assert ico_path.exists(), "assets/jarvis.ico must exist"
    assert png_path.exists(), "assets/jarvis.png must exist"
    assert ico_path.stat().st_size > 1000, "jarvis.ico should be non-trivial"
    assert png_path.stat().st_size > 1000, "jarvis.png should be non-trivial"

def test_launchers_exist():
    bat_path = BASE_DIR / "run_app.bat"
    vbs_path = BASE_DIR / "run_app_silent.vbs"
    perm_ps1 = BASE_DIR / "scripts" / "configure_permissions.ps1"
    perm_bat = BASE_DIR / "scripts" / "grant_permissions.bat"

    assert bat_path.exists(), "run_app.bat must exist"
    assert vbs_path.exists(), "run_app_silent.vbs must exist"
    assert perm_ps1.exists(), "scripts/configure_permissions.ps1 must exist"
    assert perm_bat.exists(), "scripts/grant_permissions.bat must exist"

def test_desktop_app_module_functions():
    import desktop_app

    # Test server check function
    # Port 8000 is running our active daemon
    running = desktop_app.is_server_running("127.0.0.1", 8000)
    assert running is True

    # Test non-existent port returns False
    closed = desktop_app.is_server_running("127.0.0.1", 59999)
    assert closed is False

    # Check power management flags
    assert desktop_app.ES_CONTINUOUS == 0x80000000
    assert desktop_app.ES_SYSTEM_REQUIRED == 0x00000001
    assert desktop_app.ES_AWAYMODE_REQUIRED == 0x00000040

def test_shortcuts_creation():
    from scripts import create_shortcuts
    desktop = create_shortcuts.get_special_folder("Desktop")
    programs = create_shortcuts.get_special_folder("Programs")
    assert desktop.exists()
    assert programs.exists()
