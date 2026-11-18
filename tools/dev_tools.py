"""Developer tools for version control inspection, inspired by OpenJarvis git tools."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

def _run_git(args: list[str], max_chars: int = 4000) -> str:
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        res = out if out else err
        if not res:
            res = f"Git command completed (Exit code {proc.returncode})"
        if len(res) > max_chars:
            res = res[:max_chars] + f"\n... [Truncated {len(res) - max_chars} characters]"
        return res
    except Exception as e:
        return f"Git Error: {str(e)}"

def git_status() -> str:
    """Return the current git working tree status (--short)."""
    return _run_git(["status", "--short", "--branch"])

def git_diff(staged: bool = False, file_path: Optional[str] = None) -> str:
    """Return git diff for unstaged or staged changes."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    if file_path:
        args.extend(["--", file_path])
    return _run_git(args)

def git_log(limit: int = 5) -> str:
    """Return the recent git commit log."""
    return _run_git(["log", f"-n{max(1, limit)}", "--oneline", "--decorate"])
