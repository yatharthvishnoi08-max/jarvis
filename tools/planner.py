"""Personal commitments shared by the owner's conversations on this gateway."""
import sqlite3
from contextlib import closing, contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional


DATABASE = Path(__file__).resolve().parents[1] / "memory" / "planner.sqlite3"


@contextmanager
def _store():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, due TEXT, done INTEGER NOT NULL DEFAULT 0
        )""")
        yield db


def _date(value: str) -> str:
    if value == "today":
        return date.today().isoformat()
    if value == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()
    return date.fromisoformat(value).isoformat()


def add_task(title: str, due: Optional[str] = None) -> str:
    title = title.strip()
    if not 1 <= len(title) <= 300:
        raise ValueError("Use a task title between 1 and 300 characters.")
    when = _date(due) if due is not None else None
    with _store() as db:
        # Serialize the duplicate check and insert when two devices submit together.
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT id FROM tasks WHERE done=0 AND title=? COLLATE NOCASE AND due IS ?",
            (title, when),
        ).fetchone()
        if existing:
            return f"Already on your list as #{existing[0]}: {title}"
        task = db.execute("INSERT INTO tasks(title, due) VALUES (?, ?)", (title, when))
        return f"Added #{task.lastrowid}: {title} ({when or 'no due date'})."


def open_tasks(view: str = "all") -> list[dict]:
    if view not in ("today", "all"):
        raise ValueError("Choose today or all.")
    today = date.today().isoformat()
    query = "SELECT id, title, due FROM tasks WHERE done=0"
    params = ()
    if view == "today":
        query += " AND due <= ?"
        params = (today,)
    with _store() as db:
        rows = db.execute(query + " ORDER BY due IS NULL, due, id", params).fetchall()
    return [dict(id=number, title=title, due=due) for number, title, due in rows]


def list_tasks(view: str = "today") -> str:
    today = date.today().isoformat()
    rows = open_tasks(view)
    if not rows:
        return "No overdue tasks or tasks due today." if view == "today" else "No open tasks."
    lines = []
    for task in rows:
        number, title, due = task["id"], task["title"], task["due"]
        label = due or "no due date"
        if due and due < today:
            label = f"overdue since {due}"
        lines.append(f"#{number} {title} ({label})")
    return "\n".join(lines)


def complete_task(task_id: int) -> str:
    with _store() as db:
        row = db.execute("SELECT title, done FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            return f"No task with ID #{task_id}."
        if row[1]:
            return f"Already completed #{task_id}: {row[0]}"
        db.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
        return f"Completed #{task_id}: {row[0]}"


def handled_decisions() -> set:
    with _store() as db:
        db.execute("CREATE TABLE IF NOT EXISTS handled (decision_id TEXT PRIMARY KEY)")
        return {row[0] for row in db.execute("SELECT decision_id FROM handled")}


def handle_decision(decision_id: str):
    with _store() as db:
        db.execute("CREATE TABLE IF NOT EXISTS handled (decision_id TEXT PRIMARY KEY)")
        db.execute("INSERT OR IGNORE INTO handled VALUES (?)", (decision_id,))
