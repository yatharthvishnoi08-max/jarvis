import re
import time
import uuid
import asyncio
from typing import Dict, Any, Tuple, Optional
from core.audit import audit_logger

# Policy definitions
POLICY_READ = "READ"
POLICY_CONFIRM = "CONFIRM"
POLICY_CRITICAL = "CRITICAL"
POLICY_BLOCKED = "BLOCKED"

# Blocked command patterns (Lethal / Catastrophic / Credential Theft / Security Tampering)
BLOCKED_PATTERNS = [
    # Disk formatting / partitioning
    r"\bdiskpart\b",
    r"\bformat\s+[A-Za-z]:",
    # Root recursive deletions
    r"Remove-Item.*-Recurse\s+['\"]?([A-Za-z]:\\?|C:\\Windows|C:\\Users)['\"]?",
    r"rmdir\s+/(s|S)\s+['\"]?([A-Za-z]:\\?|C:\\Windows|C:\\Users)['\"]?",
    r"del\s+/(s|S)\s+['\"]?([A-Za-z]:\\?|C:\\Windows)['\"]?",
    # Credential extraction
    r"\bmimikatz\b",
    r"\bprocdump.*lsass\b",
    r"\bntdsutil\b",
    r"Get-Process.*lsass",
    # Disabling security protections
    r"Set-MpPreference.*-DisableRealtimeMonitoring\s+\$true",
    r"Set-MpPreference.*-DisableBehaviorMonitoring",
    r"sc\s+stop\s+WinDefend",
    r"net\s+stop\s+WinDefend",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # Fork bomb
]

# Critical patterns requiring high-level warning and explicit confirmation
CRITICAL_PATTERNS = [
    r"\b(Remove-Item|rmdir|del)\b",
    r"\b(winget|pip|npm|choco)\s+install\b",
    r"\breg\s+(add|delete|import|copy)\b",
    r"\bSet-ItemProperty.*(HKLM|HKCU)\b",
    r"\b(net\s+user|net\s+localgroup)\b",
    r"\b(New-LocalUser|Remove-LocalUser)\b",
    r"\bSet-NetFirewallRule\b",
    r"\b(runas|Start-Process.*-Verb\s+RunAs)\b",
    r"\bStop-Service\b",
    r"\bStop-Computer\b",
    r"\bRestart-Computer\b"
]

def classify_tool_call(tool_name: str, args: Dict[str, Any]) -> Tuple[str, str]:
    """
    Evaluates tool name and arguments against security policies.
    Returns: (POLICY_LEVEL, reason)
    """
    # 1. READ tools & Direct GUI Automation
    read_tools = [
        "read_file", "list_directory", "get_system_stats", "list_employees",
        "read_employee_sop", "read_memory", "web_search", "fetch_web_page",
        "calculator", "read_pdf", "get_weather", "git_status", "git_diff",
        "git_log", "list_skills", "inspect_skill", "read_skill", "generate_morning_digest",
        "run_deep_research", "analyze_image", "analyze_screen", "capture_screen",
        "get_battery_status", "get_clipboard", "set_clipboard", "control_media", "find_files",
        "mouse_click", "mouse_move", "mouse_scroll", "mouse_drag", "get_mouse_position",
        "keyboard_type", "keyboard_press", "keyboard_hotkey", "open_windows_settings",
        "open_app", "focus_window", "click_screen_element", "configure_laptop_permissions"
    ]
    if tool_name in read_tools:
        return POLICY_READ, f"Direct execution / inspection via '{tool_name}'."

    # 1.1 Run elevated command
    if tool_name == "run_elevated_command":
        cmd = args.get("command", "")
        return POLICY_CRITICAL, f"Administrator UAC elevation requested for command: {cmd}"

    # 1.1 Manage applications
    if tool_name == "manage_application":
        act = args.get("action", "").lower().strip()
        name = args.get("name", "")
        if act == "list":
            return POLICY_READ, "List active running applications."
        elif act == "launch":
            return POLICY_READ, f"Launch application '{name}'."
        elif act == "close":
            return POLICY_CONFIRM, f"Terminate process / application '{name}'."
        return POLICY_CONFIRM, f"Application action '{act}'."

    # 2. PowerShell analysis
    if tool_name == "execute_powershell":
        cmd = args.get("command", "")
        # Check BLOCKED
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return POLICY_BLOCKED, f"Dangerous command blocked by policy: matched pattern '{pattern}'."

        # Check CRITICAL
        for pattern in CRITICAL_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return POLICY_CRITICAL, f"High-impact operation requiring explicit user confirmation: '{pattern}'."

        # Otherwise CONFIRM
        return POLICY_CONFIRM, "PowerShell execution requires user authorization."

    # 3. File modifications
    if tool_name == "write_file":
        path = args.get("path", "")
        if any(p in path.lower() for p in ["windows", "system32", "program files"]):
            return POLICY_CRITICAL, "Writing to system directory requires critical confirmation."
        return POLICY_CONFIRM, f"Creating or modifying file at '{path}'."

    # 4. Memory and SOP modifications
    if tool_name in ["update_employee_sop", "log_learned_rule"]:
        return POLICY_CONFIRM, f"System rule / employee SOP modification via {tool_name}."

    # Default unknown tools to CONFIRM
    return POLICY_CONFIRM, f"Tool '{tool_name}' requires confirmation."


