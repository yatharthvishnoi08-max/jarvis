import json
import time
import uuid
import asyncio
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
from tools.system_tools import (
    execute_powershell,
    read_file,
    write_file,
    list_directory,
    get_system_stats,
    get_battery_status,
    get_clipboard,
    set_clipboard,
    control_media,
    manage_application,
    find_files,
)
from tools.multimodal_tools import (
    analyze_image,
    capture_screen,
    analyze_screen,
)
from tools.computer_use_tools import (
    mouse_click,
    mouse_move,
    mouse_scroll,
    mouse_drag,
    keyboard_type,
    keyboard_press,
    keyboard_hotkey,
    get_mouse_position,
    open_windows_settings,
    open_app,
    focus_window,
    click_screen_element,
    configure_laptop_permissions,
    run_elevated_command,
)
from tools.meta_tools import (
    list_employees,
    read_employee_sop,
    update_employee_sop,
    log_learned_rule,
    read_memory,
)
from tools.web_tools import web_search, fetch_web_page
from tools.code_tools import calculator, code_interpreter, apply_unified_patch
from tools.dev_tools import git_status, git_diff, git_log
from tools.doc_tools import read_pdf, get_weather
from agents.deep_research import run_deep_research
from agents.morning_digest import generate_morning_digest
from agents.loop_guard import LoopGuard
from skills.manager import skill_manager
from learning.traces import trace_store, ExecutionTrace, ToolExecutionStep

BASE_DIR = Path(__file__).resolve().parent.parent

# Helper sync wrappers for tools
def _sync_deep_research(topic: str) -> str:
    try:
        return asyncio.run(run_deep_research(topic, max_hops=2))
    except RuntimeError:
        # If already in an event loop in this thread, run via a worker thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(run_deep_research(topic, max_hops=2))).result()

def _get_morning_digest(location: str = "auto") -> str:
    res = generate_morning_digest(location=location)
    return res["markdown"]

def _list_skills() -> str:
    skills = skill_manager.list_skills()
    if not skills:
        return "No skills currently in catalog."
    return "\n".join([f"- **{s['name']}**: {s['description']}" for s in skills])

def _inspect_skill(skill_name: str) -> str:
    skill = skill_manager.get_skill(skill_name)
    if not skill:
        return f"Skill '{skill_name}' not found."
    return f"# Skill: {skill.name}\n\n{skill.content}"

TOOL_FUNCTIONS = {
    # System & Meta
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
    # Web & Research
    "web_search": web_search,
    "fetch_web_page": fetch_web_page,
    "run_deep_research": _sync_deep_research,
    "generate_morning_digest": _get_morning_digest,
    # Code & Math
    "calculator": calculator,
    "code_interpreter": code_interpreter,
    "apply_unified_patch": apply_unified_patch,
    # Git
    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,
    # Docs & Environment
    "read_pdf": read_pdf,
    "get_weather": get_weather,
    # Skills
    "list_skills": _list_skills,
    "inspect_skill": _inspect_skill,
    # Multimodal & Vision
    "analyze_image": analyze_image,
    "capture_screen": capture_screen,
    "analyze_screen": analyze_screen,
    # Host Environment & System Control
    "get_battery_status": get_battery_status,
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
    "control_media": control_media,
    "manage_application": manage_application,
    "find_files": find_files,
    # Computer Use & OS Automation
    "mouse_click": mouse_click,
    "mouse_move": mouse_move,
    "mouse_scroll": mouse_scroll,
    "mouse_drag": mouse_drag,
    "keyboard_type": keyboard_type,
    "keyboard_press": keyboard_press,
    "keyboard_hotkey": keyboard_hotkey,
    "get_mouse_position": get_mouse_position,
    "open_windows_settings": open_windows_settings,
    "open_app": open_app,
    "focus_window": focus_window,
    "click_screen_element": click_screen_element,
    "configure_laptop_permissions": configure_laptop_permissions,
    "run_elevated_command": run_elevated_command,
}

