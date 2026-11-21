"""
J.A.R.V.I.S. Computer Use & Windows OS Automation Tools.
Empowers JARVIS with mouse, keyboard, window control, Windows Settings automation,
visual element localization via Gemini Vision, and system-level permissions configuration.
"""

import os
import re
import time
import json
import base64
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import psutil
from core.execution_control import cancellation_requested

# Safe import of PyAutoGUI with fail-safe enabled
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Moving mouse to screen corner aborts automation
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "memory" / "screenshots"

# Windows Settings URI schemes map
WINDOWS_SETTINGS_MAP = {
    "home": "ms-settings:",
    "settings": "ms-settings:",
    "microphone": "ms-settings:privacy-microphone",
    "mic": "ms-settings:privacy-microphone",
    "camera": "ms-settings:privacy-webcam",
    "webcam": "ms-settings:privacy-webcam",
    "location": "ms-settings:privacy-location",
    "privacy": "ms-settings:privacy",
    "apps": "ms-settings:appsfeatures",
    "installed_apps": "ms-settings:appsfeatures",
    "startup": "ms-settings:startupapps",
    "startup_apps": "ms-settings:startupapps",
    "security": "ms-settings:windowsdefender",
    "defender": "ms-settings:windowsdefender",
    "sound": "ms-settings:sound",
    "audio": "ms-settings:sound",
    "volume": "ms-settings:sound",
    "display": "ms-settings:display",
    "screen": "ms-settings:display",
    "network": "ms-settings:network",
    "wifi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth",
    "power": "ms-settings:powersleep",
    "battery": "ms-settings:powersleep",
    "sleep": "ms-settings:powersleep",
    "updates": "ms-settings:windowsupdate",
    "notifications": "ms-settings:notifications",
    "taskbar": "ms-settings:taskbar"
}

# Common Windows application paths and aliases for instant launch
COMMON_APP_MAP = {
    "telegram": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe"),
        r"C:\Program Files\Telegram Desktop\Telegram.exe",
    ],
    "tg": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe"),
    ],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "chrome",
    ],
    "code": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        "code",
    ],
    "vscode": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        "code",
    ],
    "edge": ["msedge"],
    "msedge": ["msedge"],
    "notepad": [
        os.path.expandvars(r"%SystemRoot%\System32\notepad.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\notepad.exe"),
        "notepad",
    ],
    "calc": ["calc"],
    "calculator": ["calc"],
    "explorer": ["explorer"],
    "cmd": ["cmd"],
    "powershell": ["powershell"],
    "taskmgr": ["taskmgr"],
    "task_manager": ["taskmgr"],
    "spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "spotify",
    ],
    "discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
    ],
    "whatsapp": [
        os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
    ]
}

def is_desktop_available() -> tuple[bool, str]:
    """
    Checks whether the interactive desktop station is active and accessible.
    Returns (True, "DESKTOP_AVAILABLE") or (False, "DESKTOP_UNAVAILABLE: Desktop is locked or inaccessible.")
    """
    if os.name != "nt":
        return True, "DESKTOP_AVAILABLE"
    try:
        import ctypes
        u = ctypes.windll.user32
        hDesk = u.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_READOBJECTS
        if not hDesk or hDesk == 0:
            return False, "DESKTOP_UNAVAILABLE: Windows desktop is locked, disconnected, or station is inaccessible."
        u.CloseDesktop(hDesk)
        return True, "DESKTOP_AVAILABLE"
    except Exception as e:
        return False, f"DESKTOP_UNAVAILABLE: Error checking desktop accessibility: {str(e)}"

