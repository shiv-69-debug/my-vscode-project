"""Session management for storing interview history."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from config import config


class SessionManager:
    """File-based session storage for interview history."""

    def __init__(self) -> None:
        os.makedirs(config.session_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        return os.path.join(config.session_dir, f"{session_id}.json")

    def create(self) -> str:
        session_id = uuid.uuid4().hex[:12]
        data = {
            "id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "history": [],
        }
        with open(self._path(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return session_id

    def load(self, session_id: str) -> Optional[dict]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, session_id: str, data: dict) -> None:
        with open(self._path(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_entry(self, session_id: str, entry: dict) -> dict:
        data = self.load(session_id)
        if data is None:
            raise ValueError(f"Session {session_id} not found")
        data["history"].append(entry)
        if len(data["history"]) > config.max_history:
            data["history"] = data["history"][-config.max_history:]
        self.save(session_id, data)
        return data

    def get_history(self, session_id: str) -> list:
        data = self.load(session_id)
        if data is None:
            return []
        return data["history"]

    def list_sessions(self) -> list:
        sessions = []
        for fname in os.listdir(config.session_dir):
            if fname.endswith(".json"):
                sid = fname[:-5]
                data = self.load(sid)
                if data:
                    sessions.append({
                        "id": sid,
                        "created_at": data.get("created_at", ""),
                        "count": len(data.get("history", [])),
                    })
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)


session_manager = SessionManager()
