import os
import re
import subprocess
import psutil
from pathlib import Path
from typing import Optional

BLOCKED_PATTERNS = [
    r"rmdir\s+/s",
    r"Remove-Item.*-Recurse\s+[A-Za-z]:\\?$",
    r"diskpart",
    r"format\s+[A-Za-z]:",
    r"reg\s+delete\s+HKLM",
    r":(){ :|:& };:"
]

def execute_powershell(command: str) -> str:
    """Executes a PowerShell command on the Windows host and returns stdout and stderr."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"BLOCKED BY SAFETY POLICY: Command matched restricted pattern '{pattern}'."
    
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=45
        )
        output = res.stdout.strip()
        errors = res.stderr.strip()
        
        result_parts = []
        if output:
            result_parts.append(f"STDOUT:\n{output}")
        if errors:
            result_parts.append(f"STDERR:\n{errors}")
        if not output and not errors:
            result_parts.append(f"Process completed with exit code {res.returncode} (No output).")
        return "\n\n".join(result_parts)
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 45 seconds."
    except Exception as e:
        return f"ERROR executing powershell: {str(e)}"

def read_file(path: str) -> str:
    """Reads the text content of a file."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"ERROR: File not found at '{path}'."
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Writes or overwrites text content to a file, creating parent directories if needed."""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"SUCCESS: Written {len(content)} characters to '{path}'."
    except Exception as e:
        return f"ERROR writing file: {str(e)}"

def list_directory(path: str = ".") -> str:
    """Lists files and folders inside a directory."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"ERROR: Directory '{path}' does not exist."
        items = list(p.iterdir())
        lines = [f"{'[DIR] ' if i.is_dir() else '[FILE]'} {i.name}" for i in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))]
        return "\n".join(lines) if lines else "(Directory is empty)"
    except Exception as e:
        return f"ERROR listing directory: {str(e)}"

def get_system_stats() -> str:
    """Returns current CPU, RAM, and disk utilization of the laptop."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        
        return (
            f"CPU Usage: {cpu}%\n"
            f"RAM Usage: {ram.percent}% (Used {ram.used // (1024**2)} MB / Total {ram.total // (1024**2)} MB)\n"
            f"Disk C: Usage: {disk.percent}% (Free {disk.free // (1024**3)} GB / Total {disk.total // (1024**3)} GB)"
        )
    except Exception as e:
        return f"ERROR getting system stats: {str(e)}"

def get_battery_status() -> str:
    """Returns real-time laptop battery percentage, power plug state, and estimated runtime."""
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return "No battery detected (Desktop PC or AC powered)."
        percent = round(battery.percent, 1)
        plugged = "Plugged in (Charging)" if battery.power_plugged else "Unplugged (On Battery)"
        if battery.secsleft == psutil.POWER_TIME_UNLIMITED:
            time_str = "Full / AC power"
        elif battery.secsleft == psutil.POWER_TIME_UNKNOWN:
            time_str = "Calculating remaining duration..."
        else:
            mins = battery.secsleft // 60
            hrs = mins // 60
            rem_mins = mins % 60
            time_str = f"{hrs}h {rem_mins}m remaining"
        return f"Battery Level: {percent}%\nPower Status: {plugged}\nEstimated Runtime: {time_str}"
    except Exception as e:
        return f"ERROR getting battery telemetry: {str(e)}"

def get_clipboard() -> str:
    """Reads current text content from the Windows clipboard."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5
        )
        text = res.stdout.strip()
        if not text:
            return "(Clipboard is empty or contains non-text content)"
        return text
    except Exception as e:
        return f"ERROR reading clipboard: {str(e)}"

def set_clipboard(text: str) -> str:
    """Copies given text to the Windows clipboard."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            input=text, text=True, capture_output=True, timeout=5
        )
        return f"SUCCESS: Copied {len(text)} characters to the Windows clipboard."
    except Exception as e:
        return f"ERROR setting clipboard: {str(e)}"

def control_media(action: str) -> str:
    """
    Controls host media and master volume.
    Supported actions: 'volume_up', 'volume_down', 'mute', 'unmute', 'play_pause', 'next_track', 'prev_track'.
    """
    action = action.lower().strip()
    key_map = {
        "mute": 173,
        "unmute": 173,
        "volume_down": 174,
        "volume_up": 175,
        "next_track": 176,
        "prev_track": 177,
        "stop": 178,
        "play_pause": 179
    }
    if action not in key_map:
        return f"ERROR: Unsupported media action '{action}'. Supported: {list(key_map.keys())}"
    key_code = key_map[action]
    repeats = 5 if "volume" in action else 1
    ps_cmd = f"(1..{repeats}) | ForEach-Object {{ (New-Object -ComObject WScript.Shell).SendKeys([char]{key_code}) }}"
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=5)
        return f"SUCCESS: Executed media command '{action}'."
    except Exception as e:
        return f"ERROR controlling media: {str(e)}"

def manage_application(action: str, name: str = "") -> str:
    """
    Manages Windows desktop applications.
    Supported actions:
    - 'launch': Starts an application by name or executable (e.g. 'notepad', 'calc', 'code', 'msedge').
    - 'close': Terminates a running process by name.
    - 'list': Returns a list of active running user applications.
    """
    action = action.lower().strip()
    if action == "list":
        apps = []
        for proc in psutil.process_iter(['name', 'status']):
            try:
                pname = proc.info.get('name') or ""
                if pname.lower().endswith('.exe') and proc.info.get('status') == psutil.STATUS_RUNNING:
                    apps.append(pname)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        unique_apps = sorted(list(set(apps)))[:35]
        return "Active Running Applications (Sample):\n" + "\n".join([f"- {a}" for a in unique_apps])

    elif action == "launch":
        if not name:
            return "ERROR: Please specify an application name to launch (e.g. 'notepad', 'calc', 'code')."
        try:
            subprocess.Popen(name, shell=True)
            return f"SUCCESS: Launched application '{name}'."
        except Exception as e:
            return f"ERROR launching application '{name}': {str(e)}"

    elif action == "close":
        if not name:
            return "ERROR: Please specify an application name to close."
        closed_count = 0
        target = name.lower()
        target_exe = target if target.endswith(".exe") else f"{target}.exe"
        for proc in psutil.process_iter(['name']):
            try:
                if (proc.info.get('name') or "").lower() in (target, target_exe):
                    proc.terminate()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if closed_count > 0:
            return f"SUCCESS: Terminated {closed_count} instance(s) of '{name}'."
        return f"NOTICE: No running process matched '{name}'."
    else:
        return f"ERROR: Unknown action '{action}'. Use 'launch', 'close', or 'list'."

def find_files(pattern: str, search_path: str = ".", max_results: int = 15) -> str:
    """
    Recursively searches for files matching a pattern or substring within search_path,
    safely excluding hidden and heavy development directories (.venv, node_modules, etc.).
    """
    base = Path(search_path).resolve()
    if not base.exists():
        return f"ERROR: Path '{search_path}' does not exist."

    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", "audio_cache", ".pytest_cache", "memory"}
    matches = []

    try:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            for file in files:
                if Path(file).match(pattern) or pattern.lower() in file.lower():
                    matches.append(str(Path(root) / file))
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break

        if not matches:
            return f"No files matching '{pattern}' found in '{search_path}'."
        return f"Found {len(matches)} matching file(s):\n" + "\n".join([f"- {m}" for m in matches])
    except Exception as e:
        return f"ERROR finding files: {str(e)}"
