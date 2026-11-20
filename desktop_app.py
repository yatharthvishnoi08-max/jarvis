"""
J.A.R.V.I.S. Standalone Windows Desktop Application.
Embeds the React HUD / Mission Control Dashboard in a native Windows WebView2 container
with persistent profile storage, native microphone auto-permissions, and host sleep prevention.
"""

import os
import sys
import time
import ctypes
import socket
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Windows Sleep Prevention Flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

def set_sleep_prevention(enable: bool = True):
    """Prevents Windows from entering sleep mode while JARVIS is active."""
    try:
        if sys.platform == "win32":
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception as e:
        print(f"[Power Manager Warning]: {e}")

def is_server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Checks if the JARVIS gateway port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def ensure_server():
    """Spawns server.py in the background if not already active."""
    if is_server_running():
        print("[JARVIS App]: Gateway server already running on port 8000.")
        return None

    print("[JARVIS App]: Spawning gateway server daemon...")
    python_exe = sys.executable
    # If running with pythonw.exe, locate python.exe or run with current executable
    server_script = BASE_DIR / "server.py"

    proc = subprocess.Popen(
        [python_exe, str(server_script)],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )

    # Wait for server to become responsive
    start = time.time()
    while time.time() - start < 15.0:
        if is_server_running():
            print("[JARVIS App]: Gateway server initialized successfully.")
            return proc
        time.sleep(0.4)

    print("[JARVIS App Warning]: Server startup wait timed out; attempting connection anyway.")
    return proc

def hook_webview_permissions():
    """Hooks WebView2 to automatically grant microphone and device permissions."""
    try:
        import webview.platforms.edgechromium as edge
        from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState

        orig_on_webview_ready = edge.EdgeChrome.on_webview_ready

        def hooked_on_webview_ready(self, sender, args):
            orig_on_webview_ready(self, sender, args)
            if args.IsSuccess:
                def on_permission_requested(s, e):
                    try:
                        # Automatically grant media, microphone, and notifications
                        e.State = CoreWebView2PermissionState.Allow
                    except Exception as ex:
                        print(f"[JARVIS Permission Handler Warning]: {ex}")

                sender.CoreWebView2.PermissionRequested += on_permission_requested

        edge.EdgeChrome.on_webview_ready = hooked_on_webview_ready
        print("[JARVIS App]: WebView2 automatic microphone permission handler registered.")
    except Exception as e:
        print(f"[JARVIS App Info]: WebView2 permission hook notice: {e}")

def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Desktop Operating System")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--debug", action="store_true", help="Enable WebView2 developer tools")
    args = parser.parse_args()

    hook_webview_permissions()

    import webview

    token = os.getenv("JARVIS_AUTH_TOKEN", "").strip()
    profile_dir = BASE_DIR / "memory" / "webview_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    icon_path = BASE_DIR / "assets" / "jarvis.ico"

    server_proc = ensure_server()
    set_sleep_prevention(True)

    url = f"http://127.0.0.1:8000/?token={token}"

    window = webview.create_window(
        title="J.A.R.V.I.S. Autonomous Operating System",
        url=url,
        width=1340,
        height=880,
        min_size=(960, 640),
        fullscreen=args.fullscreen,
        background_color="#050811",
        text_select=True
    )

    try:
        # Start WebView2 with persistent storage path so permissions & localStorage are saved
        webview.start(
            debug=args.debug,
            private_mode=False,
            storage_path=str(profile_dir),
            icon=str(icon_path) if icon_path.exists() else None
        )
    finally:
        set_sleep_prevention(False)
        if server_proc and server_proc.poll() is None:
            print("[JARVIS App]: Terminating background server process...")
            server_proc.terminate()

if __name__ == "__main__":
    main()
