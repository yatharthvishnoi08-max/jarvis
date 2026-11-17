from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
EMPLOYEES_DIR = BASE_DIR / "agents" / "employees"
MEMORY_FILE = BASE_DIR / "memory" / "learned_rules.md"

def list_employees() -> str:
    """Lists all employee agents currently registered in the system."""
    try:
        employees = []
        for file in sorted(EMPLOYEES_DIR.glob("*.md")):
            first_line = file.read_text(encoding="utf-8").splitlines()[0] if file.stat().st_size > 0 else "(Empty)"
            employees.append(f"- **{file.stem}**: {first_line}")
        return "\n".join(employees) if employees else "No employees registered."
    except Exception as e:
        return f"ERROR listing employees: {str(e)}"

def read_employee_sop(employee_name: str) -> str:
    """Reads the current Standard Operating Procedure (SOP) / system prompt of an employee."""
    try:
        file = EMPLOYEES_DIR / f"{employee_name.lower().strip()}.md"
        if not file.exists():
            return f"ERROR: Employee '{employee_name}' does not exist."
        return file.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading employee SOP: {str(e)}"

def update_employee_sop(employee_name: str, feedback_or_new_rule: str) -> str:
    """Permanently appends or updates an employee agent's SOP based on user feedback or self-reflection."""
    try:
        file = EMPLOYEES_DIR / f"{employee_name.lower().strip()}.md"
        if not file.exists():
            return f"ERROR: Employee '{employee_name}' not found in {EMPLOYEES_DIR}."
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        update_entry = (
            f"\n\n### Updated Guideline ({timestamp})\n"
            f"- **Rule/Correction**: {feedback_or_new_rule}\n"
        )
        with open(file, "a", encoding="utf-8") as f:
            f.write(update_entry)
            
        return f"SUCCESS: Permanently updated SOP for '{employee_name}' with new guideline."
    except Exception as e:
        return f"ERROR updating employee SOP: {str(e)}"

def log_learned_rule(category: str, rule: str) -> str:
    """Logs a system-wide lesson, user preference, or operational rule into persistent memory."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n- **[{category.upper()}]** ({timestamp}): {rule}\n"
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"SUCCESS: Logged rule under category '{category}' into persistent memory."
    except Exception as e:
        return f"ERROR logging rule: {str(e)}"

def read_memory() -> str:
    """Reads all learned rules, user preferences, and operational memories."""
    try:
        if not MEMORY_FILE.exists():
            return "(Memory file does not exist yet.)"
        return MEMORY_FILE.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading memory: {str(e)}"
