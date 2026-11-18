import json
import time
import asyncio
from datetime import date
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from core.client import get_client
from core.auth import redact_secrets
from core.audit import audit_logger
from core.approvals import (
    classify_tool_call,
    approval_manager,
    POLICY_READ,
    POLICY_CONFIRM,
    POLICY_CRITICAL,
    POLICY_BLOCKED,
)
from core.session import Session, session_manager
from tools.planner import add_task, complete_task, list_tasks
from tools.system_tools import (
    execute_powershell,
    read_file,
    write_file,
    list_directory,
    get_system_stats,
)
from tools.meta_tools import (
    list_employees,
    read_employee_sop,
    update_employee_sop,
    log_learned_rule,
    read_memory,
)

BASE_DIR = Path(__file__).resolve().parent.parent

TOOL_FUNCTIONS = {
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "execute_powershell": execute_powershell,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "get_system_stats": get_system_stats,
    "list_employees": list_employees,
    "read_employee_sop": read_employee_sop,
    "update_employee_sop": update_employee_sop,
    "log_learned_rule": log_learned_rule,
    "read_memory": read_memory,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "add_task",
        "description": "Save a requested personal commitment across conversations. This records a task without scheduling a notification.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string", "description": "The user's task."},
            "due": {"type": "string", "description": "today, tomorrow, or YYYY-MM-DD. Omit if unspecified."}
        }, "required": ["title"]}
    }},
    {"type": "function", "function": {
        "name": "list_tasks",
        "description": "Read the owner's planner. Today includes overdue tasks. All includes undated and future open tasks.",
        "parameters": {"type": "object", "properties": {
            "view": {"type": "string", "enum": ["today", "all"]}
        }}
    }},
    {"type": "function", "function": {
        "name": "complete_task",
        "description": "Mark the user's chosen task done. Resolve the ID with list_tasks and clarify ambiguous matches.",
        "parameters": {"type": "object", "properties": {
            "task_id": {"type": "integer", "description": "Planner task ID."}
        }, "required": ["task_id"]}
    }},
    {
        "type": "function",
        "function": {
            "name": "execute_powershell",
            "description": "Run a PowerShell command on the Windows host.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact PowerShell command to run."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text content of a file on the machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or create a text file with content on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to create or overwrite."},
                    "content": {"type": "string", "description": "The full text content to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a given folder path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list. Defaults to current working directory."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Get current CPU usage, RAM utilization, and free disk space.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "List all active employee subagents and their roles.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_employee_sop",
            "description": "Read the current SOP and guidelines of an employee agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "Name of the employee."}
                },
                "required": ["employee_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_employee_sop",
            "description": "Permanently update or add a new operational rule to an employee agent's SOP based on user feedback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "Name of the employee to update."},
                    "feedback_or_new_rule": {"type": "string", "description": "The exact rule or correction to append."}
                },
                "required": ["employee_name", "feedback_or_new_rule"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_learned_rule",
            "description": "Store a long-term lesson, user preference, or system quirk into persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category (e.g. 'powershell', 'workflow', 'user_pref')."},
                    "rule": {"type": "string", "description": "The rule or lesson to record."}
                },
                "required": ["category", "rule"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "Read all recorded rules, system memories, and user preferences.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

class JarvisAgent:
    def __init__(self):
        self.client, self.model_name = get_client()

    def build_system_prompt(self) -> str:
        prompt_file = BASE_DIR / "SOUL.md"
        if not prompt_file.exists():
            prompt_file = BASE_DIR / "agents" / "central_brain.md"
        base_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "You are JARVIS."

        employees_info = list_employees()
        memory_info = read_memory()

        return (
            f"{base_prompt}\n\n"
            f"Local planner date: {date.today().isoformat()}. Use planner tools for commitments, "
            "including daily briefings. Only claim a task change after its tool succeeds.\n\n"
            f"## Current Team Roster:\n{employees_info}\n\n"
            f"## Persistent System Memory:\n{memory_info}\n"
        )

    async def chat_async(
        self,
        session: Session,
        user_input: str,
        on_thought: Optional[Callable[[str], None]] = None,
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
        on_approval_needed: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        Asynchronous ReAct loop with:
        - Per-session message isolation
        - Emergency stop check
        - Strict tool policy checks (READ, CONFIRM, CRITICAL, BLOCKED)
        - Asynchronous user approval gates
        - Audit trail logging
        """
        session.reset_cancellation()
        session.add_message(role="user", content=user_input)

        # Assemble conversation history for the LLM
        messages = [{"role": "system", "content": self.build_system_prompt()}]
        for m in session.messages:
            msg_obj = {"role": m["role"], "content": m["content"]}
            if m.get("tool_calls"):
                msg_obj["tool_calls"] = m["tool_calls"]
            if m.get("tool_call_id"):
                msg_obj["tool_call_id"] = m["tool_call_id"]
            messages.append(msg_obj)

        max_turns = 10
        loop = asyncio.get_event_loop()

        for turn in range(max_turns):
            if session.is_cancelled:
                msg = "[EMERGENCY STOP] Operation cancelled by user."
                session.add_message(role="assistant", content=msg)
                return msg

            # Run LLM completion in thread to prevent blocking the event loop
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        tools=TOOL_SCHEMAS,
                        tool_choice="auto",
                        temperature=0.3
                    )
                )
            except Exception as e:
                err_text = f"LLM Inference Error: {str(e)}"
                session.add_message(role="assistant", content=err_text)
                return err_text

            if session.is_cancelled:
                msg = "[EMERGENCY STOP] Operation cancelled by user."
                session.add_message(role="assistant", content=msg)
                return msg

            message = response.choices[0].message

            # If no tool calls, this is the final answer
            if not message.tool_calls:
                final_content = redact_secrets(message.content or "")
                session.add_message(role="assistant", content=final_content)
                return final_content

            # Format tool calls
            formatted_tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

            assistant_content = redact_secrets(message.content or "")
            if on_thought and assistant_content:
                on_thought(assistant_content)

            session.add_message(
                role="assistant",
                content=assistant_content,
                tool_calls=formatted_tool_calls
            )
            messages.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": formatted_tool_calls
            })

            # Execute tool calls with policy check
            for tc in message.tool_calls:
                if session.is_cancelled:
                    msg = "[EMERGENCY STOP] Operation cancelled by user."
                    session.add_message(role="assistant", content=msg)
                    return msg

                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                if not isinstance(args, dict):
                    args = {}

                # 1. Evaluate tool policy
                policy_level, policy_reason = classify_tool_call(fn_name, args)

                audit_logger.log_event(
                    event_type="TOOL_ATTEMPT",
                    session_id=session.id,
                    tool=fn_name,
                    args=args,
                    policy=policy_level,
                    status="ATTEMPT",
                    detail=policy_reason
                )

                # 2. Check BLOCKED
                if policy_level == POLICY_BLOCKED:
                    blocked_result = f"SECURITY POLICY BLOCK: Operation '{fn_name}' was blocked. Reason: {policy_reason}"
                    audit_logger.log_event(
                        event_type="TOOL_BLOCKED",
                        session_id=session.id,
                        tool=fn_name,
                        args=args,
                        policy=policy_level,
                        status="BLOCKED",
                        detail=policy_reason
                    )
                    session.add_message(role="tool", content=blocked_result, tool_call_id=tc.id)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": blocked_result})
                    continue

                # 3. Check CONFIRM or CRITICAL (requires approval)
                if policy_level in [POLICY_CONFIRM, POLICY_CRITICAL]:
                    # Create approval request
                    summary = f"Tool: {fn_name}\nPolicy: {policy_level}\nReason: {policy_reason}"
                    req = approval_manager.create_request(
                        session_id=session.id,
                        tool=fn_name,
                        args=args,
                        policy_level=policy_level,
                        summary=summary
                    )

                    if on_approval_needed:
                        on_approval_needed(req.to_dict())

                    # Wait for user approval
                    await req.event.wait()

                    if session.is_cancelled:
                        return "[EMERGENCY STOP] Operation cancelled by user."

                    if req.status != "APPROVED":
                        reject_msg = f"Operation '{fn_name}' rejected by user or expired."
                        session.add_message(role="tool", content=reject_msg, tool_call_id=tc.id)
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": reject_msg})
                        continue

                # 4. Execute tool
                if on_tool_start:
                    on_tool_start(fn_name, args)

                start_time = time.time()
                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn:
                    try:
                        raw_result = await loop.run_in_executor(None, lambda: fn(**args))
                    except Exception as err:
                        raw_result = f"ERROR executing {fn_name}: {str(err)}"
                else:
                    raw_result = f"ERROR: Tool '{fn_name}' not found."

                duration_ms = int((time.time() - start_time) * 1000)
                clean_result = redact_secrets(str(raw_result))

                audit_logger.log_event(
                    event_type="TOOL_EXECUTED",
                    session_id=session.id,
                    tool=fn_name,
                    args=args,
                    policy=policy_level,
                    status="SUCCESS",
                    detail=f"Duration: {duration_ms}ms"
                )

                if on_tool_end:
                    on_tool_end(fn_name, clean_result)

                session.add_message(role="tool", content=clean_result, tool_call_id=tc.id)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": clean_result})

        return "Task completed."

    def chat(self, user_input: str, on_tool_start=None, on_tool_end=None) -> str:
        """Synchronous wrapper for legacy CLI launchers (run.bat)."""
        session = session_manager.get_or_create_session("cli_session")
        try:
            return asyncio.run(
                self.chat_async(
                    session=session,
                    user_input=user_input,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                    on_approval_needed=lambda req: approval_manager.decide(req["id"], "approve")
                )
            )
        except Exception as e:
            return f"Error: {str(e)}"
