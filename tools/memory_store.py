"""Owner-editable memories with revisions; legacy Markdown is preserved on import."""
import json
import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATABASE = Path(__file__).resolve().parents[1] / "memory" / "memories.sqlite3"
LEGACY_FILE = DATABASE.parent / "learned_rules.md"


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _store():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY, category TEXT NOT NULL, rule TEXT NOT NULL,
            source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            expires_at TEXT, archived INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
            pinned INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS revisions (
            memory_id INTEGER NOT NULL, version INTEGER NOT NULL, snapshot TEXT NOT NULL,
            PRIMARY KEY(memory_id, version)
        )""")
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY)")
        db.execute("BEGIN IMMEDIATE")
        if 'pinned' not in {row['name'] for row in db.execute('PRAGMA table_info(memories)')}:
            db.execute('ALTER TABLE memories ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0')
        if not db.execute("SELECT 1 FROM metadata WHERE key='legacy_imported'").fetchone():
            if LEGACY_FILE.exists():
                for line in LEGACY_FILE.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = re.match(r"^- \*\*\[([^\]]+)\]\*\* \([^)]+\): (.*)$", line)
                    category, rule = match.groups() if match else ("LEGACY", line)
                    stamp = _now()
                    db.execute("""INSERT INTO memories(category, rule, source, created_at, updated_at)
                        VALUES (?, ?, 'Imported from learned_rules.md', ?, ?)""", (category, rule, stamp, stamp))
            db.execute("INSERT INTO metadata VALUES ('legacy_imported')")
        yield db


def _validate(category: str, rule: str, expires_at: Optional[str]):
    category, rule = category.strip().upper(), rule.strip()
    if not 1 <= len(category) <= 40 or not 1 <= len(rule) <= 4000:
        raise ValueError("Use a category of 1–40 characters and a memory of 1–4000 characters.")
    if expires_at:
        stamp = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError("Expiry must include a timezone.")
        expires_at = stamp.astimezone(timezone.utc).isoformat()
    return category, rule, expires_at or None


def list_memories(include_inactive=False):
    with _store() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM memories ORDER BY id DESC")]
    for row in rows:
        row['expired'] = bool(row['expires_at'] and row['expires_at'] <= _now())
    return rows if include_inactive else [r for r in rows if not r['archived'] and not r['expired']]


def add_memory(category: str, rule: str, source='Owner in Memory', expires_at=None, pinned=False):
    category, rule, expires_at = _validate(category, rule, expires_at)
    with _store() as db:
        # Repeated clicks/model retries should not create duplicate active preferences.
        prior = db.execute("""SELECT * FROM memories WHERE category=? AND rule=? AND archived=0
            AND expires_at IS ? AND pinned=?""", (category, rule, expires_at, int(pinned))).fetchone()
        if prior:
            return dict(prior)
        stamp = _now()
        cursor = db.execute("""INSERT INTO memories(category, rule, source, created_at, updated_at, expires_at, pinned)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (category, rule, source, stamp, stamp, expires_at, int(pinned)))
        return dict(db.execute("SELECT * FROM memories WHERE id=?", (cursor.lastrowid,)).fetchone())


def change_memory(memory_id: int, version: int, *, action='edit', category=None, rule=None, expires_at=None, pinned=None):
    with _store() as db:
        found = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not found:
            raise KeyError("Memory not found.")
        old = dict(found)
        if old['version'] != version:
            raise RuntimeError("This memory changed elsewhere. Reload before editing it.")
        new = dict(old)
        if action == 'edit':
            new['category'], new['rule'], new['expires_at'] = _validate(category, rule, expires_at)
            if pinned is not None:
                new['pinned'] = int(pinned)
        elif action == 'archive':
            new['archived'] = 1
        elif action == 'restore':
            new['archived'] = 0
        elif action == 'undo':
            previous = db.execute("SELECT snapshot FROM revisions WHERE memory_id=? ORDER BY version DESC LIMIT 1", (memory_id,)).fetchone()
            if not previous:
                raise ValueError("There is no previous change to undo.")
            new = json.loads(previous['snapshot'])
        else:
            raise ValueError("Unknown memory action.")
        db.execute("INSERT INTO revisions VALUES (?, ?, ?)", (memory_id, old['version'], json.dumps(old)))
        db.execute("""UPDATE memories SET category=?, rule=?, expires_at=?, archived=?, pinned=?, updated_at=?, version=version+1
            WHERE id=?""", (new['category'], new['rule'], new['expires_at'], new['archived'], new.get('pinned', 0), _now(), memory_id))
        return dict(db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone())


def memory_text():
    return '\n'.join(f"- **[{r['category']}]** (#{r['id']}): {r['rule']}" for r in list_memories()) or '(No active memories.)'
