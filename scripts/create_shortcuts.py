"""
Creates Windows Desktop and Start Menu shortcuts for J.A.R.V.I.S.
with custom Arc Reactor icon and silent launcher.
"""

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = BASE_DIR / "assets" / "jarvis.ico"
SILENT_LAUNCHER = BASE_DIR / "run_app_silent.vbs"
BAT_LAUNCHER = BASE_DIR / "run_app.bat"

def get_special_folder(folder_name: str) -> Path:
    """Retrieves standard Windows shell special folders using PowerShell."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"[Environment]::GetFolderPath('{folder_name}')"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    folder = res.stdout.strip()
    return Path(folder)

def create_shortcut(lnk_path: Path, target: str, args: str, work_dir: str, icon: str, description: str):
    """Creates a Windows .lnk shortcut using PowerShell COM object."""
    lnk_path.parent.mkdir(parents=True, exist_ok=True)
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{lnk_path}')
$Shortcut.TargetPath = '{target}'
$Shortcut.Arguments = '{args}'
$Shortcut.WorkingDirectory = '{work_dir}'
$Shortcut.IconLocation = '{icon},0'
$Shortcut.Description = '{description}'
$Shortcut.Save()
"""
    cmd = ["powershell", "-NoProfile", "-Command", ps_script]
    subprocess.run(cmd, check=True)
    print(f"[JARVIS Shortcut]: Successfully created -> {lnk_path}")

def main():
    if not ICON_PATH.exists():
        print(f"[Error]: Icon file not found at {ICON_PATH}")
        sys.exit(1)

    wscript_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"

    # 1. Desktop Shortcut
    try:
        desktop_dir = get_special_folder("Desktop")
        desktop_lnk = desktop_dir / "JARVIS.lnk"
        create_shortcut(
            lnk_path=desktop_lnk,
            target=str(wscript_path),
            args=f'"{SILENT_LAUNCHER}"',
            work_dir=str(BASE_DIR),
            icon=str(ICON_PATH),
            description="J.A.R.V.I.S. Autonomous AI Operating System"
        )
    except Exception as e:
        print(f"[Warning]: Failed creating Desktop shortcut: {e}")

    # 2. Start Menu Shortcut
    try:
        programs_dir = get_special_folder("Programs")
        start_menu_lnk = programs_dir / "JARVIS.lnk"
        create_shortcut(
            lnk_path=start_menu_lnk,
            target=str(wscript_path),
            args=f'"{SILENT_LAUNCHER}"',
            work_dir=str(BASE_DIR),
            icon=str(ICON_PATH),
            description="J.A.R.V.I.S. Autonomous AI Operating System"
        )
    except Exception as e:
        print(f"[Warning]: Failed creating Start Menu shortcut: {e}")

if __name__ == "__main__":
    main()
