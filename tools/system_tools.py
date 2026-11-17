import os
import re
import subprocess
import psutil
from pathlib import Path

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
