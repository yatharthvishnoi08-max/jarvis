"""Build an owner-visible briefing from local tasks and the latest Google sync."""
import re
from datetime import date, datetime, timezone
from itertools import combinations

from tools import planner

REQUEST = re.compile(r"\b(please (?:confirm|approve|review|send|reply)|can you (?:confirm|review|send|approve)|approval (?:requested|required)|rsvp|action required|response requested)\b", re.I)
DEADLINE = re.compile(r"\b(by (?:today|tomorrow|noon|end of day)|due today|deadline|urgent)\b", re.I)


def _instant(value):
    if not value or "T" not in value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.astimezone(timezone.utc) if timestamp.tzinfo else None
    except ValueError:
        return None


def items(snapshot, today=None):
    current_date = (today or date.today()).isoformat()
    rows = []
    for task in planner.open_tasks("today"):
        overdue = task["due"] < current_date
        rows.append({"id":f"task:{task['id']}", "kind":"task", "task_id":task["id"], "title":task["title"],
                     "reason":("Overdue since " if overdue else "Due ") + task["due"], "priority":0 if overdue else 1})
    if snapshot["state"] == "connected":
        for thread in snapshot["inbox"]:
            context = thread["title"] + " " + thread.get("preview", "")
            match = REQUEST.search(context)
            if match:
                rows.append({"id":"mail:"+thread["id"]+":"+thread["version"], "kind":"email", "title":thread["title"],
                             "reason":"Possible request · " + match.group(0), "thread_id":thread["id"],
                             "priority":0 if DEADLINE.search(context) else 2})
        for first, second in combinations(snapshot["events"], 2):
            a,b,c,d = [_instant(value) for value in (first["start"],first.get("end"),second["start"],second.get("end"))]
            if all((a,b,c,d)) and max(a,c) < min(b,d):
                event_ids = sorted((first["id"]+"@"+first["start"],second["id"]+"@"+second["start"]))
                rows.append({"id":"calendar:"+"+".join(event_ids), "kind":"conflict", "title":first["title"]+" / "+second["title"],
                             "reason":"Calendar overlap · " + second["start"], "priority":1})
    hidden=planner.handled_decisions()
    return sorted((item for item in rows if item["id"] not in hidden), key=lambda item:item["priority"])
