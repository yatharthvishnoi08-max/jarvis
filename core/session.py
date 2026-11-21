import asyncio
import os
import tempfile
import re
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.auth import redact_secrets

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "memory" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

class Session:
    def __init__(self, session_id: Optional[str] = None, title: str = "New Session"):
        self.id = session_id or str(uuid.uuid4())[:8]
        self.title = title
        self.created_at = int(time.time())
        self.updated_at = self.created_at
        self.messages: List[Dict[str, Any]] = []
        self._is_cancelled = False
        self._turn_lock = None

    @property
    def turn_lock(self) -> asyncio.Lock:
        if self._turn_lock is None:
            self._turn_lock = asyncio.Lock()
        return self._turn_lock

    def cancel(self):
        self._is_cancelled = True

    def reset_cancellation(self):
        self._is_cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        audio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        msg = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "role": role,
            "content": redact_secrets(content),
            "timestamp": int(time.time()),
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "audio_id": audio_id
        }
        self.messages.append(msg)
        self.updated_at = int(time.time())
        
        # Auto-update title if it's the first user message
        if role == "user" and (self.title == "New Session" or not self.title):
            clean_title = content.strip().split("\n")[0][:36]
            if clean_title:
                self.title = clean_title

        self.save()
        return msg

    def save(self):
        file_path = SESSIONS_DIR / f"{self.id}.json"
        data = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SESSIONS_DIR,
                                             suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                json.dump(data, output, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, file_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, session_id: str) -> Optional['Session']:
        file_path = SESSIONS_DIR / f"{session_id}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            session = cls(session_id=data["id"], title=data.get("title", "Session"))
            session.created_at = data.get("created_at", int(time.time()))
            session.updated_at = data.get("updated_at", session.created_at)
            session.messages = data.get("messages", [])
            return session
        except Exception as e:
            print(f"[Session Load Error]: {e}")
            return None


class SessionManager:
    def __init__(self):
        self._active_sessions: Dict[str, Session] = {}

    @staticmethod
    def valid_id(session_id: str) -> bool:
        return isinstance(session_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id) is not None

    def get_session(self, session_id: str) -> Optional[Session]:
        if not self.valid_id(session_id):
            return None
        if session_id not in self._active_sessions:
            loaded = Session.load(session_id)
            if loaded is None:
                return None
            self._active_sessions[session_id] = loaded
        return self._active_sessions[session_id]

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if session_id:
            if not self.valid_id(session_id):
                raise ValueError("Invalid conversation ID")
            loaded = self.get_session(session_id)
            if loaded:
                return loaded

        # Create new
        new_session = Session(session_id)
        new_session.save()
        self._active_sessions[new_session.id] = new_session
        return new_session

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions_meta = []
        for file in sorted(SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                sessions_meta.append({
                    "id": data["id"],
                    "title": data.get("title", "Session"),
                    "created_at": data.get("created_at", int(file.stat().st_ctime)),
                    "updated_at": data.get("updated_at", int(file.stat().st_mtime)),
                    "message_count": len(data.get("messages", []))
                })
            except Exception:
                continue
        return sessions_meta

    def delete_session(self, session_id: str) -> bool:
        if not self.valid_id(session_id):
            return False
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        file_path = SESSIONS_DIR / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

session_manager = SessionManager()