class ApprovalRequest:
    def __init__(
        self,
        session_id: str,
        tool: str,
        args: Dict[str, Any],
        policy_level: str,
        summary: str,
        ttl_seconds: int = 300
    ):
        self.id = str(uuid.uuid4())
        self.session_id = session_id
        self.tool = tool
        self.args = args
        self.policy_level = policy_level
        self.summary = summary
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.status = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
        self.single_use = True
        self.event = asyncio.Event()

    def is_expired(self) -> bool:
        if self.status == "PENDING" and time.time() > self.expires_at:
            self.status = "EXPIRED"
            return True
        return self.status == "EXPIRED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool": self.tool,
            "args": self.args,
            "policy_level": self.policy_level,
            "summary": self.summary,
            "created_at": int(self.created_at),
            "expires_at": int(self.expires_at),
            "status": self.status,
            "ttl_remaining": max(0, int(self.expires_at - time.time()))
        }


class ApprovalManager:
    def __init__(self):
        self.requests: Dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        session_id: str,
        tool: str,
        args: Dict[str, Any],
        policy_level: str,
        summary: str
    ) -> ApprovalRequest:
        req = ApprovalRequest(session_id, tool, args, policy_level, summary)
        self.requests[req.id] = req
        audit_logger.log_event(
            event_type="APPROVAL_REQUESTED",
            session_id=session_id,
            tool=tool,
            args=args,
            policy=policy_level,
            status="PENDING",
            detail=summary
        )
        return req

    def decide(self, request_id: str, decision: str) -> Tuple[bool, str]:
        """
        Processes a single-use decision ('approve' or 'reject').
        Returns (success, message).
        """
        req = self.requests.get(request_id)
        if not req:
            return False, "Approval request not found."

        if req.is_expired():
            return False, "Approval request has expired."

        if req.status != "PENDING":
            return False, f"Approval request already finalized as {req.status}."

        if decision.lower() in ["approve", "approved", "yes"]:
            req.status = "APPROVED"
            req.event.set()
            audit_logger.log_event(
                event_type="APPROVAL_DECIDED",
                session_id=req.session_id,
                tool=req.tool,
                args=req.args,
                policy=req.policy_level,
                status="APPROVED",
                detail="User approved operation."
            )
            return True, "Operation approved."
        else:
            req.status = "REJECTED"
            req.event.set()
            audit_logger.log_event(
                event_type="APPROVAL_DECIDED",
                session_id=req.session_id,
                tool=req.tool,
                args=req.args,
                policy=req.policy_level,
                status="REJECTED",
                detail="User rejected operation."
            )
            return True, "Operation rejected."

    def cancel_session_approvals(self, session_id: str):
        """Cancels all pending approvals for a session on emergency stop."""
        for req in self.requests.values():
            if req.session_id == session_id and req.status == "PENDING":
                req.status = "CANCELLED"
                req.event.set()

    def get_pending_requests(self, session_id: Optional[str] = None) -> list:
        pending = []
        for req in list(self.requests.values()):
            if req.is_expired():
                continue
            if req.status == "PENDING":
                if session_id is None or req.session_id == session_id:
                    pending.append(req.to_dict())
        return pending

approval_manager = ApprovalManager()
