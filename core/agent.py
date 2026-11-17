import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from core.client import get_client
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

console = Console()
BASE_DIR = Path(__file__).resolve().parent.parent

# Tool mapping registry
TOOL_FUNCTIONS = {
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
                    "employee_name": {"type": "string", "description": "Name of the employee (e.g. 'os_operator', 'coder', 'reviewer')."}
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
        self.system_prompt = self._build_system_prompt()
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _build_system_prompt(self) -> str:
        prompt_file = BASE_DIR / "agents" / "central_brain.md"
        base_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "You are JARVIS."
        
        # Inject employee summary and memory dynamically
        employees_info = list_employees()
        memory_info = read_memory()
        
        full_prompt = (
            f"{base_prompt}\n\n"
            f"## Current Team Roster:\n{employees_info}\n\n"
            f"## Persistent System Memory:\n{memory_info}\n"
        )
        return full_prompt

    def chat(self, user_input: str, on_tool_start=None, on_tool_end=None) -> str:
        """Processes a user input through the Hermes ReAct loop."""
        self.messages.append({"role": "user", "content": user_input})
        
        max_turns = 8
        for turn in range(max_turns):
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            # If the model has text response, save it to history
            if message.content:
                self.messages.append({"role": "assistant", "content": message.content})
            
            # If no tool calls, we're done
            if not message.tool_calls:
                return message.content or ""
            
            # If tool calls are requested
            self.messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
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
            })
            
            # Execute each tool call
            for tc in message.tool_calls:
                fn_name = tc.function.name
                fn = TOOL_FUNCTIONS.get(fn_name)
                
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                
                console.print(f"[bold cyan]⚡ Tool Execution:[/bold cyan] [yellow]{fn_name}[/yellow] with args: {args}")
                if on_tool_start:
                    try:
                        on_tool_start(fn_name, args)
                    except Exception:
                        pass
                
                if fn:
                    try:
                        result = fn(**args)
                    except Exception as err:
                        result = f"ERROR executing {fn_name}: {str(err)}"
                else:
                    result = f"ERROR: Tool '{fn_name}' not found."
                
                console.print(f"[dim]Output: {str(result)[:150]}...[/dim]")
                if on_tool_end:
                    try:
                        on_tool_end(fn_name, result)
                    except Exception:
                        pass
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })

        return "I have completed the operations as requested."