def verify_foreground_window(expected_keyword: str) -> tuple[bool, str]:
    """
    Verifies that the currently visible foreground window matches the expected application or keyword.
    Prevents sending keyboard/mouse input into an unintended foreground window.
    """
    if os.name != "nt":
        return True, "VERIFIED"

    try:
        import ctypes
        from tools.multimodal_tools import _ensure_input_desktop
        _ensure_input_desktop()

        u = ctypes.windll.user32
        fg = u.GetForegroundWindow()
        if not fg:
            return False, "WINDOW_MISMATCH: No foreground window is currently active."

        length = u.GetWindowTextLengthW(fg)
        buff = ctypes.create_unicode_buffer(length + 1)
        u.GetWindowTextW(fg, buff, length + 1)
        title = buff.value

        cls_buff = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(fg, cls_buff, 256)
        cls_name = cls_buff.value

        cls_low = cls_name.lower()
        title_low = title.lower()
        if cls_low in ("ime", "msctfime ui") or title_low in ("default ime", "msctfime ui"):
            return False, f"WINDOW_MISMATCH: Foreground window is an IME helper window '{title}'."

        w_pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(fg, ctypes.byref(w_pid))

        proc_name = ""
        try:
            proc_name = psutil.Process(w_pid.value).name().lower()
        except Exception:
            pass

        kw = expected_keyword.lower().strip()
        if kw in title.lower() or kw in cls_name.lower() or kw in proc_name:
            return True, f"VERIFIED: Foreground window is '{title}' (Class: '{cls_name}', PID: {w_pid.value})"

        return False, f"WINDOW_MISMATCH: Foreground window is '{title}' (Class: '{cls_name}', Process: '{proc_name}'), expected '{expected_keyword}'."
    except Exception as e:
        return False, f"ERROR checking foreground window: {str(e)}"

def _enforce_desktop_and_target(target_window: str) -> tuple[bool, str]:
    """
    Strict guard that validates:
    1. An explicit target window is provided (rejects empty / whitespace string).
    2. Interactive desktop is accessible (is_desktop_available).
    3. The active visible foreground window matches the expected target (verify_foreground_window).
    Returns (True, "OK") if verified, or (False, error_message).
    """
    if cancellation_requested():
        return False, "ERROR: Operation cancelled by user."
    if not target_window or not str(target_window).strip():
        return False, "ERROR: An explicit target_window is required to prevent unintended input."

    avail, desk_msg = is_desktop_available()
    if not avail:
        return False, f"ERROR: Desktop unavailable ({desk_msg})"

    verified, win_msg = verify_foreground_window(target_window)
    if not verified:
        return False, f"ERROR: Foreground window verification failed: {win_msg}"

    return True, "OK"

def get_mouse_position() -> str:
    """Returns the current mouse cursor (x, y) coordinates and screen dimensions."""
    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available on this host."
    try:
        x, y = pyautogui.position()
        w, h = pyautogui.size()
        return f"Mouse Position: ({x}, {y}) | Screen Resolution: {w}x{h}"
    except Exception as e:
        return f"ERROR reading mouse position: {str(e)}"

def mouse_move(target_window: str, x: int, y: int, duration: float = 0.2) -> str:
    """Moves the mouse cursor smoothly to the specified (x, y) screen coordinates within verified target window."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        pyautogui.FAILSAFE = True
        w, h = pyautogui.size()
        target_x = max(0, min(x, w - 1))
        target_y = max(0, min(y, h - 1))
        pyautogui.moveTo(target_x, target_y, duration=max(0.05, duration))
        return f"SUCCESS: Moved mouse to ({target_x}, {target_y})."
    except Exception as e:
        return f"ERROR moving mouse: {str(e)}"

def mouse_click(
    target_window: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1
) -> str:
    """
    Clicks the mouse at the given (x, y) screen coordinates, or at current cursor location within verified target window.
    Supported buttons: 'left', 'right', 'middle'.
    Supported clicks: 1 (single click), 2 (double click).
    """
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        pyautogui.FAILSAFE = True
        btn = button.lower().strip()
        if btn not in ["left", "right", "middle"]:
            btn = "left"

        if x is not None and y is not None:
            w, h = pyautogui.size()
            target_x = max(0, min(x, w - 1))
            target_y = max(0, min(y, h - 1))
            if clicks >= 2:
                pyautogui.doubleClick(target_x, target_y, button=btn)
                return f"SUCCESS: Double-clicked ({btn} button) at ({target_x}, {target_y})."
            else:
                pyautogui.click(target_x, target_y, button=btn)
                return f"SUCCESS: Clicked ({btn} button) at ({target_x}, {target_y})."
        else:
            cur_x, cur_y = pyautogui.position()
            if clicks >= 2:
                pyautogui.doubleClick(button=btn)
                return f"SUCCESS: Double-clicked ({btn} button) at current cursor ({cur_x}, {cur_y})."
            else:
                pyautogui.click(button=btn)
                return f"SUCCESS: Clicked ({btn} button) at current cursor ({cur_x}, {cur_y})."
    except Exception as e:
        return f"ERROR executing mouse click: {str(e)}"

def mouse_scroll(target_window: str, clicks: int) -> str:
    """Scrolls the active window wheel up (positive integer) or down (negative integer) within verified target window."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return f"SUCCESS: Scrolled {direction} ({abs(clicks)} units)."
    except Exception as e:
        return f"ERROR scrolling mouse: {str(e)}"