TOOL_SCHEMAS = [
    # 1. execute_powershell
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
    # 2. read_file
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read content from a file on the host filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read."}
                },
                "required": ["path"]
            }
        }
    },
    # 3. write_file
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite content to a file on the host filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Target file path."},
                    "content": {"type": "string", "description": "Full text content to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    # 4. list_directory
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in a directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list (defaults to current dir)."}
                }
            }
        }
    },
    # 5. get_system_stats
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Get current CPU usage, RAM utilization, and free disk space.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 6. list_employees
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "List all active employee subagents and their roles.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 7. read_employee_sop
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
    # 8. update_employee_sop
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
    # 9. log_learned_rule
    {
        "type": "function",
        "function": {
            "name": "log_learned_rule",
            "description": "Store a permanent long-term rule, lesson, or preference across all sessions on disk. Never use this for temporary words or context specific to the current conversation.",
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
    # 10. read_memory
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "Read all recorded rules, system memories, and user preferences.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 11. web_search
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web for real-time information, technical docs, current events, and news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The web search query."},
                    "max_results": {"type": "integer", "description": "Max results to return (1-10)."}
                },
                "required": ["query"]
            }
        }
    },
    # 12. fetch_web_page
    {
        "type": "function",
        "function": {
            "name": "fetch_web_page",
            "description": "Fetch external web page content as clean, readable text. Use to inspect articles, API documentation, and links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full HTTP/HTTPS URL to fetch."}
                },
                "required": ["url"]
            }
        }
    },
    # 13. calculator
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Safely compute mathematical calculations and formulas (supports sqrt, log, sin, cos, powers, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression to evaluate (e.g. 'sqrt(144) + 12')."}
                },
                "required": ["expression"]
            }
        }
    },
    # 14. code_interpreter
    {
        "type": "function",
        "function": {
            "name": "code_interpreter",
            "description": "Execute Python code in an isolated environment with AST safety validation. Returns stdout and stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The Python code snippet to run."}
                },
                "required": ["code"]
            }
        }
    },
    # 15. apply_unified_patch
    {
        "type": "function",
        "function": {
            "name": "apply_unified_patch",
            "description": "Apply a unified diff patch string cleanly to a target file on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch_text": {"type": "string", "description": "Unified diff patch text."}
                },
                "required": ["patch_text"]
            }
        }
    },
    # 16. git_status
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Inspect the current git working tree status and branch.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 17. git_diff
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "View unstaged or staged git diff changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "staged": {"type": "boolean", "description": "Whether to view staged changes."},
                    "file_path": {"type": "string", "description": "Specific file to diff."}
                }
            }
        }
    },
    # 18. git_log
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "View recent git commit history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of commits to return (default 5)."}
                }
            }
        }
    },
    # 19. read_pdf
    {
        "type": "function",
        "function": {
            "name": "read_pdf",
            "description": "Read and extract text from a local PDF document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the PDF file."},
                    "max_pages": {"type": "integer", "description": "Maximum pages to extract."}
                },
                "required": ["file_path"]
            }
        }
    },
    # 20. get_weather
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Look up current weather conditions and forecast for any city or location worldwide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location (e.g. 'London', 'Tokyo', 'San Francisco')."},
                    "units": {"type": "string", "description": "'metric' (Celsius) or 'imperial' (Fahrenheit)."}
                },
                "required": ["location"]
            }
        }
    },
    # 21. run_deep_research
    {
        "type": "function",
        "function": {
            "name": "run_deep_research",
            "description": "Execute an autonomous multi-hop web investigation synthesizing a cited research report on any complex topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The research subject or question."}
                },
                "required": ["topic"]
            }
        }
    },
    # 22. generate_morning_digest
    {
        "type": "function",
        "function": {
            "name": "generate_morning_digest",
            "description": "Synthesize a comprehensive daily executive morning briefing including system health, weather, and world intelligence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location for weather report (optional)."}
                }
            }
        }
    },
    # 23. list_skills
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all expert on-demand skills available in the catalog.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 24. inspect_skill
    {
        "type": "function",
        "function": {
            "name": "inspect_skill",
            "description": "Read the detailed instructions, guidelines, and methodology of an expert skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill to inspect."}
                },
                "required": ["skill_name"]
            }
        }
    },
    # 25. analyze_image
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze any local image file (PNG, JPG, WebP) using Gemini Vision to read text, describe diagrams, inspect charts, or debug screenshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Absolute or relative path to the image file on disk."},
                    "prompt": {"type": "string", "description": "Specific question or analysis prompt for Gemini Vision (optional)."}
                },
                "required": ["image_path"]
            }
        }
    },
    # 26. capture_screen
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Capture a screenshot of the primary computer display and save it to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "save_path": {"type": "string", "description": "Optional custom file path to save the screenshot."}
                }
            }
        }
    },
    # 27. analyze_screen
    {
        "type": "function",
        "function": {
            "name": "analyze_screen",
            "description": "Capture the user's active screen and analyze it with Gemini Vision to see what is on screen, debug UI errors, and provide visual assistance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Question or focus area for visual analysis (optional)."}
                }
            }
        }
    },
    # 28. get_battery_status
    {
        "type": "function",
        "function": {
            "name": "get_battery_status",
            "description": "Returns current host battery percentage, AC power plug status, and estimated remaining runtime.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 29. get_clipboard
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Reads and returns the current text stored in the Windows clipboard.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 30. set_clipboard
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "Copies text directly into the Windows clipboard for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text content to copy to the clipboard."}
                },
                "required": ["text"]
            }
        }
    },
    # 31. control_media
    {
        "type": "function",
        "function": {
            "name": "control_media",
            "description": "Control host media playback and master volume (volume_up, volume_down, mute, unmute, play_pause, next_track, prev_track).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_up", "volume_down", "mute", "unmute", "play_pause", "next_track", "prev_track"],
                        "description": "Media action to execute."
                    }
                },
                "required": ["action"]
            }
        }
    },
    # 32. manage_application
    {
        "type": "function",
        "function": {
            "name": "manage_application",
            "description": "Launch, list, or close Windows desktop applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["launch", "close", "list"],
                        "description": "Action: 'launch' to start an app, 'close' to terminate, 'list' to view active apps."
                    },
                    "name": {
                        "type": "string",
                        "description": "Name or executable of the application (e.g. 'notepad', 'calc', 'code', 'chrome'). Required for 'launch' and 'close'."
                    }
                },
                "required": ["action"]
            }
        }
    },
    # 33. find_files
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Search for files by pattern or substring across directories, ignoring build artifacts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern or filename (e.g. '*.ico', 'budget', '*.py')."},
                    "search_path": {"type": "string", "description": "Root path to search from (default is project root '.')."},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return (default 15)."}
                },
                "required": ["pattern"]
            }
        }
    },
    # 34. mouse_click
    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description": "Click the mouse at specified screen (x, y) coordinates or at current position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate in pixels (optional)."},
                    "y": {"type": "integer", "description": "Y coordinate in pixels (optional)."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button (default 'left')."},
                    "clicks": {"type": "integer", "enum": [1, 2], "description": "1 for single click, 2 for double click (default 1)."}
                }
            }
        }
    },
    # 35. mouse_move
    {
        "type": "function",
        "function": {
            "name": "mouse_move",
            "description": "Smoothly move the mouse cursor to (x, y) coordinates on the screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate in pixels."},
                    "y": {"type": "integer", "description": "Y coordinate in pixels."},
                    "duration": {"type": "number", "description": "Movement duration in seconds (default 0.2)."}
                },
                "required": ["x", "y"]
            }
        }
    },
    # 36. mouse_scroll
    {
        "type": "function",
        "function": {
            "name": "mouse_scroll",
            "description": "Scroll the mouse wheel up (positive integer) or down (negative integer).",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer", "description": "Scroll amount (e.g. 5 for up, -5 for down)."}
                },
                "required": ["clicks"]
            }
        }
    },
    # 37. mouse_drag
    {
        "type": "function",
        "function": {
            "name": "mouse_drag",
            "description": "Click and drag the mouse from (start_x, start_y) to (end_x, end_y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Starting X coordinate."},
                    "start_y": {"type": "integer", "description": "Starting Y coordinate."},
                    "end_x": {"type": "integer", "description": "Ending X coordinate."},
                    "end_y": {"type": "integer", "description": "Ending Y coordinate."},
                    "duration": {"type": "number", "description": "Drag duration in seconds (default 0.5)."}
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        }
    },
    # 38. keyboard_type
    {
        "type": "function",
        "function": {
            "name": "keyboard_type",
            "description": "Type text into the currently active or focused input field or window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The exact string to type."},
                    "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing (default false)."}
                },
                "required": ["text"]
            }
        }
    },
    # 39. keyboard_press
    {
        "type": "function",
        "function": {
            "name": "keyboard_press",
            "description": "Press a single keyboard key (enter, esc, tab, space, backspace, win, f5, delete, up, down, left, right).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name to press."}
                },
                "required": ["key"]
            }
        }
    },
    # 40. keyboard_hotkey
    {
        "type": "function",
        "function": {
            "name": "keyboard_hotkey",
            "description": "Press a keyboard shortcut combination (e.g. ['win', 'i'] for Settings, ['ctrl', 'c'] for copy, ['alt', 'tab']).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key names (e.g. ['win', 'i'], ['ctrl', 'v'], ['alt', 'f4'])."
                    }
                },
                "required": ["keys"]
            }
        }
    },
    # 41. get_mouse_position
    {
        "type": "function",
        "function": {
            "name": "get_mouse_position",
            "description": "Get current mouse cursor coordinates and display resolution.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # 42. open_windows_settings
    {
        "type": "function",
        "function": {
            "name": "open_windows_settings",
            "description": "Directly open Windows Settings to a specific page ('microphone', 'camera', 'apps', 'startup', 'security', 'sound', 'display', 'network', 'bluetooth', 'power', 'updates', 'home').",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "string", "description": "Settings page name (e.g. 'microphone', 'apps', 'security', 'sound', 'home')."}
                }
            }
        }
    },
    # 43. open_app
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open or launch any application by name or executable (e.g. 'notepad', 'calc', 'chrome', 'msedge', 'code', 'explorer', 'settings').",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Name or executable of the application or document."}
                },
                "required": ["target"]
            }
        }
    },
    # 44. focus_window
    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring an application window to the foreground by matching its title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_keyword": {"type": "string", "description": "Partial or full title of the window to activate."}
                },
                "required": ["title_keyword"]
            }
        }
    },
    # 45. click_screen_element
    {
        "type": "function",
        "function": {
            "name": "click_screen_element",
            "description": "Visual Grounding: Look at the live screen using Gemini Vision, locate the target element (button, icon, menu, toggle), and click it automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_description": {"type": "string", "description": "Description of the element to click (e.g. 'Microphone toggle switch', 'Close icon', 'Start button')."},
                    "clicks": {"type": "integer", "enum": [1, 2], "description": "Single or double click (default 1)."},
                    "button": {"type": "string", "enum": ["left", "right"], "description": "Mouse button (default 'left')."}
                },
                "required": ["target_description"]
            }
        }
    },
    # 46. configure_laptop_permissions
    {
        "type": "function",
        "function": {
            "name": "configure_laptop_permissions",
            "description": "Directly configure Windows laptop permissions (Microphone privacy consent for desktop apps, PowerShell RemoteSigned, and Firewall).",
            "parameters": {
                "type": "object",
                "properties": {
                    "permission_type": {"type": "string", "description": "'all' or specific permission (optional)."}
                }
            }
        }
    },
    # 47. run_elevated_command
    {
        "type": "function",
        "function": {
            "name": "run_elevated_command",
            "description": "Execute an administrative command via Windows UAC elevation (RunAs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The administrative command to execute."}
                },
                "required": ["command"]
            }
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
        skills_info = _list_skills()

        return (
            f"{base_prompt}\n\n"
            f"## Available Expert Skills Catalog:\n{skills_info}\n\n"
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
        - LoopGuard protection against infinite/repetitive tool cycles
        - TraceStore recording for continuous learning
        - Per-session message isolation
        - Strict tool policy checks (READ, CONFIRM, CRITICAL, BLOCKED)
        - Asynchronous user approval gates
        - Audit trail logging
        """
        session.reset_cancellation()
        session.add_message(role="user", content=user_input)

        loop_guard = LoopGuard()
        trace_steps: List[ToolExecutionStep] = []
        recorded_thoughts: List[str] = []
        turn_start_time = time.time()

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

                # Record execution trace for learning
                total_duration = round(time.time() - turn_start_time, 3)
                trace = ExecutionTrace(
                    trace_id=f"tr_{uuid.uuid4().hex[:12]}",
                    session_id=session.id,
                    user_query=user_input,
                    response_text=final_content,
                    timestamp=time.time(),
                    duration_seconds=total_duration,
                    model_name=self.model_name,
                    thoughts=recorded_thoughts,
                    steps=trace_steps
                )
                trace_store.record_trace(trace)

                return final_content

            # Format tool calls (preserving provider-specific fields like Google thought signatures)
            formatted_tool_calls = []
            for tc in message.tool_calls:
                tc_dict = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                if hasattr(tc, "extra_content") and tc.extra_content:
                    tc_dict["extra_content"] = tc.extra_content
                elif hasattr(tc, "model_dump"):
                    dumped = tc.model_dump(exclude_unset=True)
                    if "extra_content" in dumped:
                        tc_dict["extra_content"] = dumped["extra_content"]
                formatted_tool_calls.append(tc_dict)

            assistant_content = redact_secrets(message.content or "")
            if assistant_content:
                recorded_thoughts.append(assistant_content)
                if on_thought:
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

                # 1. LoopGuard check
                verdict = loop_guard.check(fn_name, args)
                if verdict.blocked:
                    blocked_msg = f"LOOP GUARD BLOCKED: {verdict.reason}"
                    session.add_message(role="tool", content=blocked_msg, tool_call_id=tc.id)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": blocked_msg})
                    continue

                # 2. Evaluate tool policy
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

                # 3. Check BLOCKED
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

                # 4. Check CONFIRM or CRITICAL (requires approval)
                if policy_level in [POLICY_CONFIRM, POLICY_CRITICAL]:
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

                # 5. Execute tool
                if on_tool_start:
                    on_tool_start(fn_name, args)

                start_time = time.time()
                fn = TOOL_FUNCTIONS.get(fn_name)
                step_error = None
                if fn:
                    try:
                        raw_result = await loop.run_in_executor(None, lambda: fn(**args))
                    except Exception as err:
                        raw_result = f"ERROR executing {fn_name}: {str(err)}"
                        step_error = str(err)
                else:
                    raw_result = f"ERROR: Tool '{fn_name}' not found."
                    step_error = "Tool not found"

                step_duration = round(time.time() - start_time, 3)
                clean_result = redact_secrets(str(raw_result))

                trace_steps.append(ToolExecutionStep(
                    tool_name=fn_name,
                    args=args,
                    result=clean_result[:500],
                    duration_seconds=step_duration,
                    error=step_error
                ))

                audit_logger.log_event(
                    event_type="TOOL_EXECUTED",
                    session_id=session.id,
                    tool=fn_name,
                    args=args,
                    policy=policy_level,
                    status="SUCCESS" if not step_error else "ERROR",
                    duration_ms=int(step_duration * 1000)
                )

                if on_tool_end:
                    on_tool_end(fn_name, clean_result)

                session.add_message(role="tool", content=clean_result, tool_call_id=tc.id)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": clean_result})

        fallback_msg = "Task reached maximum reasoning iterations."
        session.add_message(role="assistant", content=fallback_msg)
        return fallback_msg

    def chat(self, user_input: str, session_id: str = "terminal") -> str:
        """
        Synchronous chat wrapper for terminal execution, interactive CLI, and scripts.
        Manages the event loop safely and handles terminal approval prompts if tools require CONFIRM/CRITICAL.
        """
        session = session_manager.get_or_create_session(session_id)

        def terminal_approval(req_dict: Dict[str, Any]):
            try:
                import sys
                from rich.prompt import Confirm
                from rich.console import Console
                c = Console()
                tool = req_dict.get("tool", "")
                level = req_dict.get("policy_level", "")
                args = req_dict.get("args", {})
                c.print(f"\n[bold yellow]⚠️ APPROVAL REQUIRED ({level})[/bold yellow]")
                c.print(f"[bold cyan]Tool:[/bold cyan] {tool}")
                c.print(f"[bold cyan]Arguments:[/bold cyan] {args}")
                if sys.stdin.isatty():
                    approved = Confirm.ask(f"Authorize JARVIS to execute '{tool}'?", default=False)
                    approval_manager.decide(req_dict["id"], "approve" if approved else "reject")
                else:
                    approval_manager.decide(req_dict["id"], "approve")
            except Exception:
                approval_manager.decide(req_dict.get("id", ""), "reject")

        async def _run():
            return await self.chat_async(
                session=session,
                user_input=user_input,
                on_approval_needed=terminal_approval
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    return ex.submit(lambda: asyncio.run(_run())).result()
            else:
                return loop.run_until_complete(_run())
        except RuntimeError:
            return asyncio.run(_run())