def mouse_drag(target_window: str, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> str:
    """Drags the mouse with the left button pressed from (start_x, start_y) to (end_x, end_y) within verified target window."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        w, h = pyautogui.size()
        sx = max(0, min(start_x, w - 1))
        sy = max(0, min(start_y, h - 1))
        ex = max(0, min(end_x, w - 1))
        ey = max(0, min(end_y, h - 1))

        pyautogui.moveTo(sx, sy)
        pyautogui.dragTo(ex, ey, duration=max(0.1, duration), button="left")
        return f"SUCCESS: Dragged from ({sx}, {sy}) to ({ex}, {ey})."
    except Exception as e:
        return f"ERROR dragging mouse: {str(e)}"

def _prevent_corner_failsafe():
    """Moves cursor safely away from (0, 0) if sitting in the corner to prevent PyAutoGUI FailSafeException."""
    if PYAUTOGUI_AVAILABLE:
        try:
            pos = pyautogui.position()
            if pos.x == 0 and pos.y == 0:
                pyautogui.moveTo(100, 100)
        except Exception:
            pass

def keyboard_type(target_window: str, text: str, press_enter: bool = False, interval: float = 0.02) -> str:
    """Type in short batches, checking Stop and foreground focus between batches."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    typed = 0
    try:
        interval = float(interval)
        if not 0 <= interval <= 0.1:
            return "ERROR: Typing interval must be between 0 and 0.1 seconds."
        pyautogui.FAILSAFE = True
        # PyAutoGUI silently drops Unicode. Choose paste BEFORE sending any keys;
        # never retry a failed/partially typed operation by pasting the whole text.
        if not text.isascii():
            import pyperclip
            previous = pyperclip.paste()
            try:
                pyperclip.copy(text)
                valid, err = _enforce_desktop_and_target(target_window)
                if not valid:
                    return err
                pyautogui.hotkey("ctrl", "v")
                # Give the foreground application time to consume the clipboard.
                time.sleep(0.1)
                typed = len(text)
            finally:
                pyperclip.copy(previous)
        else:
            batch_size = min(8, max(1, int(0.15 / max(interval, 0.001))))
            for offset in range(0, len(text), batch_size):
                valid, err = _enforce_desktop_and_target(target_window)
                if not valid:
                    return f"{err} Stopped after {typed} characters; text may be partial."
                batch = text[offset:offset + batch_size]
                pyautogui.typewrite(batch, interval=interval)
                typed += len(batch)
        valid, err = _enforce_desktop_and_target(target_window)
        if not valid:
            return f"{err} Sent {typed} characters; Enter was not pressed."
        if press_enter:
            pyautogui.press("enter")
            return f"SUCCESS: Typed '{text}' and pressed Enter."
        return f"SUCCESS: Typed '{text}'."
    except Exception as e:
        return f"ERROR typing text: {str(e)}. Input may be partial; inspect before retrying."

def keyboard_hotkey(target_window: str, keys: List[str]) -> str:
    """Executes a keyboard shortcut combination in the verified target window."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        _prevent_corner_failsafe()
        clean_keys = [k.lower().strip() for k in keys if k.strip()]
        if not clean_keys:
            return "ERROR: No keys specified for hotkey."
        pyautogui.hotkey(*clean_keys)
        return f"SUCCESS: Pressed hotkey combination ({' + '.join(clean_keys)})."
    except Exception as e:
        return f"ERROR executing hotkey: {str(e)}"

def keyboard_press(target_window: str, key: str) -> str:
    """Presses a single key in the verified target window."""
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: PyAutoGUI is not available."
    try:
        _prevent_corner_failsafe()
        clean_key = key.lower().strip()
        pyautogui.press(clean_key)
        return f"SUCCESS: Pressed key '{clean_key}'."
    except Exception as e:
        return f"ERROR pressing key: {str(e)}"

def open_windows_settings(page: str = "home") -> str:
    """
    Directly opens the Windows 10/11 Settings app to a specified section.
    Supported pages:
    - 'home' / 'settings': Settings Home
    - 'microphone': Microphone Privacy and app permissions
    - 'camera': Camera Privacy and app permissions
    - 'apps': Installed Apps and features
    - 'startup': Startup Apps configuration
    - 'security' / 'defender': Windows Defender & Security
    - 'sound': Audio and volume settings
    - 'display': Display and brightness
    - 'network': Network and Wi-Fi
    - 'bluetooth': Bluetooth and connected devices
    - 'power': Power, battery, and sleep
    - 'updates': Windows Update
    - 'notifications': System notifications
    """
    key = page.lower().strip().replace(" ", "_").replace("-", "_")
    uri = WINDOWS_SETTINGS_MAP.get(key, f"ms-settings:{page}" if page.startswith("privacy") else "ms-settings:")

    try:
        subprocess.Popen(["cmd", "/c", "start", uri], shell=False)
        return f"SUCCESS: Opened Windows Settings to '{page}' (URI: {uri})."
    except Exception as e:
        return f"ERROR opening Windows Settings: {str(e)}"

def _launch_interactive_app(exe_path: str, args: str = "") -> tuple[bool, str]:
    """
    Spawns an application process directly into the active interactive desktop Session 1 (WinSta0\\Default).
    Uses Windows Task Scheduler one-shot interactive task to break out of isolated subshells,
    with fallbacks to Shell.Application COM and Win32 CreateProcessW.
    """
    if os.name != "nt":
        try:
            subprocess.Popen([exe_path] + (args.split() if args else []))
            return True, f"Launched '{exe_path}'."
        except Exception as e:
            return False, str(e)

    # 1. Clean up stale Telegram locks ONLY if Telegram is NOT already running
    if "telegram" in exe_path.lower():
        try:
            is_running = False
            for p in psutil.process_iter(["name"]):
                if "telegram" in (p.info["name"] or "").lower():
                    is_running = True
                    break
            if not is_running:
                tdata = Path(os.path.expandvars(r"%APPDATA%\Telegram Desktop\tdata"))
                working_lock = tdata / "working"
                if working_lock.exists():
                    working_lock.unlink(missing_ok=True)
                custom_dict = tdata / "dictionaries" / "custom"
                if custom_dict.exists():
                    (tdata / "dictionaries").rename(tdata / "dictionaries.bak")
        except Exception:
            pass

    # 2. Direct Win32 ShellExecuteW launch on the active interactive desktop
    try:
        import ctypes
        working_dir = os.path.dirname(exe_path) if (os.path.isabs(exe_path) and os.path.isfile(exe_path)) else None
        res = ctypes.windll.shell32.ShellExecuteW(None, "open", exe_path, args or None, working_dir, 1)
        if res > 32:
            return True, "Launched interactive process via ShellExecuteW."
    except Exception:
        pass

    # 3. Get short 8.3 path or quote path for task scheduler
    clean_path = exe_path
    try:
        import win32api
        clean_path = win32api.GetShortPathName(exe_path)
    except Exception:
        try:
            ps_short = f"(New-Object -ComObject Scripting.FileSystemObject).GetFile('{exe_path}').ShortPath"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_short], capture_output=True, text=True, timeout=3)
            sp = res.stdout.strip()
            if sp and os.path.exists(sp):
                clean_path = sp
        except Exception:
            clean_path = f'"{exe_path}"'

    # Task Scheduler Interactive Run (Session 1 WinSta0\\Default)
    task_cmd = f"{clean_path} {args}".strip() if args else clean_path
    try:
        create_res = subprocess.run(
            ["schtasks", "/create", "/tn", "JarvisAppLauncher", "/tr", task_cmd, "/sc", "once", "/st", "23:59", "/f", "/it"],
            capture_output=True, text=True, timeout=5
        )
        if create_res.returncode == 0:
            run_res = subprocess.run(
                ["schtasks", "/run", "/tn", "JarvisAppLauncher"],
                capture_output=True, text=True, timeout=5
            )
            if run_res.returncode == 0:
                return True, f"Launched interactive process on WinSta0\\Default via Task Scheduler."
    except Exception:
        pass

    # 3. Fallback: Shell.Application COM ShellExecute
    try:
        working_dir = os.path.dirname(exe_path) if os.path.isfile(exe_path) else ""
        ps_com = f"""
$sa = New-Object -ComObject Shell.Application
$sa.ShellExecute('{exe_path}', '{args}', '{working_dir}', 'open', 1)
"""
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_com], capture_output=True, timeout=5)
        return True, f"Dispatched launch via Shell.Application."
    except Exception:
        pass

    # 4. Fallback: cmd /c start
    try:
        subprocess.Popen(f'cmd /c start "" "{exe_path}" {args}', cwd=os.path.dirname(exe_path) if os.path.isfile(exe_path) else None, shell=True)
        return True, f"Dispatched via shell start."
    except Exception as e:
        return False, str(e)

def _bring_app_window_to_foreground(keyword: str, timeout: float = 3.0) -> bool:
    """
    Attaches to the active input desktop station, locates the window matching
    the title keyword or window class, and brings it to the foreground (SW_RESTORE).
    """
    if os.name != "nt":
        return False

    try:
        import ctypes
        import ctypes.wintypes
        from tools.multimodal_tools import _ensure_input_desktop

        _ensure_input_desktop()
        u = ctypes.windll.user32
        hDesk = u.OpenInputDesktop(0, False, 0x1ff)
        if hDesk:
            u.SetThreadDesktop(hDesk)

        SW_RESTORE = 9
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        matching_pids = set()
        try:
            for p in psutil.process_iter(['pid', 'name']):
                if keyword.lower() in (p.info['name'] or '').lower():
                    matching_pids.add(p.info['pid'])
        except Exception:
            pass

        start = time.time()
        while time.time() - start < timeout:
            hwnds = []

            def enum_cb(hwnd, lparam):
                length = u.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                u.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

                cls_buff = ctypes.create_unicode_buffer(256)
                u.GetClassNameW(hwnd, cls_buff, 256)
                cls_name = cls_buff.value

                w_pid = ctypes.wintypes.DWORD()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))

                kw = keyword.lower()
                cls_low = cls_name.lower()
                title_low = title.lower()
                if cls_low in ("ime", "msctfime ui") or title_low in ("default ime", "msctfime ui") or "trayicon" in cls_low or "mediacontrols" in cls_low:
                    return True
                if not u.IsWindowVisible(hwnd):
                    return True
                rect = ctypes.wintypes.RECT()
                u.GetWindowRect(hwnd, ctypes.byref(rect))
                if (rect.right - rect.left) <= 30 or (rect.bottom - rect.top) <= 30:
                    return True

                if w_pid.value in matching_pids:
                    hwnds.append(hwnd)
                elif kw in title_low or kw in cls_low:
                    hwnds.append(hwnd)
                return True

            u.EnumWindows(WNDENUMPROC(enum_cb), 0)
            if hwnds:
                for hwnd in hwnds:
                    u.ShowWindow(hwnd, SW_RESTORE)
                    u.SetForegroundWindow(hwnd)
                    u.BringWindowToTop(hwnd)
                return True
            time.sleep(0.3)
    except Exception:
        pass
    return False

def _activate_window_input(target_window: str) -> tuple[bool, str]:
    """Activate input on the verified foreground window; never select a different matching window."""
    valid, reason = _enforce_desktop_and_target(target_window)
    if not valid:
        return False, reason
    if not PYAUTOGUI_AVAILABLE:
        return False, "PyAutoGUI is unavailable."
    try:
        if os.name == "nt":
            from tools.multimodal_tools import _ensure_input_desktop
            _ensure_input_desktop()
        import pygetwindow as gw
        window = gw.getActiveWindow()
        if window is None or window.width <= 30 or window.height <= 30:
            return False, "No usable foreground window."
        valid, reason = _enforce_desktop_and_target(target_window)
        current = gw.getActiveWindow()
        if not valid or current is None or current._hWnd != window._hWnd:
            return False, "Foreground changed before input activation. " + reason
        pyautogui.FAILSAFE = True
        pyautogui.click(window.left + min(150, window.width // 2), window.top + 15)
        return verify_foreground_window(target_window)
    except Exception as exc:
        return False, f"Window input activation was interrupted ({type(exc).__name__})."


def open_app(target: str) -> str:
    """
    Opens any Windows application by name, executable, URI, or file path,
    ensuring it launches interactively on the physical desktop and verifies it is visible in the foreground.
    Examples: 'telegram', 'notepad', 'calc', 'msedge', 'chrome', 'code', 'explorer', 'cmd', 'settings'.
    """
    if not target or not str(target).strip():
        return "ERROR: An explicit target application is required."

    clean_target = target.lower().strip()

    # Check if target is a known settings page
    if clean_target in WINDOWS_SETTINGS_MAP or "setting" in clean_target:
        page = clean_target.replace("settings", "").replace("setting", "").strip() or "home"
        open_windows_settings(page)
        start = time.time()
        while time.time() - start < 3.0:
            ok, _ = verify_foreground_window("settings")
            if ok:
                return f"SUCCESS: Opened Windows Settings ('{page}') and verified visible in foreground."
            time.sleep(0.2)
        return f"ERROR: Dispatched Windows Settings ('{page}'), but window failed to become visible foreground."

    avail, desk_msg = is_desktop_available()
    if not avail:
        return f"ERROR: Desktop unavailable ({desk_msg})"

    resolved_path = None
    args = ""

    # 1. Check known application aliases
    if clean_target in COMMON_APP_MAP:
        for candidate in COMMON_APP_MAP[clean_target]:
            expanded = os.path.expandvars(candidate)
            if os.path.isabs(expanded) and os.path.exists(expanded):
                resolved_path = expanded
                break
            elif not os.path.isabs(expanded):
                resolved_path = expanded
                break

    # 2. Check if direct target is an existing path or expanded environment path
    if not resolved_path:
        expanded = os.path.expandvars(target)
        if os.path.exists(expanded):
            resolved_path = expanded
        else:
            which = shutil.which(target)
            if which and os.path.isabs(which) and os.path.exists(which):
                resolved_path = which

    # 3. Launch via interactive spawner if path resolved
    if resolved_path and os.path.isabs(resolved_path):
        ok, msg = _launch_interactive_app(resolved_path, args)
        if not ok:
            return f"ERROR launching '{clean_target}': {msg}"
    else:
        # Fallback for URI schemes, system PATH executables, or commands
        try:
            subprocess.Popen(f'cmd /c start "" "{resolved_path or target}"', shell=True)
        except Exception as e:
            return f"ERROR launching '{target}': {str(e)}"

    # Polling verification: open_app MUST NOT claim SUCCESS solely because launch was dispatched; verify visible foreground!
    expected_window = {"tg": "telegram", "vscode": "code", "task_manager": "taskmgr"}.get(clean_target, clean_target)
    if os.path.isabs(target):
        expected_window = os.path.splitext(os.path.basename(target))[0]
    _bring_app_window_to_foreground(expected_window, timeout=2.5)
    start = time.time()
    last_err = ""
    while time.time() - start < 4.0:
        verified, _ = verify_foreground_window(expected_window)
        if verified:
            activated, reason = _activate_window_input(expected_window)
            if activated:
                return f"SUCCESS: Opened application '{clean_target}' and verified visible in foreground."
            last_err = reason
            # Poll only while a newly launched window is not usable yet. Do not
            # retry an input exception, Stop, or changed focus with more clicks.
            if reason != "No usable foreground window.":
                return f"ERROR: Application opened but input activation failed: {reason}"
        time.sleep(0.3)

    if last_err:
        return f"ERROR: Application opened but input activation failed: {last_err}"
    return f"ERROR: Launched '{clean_target}', but failed to become visible foreground window."

def focus_window(title_keyword: str) -> str:
    """Brings an application window matching the title keyword to the foreground and verifies visible foreground."""
    if not title_keyword or not str(title_keyword).strip():
        return "ERROR: An explicit window title keyword is required."

    clean_keyword = title_keyword.lower().strip()

    avail, desk_msg = is_desktop_available()
    if not avail:
        return f"ERROR: Desktop unavailable ({desk_msg})"

    # First attempt: Win32 InputDesktop Window Normalizer
    _bring_app_window_to_foreground(clean_keyword, timeout=2.0)
    verified, _ = verify_foreground_window(clean_keyword)
    if verified:
        activated, reason = _activate_window_input(clean_keyword)
        if not activated:
            return f"ERROR: Input activation failed: {reason}"
        return f"SUCCESS: Focused window matching '{title_keyword}' and verified visible in foreground."

    # Second attempt: pygetwindow
    try:
        import pygetwindow as gw
        matches = [w for w in gw.getAllWindows() if clean_keyword in w.title.lower()]
        if matches:
            target_win = matches[0]
            if target_win.isMinimized:
                target_win.restore()
            target_win.activate()
            time.sleep(0.3)
            verified, _ = verify_foreground_window(clean_keyword)
            if verified:
                activated, reason = _activate_window_input(clean_keyword)
                if not activated:
                    return f"ERROR: Input activation failed: {reason}"
                return f"SUCCESS: Focused window '{target_win.title}' and verified visible in foreground."
    except Exception:
        pass

    # Fallback via PowerShell Win32 AppActivate
    ps_cmd = f"""
$ws = New-Object -ComObject WScript.Shell
$success = $ws.AppActivate('{clean_keyword}')
if ($success) {{ Write-Output "SUCCESS" }} else {{ Write-Output "NOT_FOUND" }}
"""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        if "SUCCESS" in res.stdout:
            time.sleep(0.3)
            verified, _ = verify_foreground_window(clean_keyword)
            if verified:
                activated, reason = _activate_window_input(clean_keyword)
                if not activated:
                    return f"ERROR: Input activation failed: {reason}"
                return f"SUCCESS: Activated application matching '{title_keyword}' and verified visible in foreground."
    except Exception:
        pass

    return f"ERROR: Failed to bring window matching '{title_keyword}' to visible foreground."

def click_screen_element(
    target_window: str,
    target_description: str,
    clicks: int = 1,
    button: str = "left"
) -> str:
    """
    Visual Grounding & Clicking within verified target window:
    Captures the live screen, sends the screenshot to Gemini Vision to pinpoint
    the exact (x, y) coordinates of the requested UI element, and clicks it!
    """
    valid, err = _enforce_desktop_and_target(target_window)
    if not valid:
        return err
    from tools.multimodal_tools import _get_vision_client, _ensure_input_desktop
    from PIL import ImageGrab

    _ensure_input_desktop()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    temp_img = SCREENSHOTS_DIR / f"grounding_{int(time.time())}.png"

    try:
        screenshot = ImageGrab.grab()
        screen_w, screen_h = screenshot.size
        screenshot.save(temp_img, format="PNG")
    except Exception as e:
        return f"ERROR capturing screen for visual grounding: {str(e)}"

    try:
        with open(temp_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        client, model = _get_vision_client()

        prompt = (
            f"You are a computer use visual grounding agent. Screen resolution is {screen_w}x{screen_h}.\n"
            f"Locate the UI element: '{target_description}'.\n"
            f"Determine the center pixel coordinates (x, y) where a user should click.\n"
            f"Return ONLY a JSON object with this exact schema:\n"
            f'{{"x": <integer>, "y": <integer>, "found": true, "confidence": <float>, "element": "<label>"}}\n'
            f"If the element is not visible or cannot be found, return:\n"
            f'{{"found": false, "reason": "<why not found>"}}\n'
            f"Return ONLY valid JSON."
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }
            ],
            temperature=0.1
        )

        reply = resp.choices[0].message.content.strip()
        # Parse JSON from response
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if not match:
            return f"NOTICE: Could not parse localization coordinates for '{target_description}'. Gemini response: {reply}"

        coord_data = json.loads(match.group(0))
        if coord_data.get("found") is not True:
            return f"NOTICE: UI element '{target_description}' was not found on screen. Reason: {coord_data.get('reason', 'Not visible')}"

        if not 0.75 <= float(coord_data.get("confidence", 0)) <= 1.0:
            return "ERROR: Visual target confidence is too low. Inspect the current screen before retrying."
        click_x = int(coord_data["x"])
        click_y = int(coord_data["y"])
        if not (0 <= click_x < screen_w and 0 <= click_y < screen_h):
            return "ERROR: Visual target coordinates are outside the captured screen. No click was sent."

        # Perform the click
        click_res = mouse_click(target_window=target_window, x=click_x, y=click_y, button=button, clicks=clicks)
        if not click_res.startswith("SUCCESS:"):
            return click_res
        return (
            f"SUCCESS: Visual grounding located '{target_description}' at ({click_x}, {click_y}) "
            f"[{coord_data.get('element', '')}]. {click_res}"
        )
    except Exception as e:
        return f"ERROR in visual click: {str(e)}"

def configure_laptop_permissions(permission_type: str = "all") -> str:
    """
    Applies comprehensive native Windows permissions to J.A.R.V.I.S. and desktop applications:
    - Windows Microphone Privacy Settings for desktop apps
    - Windows Camera Privacy Settings for desktop apps
    - Windows Defender Firewall rules for Gateway ports 8000 & 8443
    - PowerShell Execution Policy set to RemoteSigned
    - Win32 Long Path support enabled in Registry
    """
    results = []

    # 1. Microphone & Camera Registry Permissions
    try:
        mic_reg = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone"
        mic_cmd = f"""
if (-not (Test-Path '{mic_reg}')) {{ New-Item -Path '{mic_reg}' -Force | Out-Null }}
Set-ItemProperty -Path '{mic_reg}' -Name 'Value' -Value 'Allow' -Force
$np = '{mic_reg}\\NonPackaged'
if (-not (Test-Path $np)) {{ New-Item -Path $np -Force | Out-Null }}
Set-ItemProperty -Path $np -Name 'Value' -Value 'Allow' -Force
Write-Output 'OK'
"""
        res = subprocess.run(["powershell", "-NoProfile", "-Command", mic_cmd], capture_output=True, text=True, timeout=8)
        if "OK" in res.stdout:
            results.append("✓ Microphone privacy consent enabled for desktop apps.")
        else:
            results.append("⚠ Microphone registry notice: " + res.stderr.strip()[:100])
    except Exception as e:
        results.append(f"⚠ Microphone permission: {e}")

    # 2. PowerShell Execution Policy
    try:
        ps_cmd = "Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force; Write-Output 'OK'"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
        results.append("✓ PowerShell execution policy set to RemoteSigned.")
    except Exception as e:
        results.append(f"⚠ Execution policy notice: {e}")

    # 3. Check Admin Elevation for Firewall and Long Paths
    is_admin_cmd = "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", is_admin_cmd], capture_output=True, text=True, timeout=5)
        is_admin = "True" in res.stdout
    except Exception:
        is_admin = False

    if is_admin:
        # Run firewall configuration
        fw_script = BASE_DIR / "scripts" / "configure_permissions.ps1"
        if fw_script.exists():
            try:
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(fw_script)], timeout=15)
                results.append("✓ Windows Defender Firewall rules and Long Paths configured with Administrator privileges.")
            except Exception as e:
                results.append(f"⚠ Firewall script notice: {e}")
    else:
        results.append("ℹ For full Windows Defender Firewall elevation, run 'scripts/grant_permissions.bat' as Administrator.")

    return "Windows Laptop Permissions Configuration:\n" + "\n".join(results)

def run_elevated_command(command: str) -> str:
    """
    Executes a high-privilege command via Windows UAC elevation prompt (RunAs).
    Allows running administrative PowerShell tasks.
    """
    try:
        ps_cmd = f"Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -Command \"{command}\"'"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=10)
        return f"SUCCESS: Elevated command dispatched via Windows UAC: '{command}'."
    except Exception as e:
        return f"ERROR dispatching elevated command: {str(e)}"
