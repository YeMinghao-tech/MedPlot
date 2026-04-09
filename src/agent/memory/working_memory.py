"""Working memory for short-term conversation context."""

import json
import sqlite3
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class ConversationTurn:
    """A single conversation turn."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""


@dataclass
class WorkingMemory:
    """Short-term working memory for current session.

    Maintains:
    - symptom_tree: structured symptom information
    - message_history: conversation history
    - current_state: current dialog state
    """

    session_id: str
    patient_id: Optional[str] = None
    symptom_tree: Dict[str, Any] = field(default_factory=dict)
    message_history: List[ConversationTurn] = field(default_factory=list)
    current_intent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, content: str):
        """Add a conversation turn."""
        turn = ConversationTurn(role=role, content=content, timestamp=datetime.now().isoformat())
        self.message_history.append(turn)

    def get_recent_messages(self, n: int = 5) -> List[ConversationTurn]:
        """Get N most recent messages."""
        return self.message_history[-n:]

    def get_conversation_text(self) -> str:
        """Get full conversation as text."""
        lines = []
        for turn in self.message_history:
            role_label = "用户" if turn.role == "user" else "助手"
            lines.append(f"{role_label}：{turn.content}")
        return "\n".join(lines)

    def clear(self):
        """Clear the working memory."""
        self.message_history = []
        self.symptom_tree = {}
        self.context = {}

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "symptom_tree": self.symptom_tree,
            "message_history": [asdict(t) for t in self.message_history],
            "current_intent": self.current_intent,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        """Create from dictionary."""
        message_history = [
            ConversationTurn(**t) for t in data.get("message_history", [])
        ]
        return cls(
            session_id=data["session_id"],
            patient_id=data.get("patient_id"),
            symptom_tree=data.get("symptom_tree", {}),
            message_history=message_history,
            current_intent=data.get("current_intent"),
            context=data.get("context", {}),
        )


class WorkingMemoryStore:
    """Store for working memories with SQLite persistence."""

    def __init__(self, db_path: str = "./data/db/working_memory.db"):
        """Initialize the store with SQLite persistence.

        Args:
            db_path: Path to SQLite database file.
        """
        self._memories: Dict[str, WorkingMemory] = {}
        self._lock = threading.Lock()
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS working_memories (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON working_memories(updated_at)")
        conn.close()

    def _save_to_db(self, memory: WorkingMemory):
        """Save memory to database."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO working_memories (session_id, data, updated_at) VALUES (?, ?, ?)",
            (memory.session_id, json.dumps(memory.to_dict()), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _load_from_db(self, session_id: str) -> Optional[WorkingMemory]:
        """Load memory from database."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT data FROM working_memories WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return WorkingMemory.from_dict(json.loads(row[0]))
        return None

    def get(self, session_id: str) -> WorkingMemory:
        """Get or create working memory for session."""
        with self._lock:
            if session_id not in self._memories:
                # Try to load from database first
                memory = self._load_from_db(session_id)
                if memory:
                    self._memories[session_id] = memory
                else:
                    self._memories[session_id] = WorkingMemory(session_id=session_id)
            return self._memories[session_id]

    def save(self, session_id: str):
        """Persist session to database."""
        with self._lock:
            if session_id in self._memories:
                self._save_to_db(self._memories[session_id])

    def delete(self, session_id: str):
        """Delete working memory for session."""
        with self._lock:
            if session_id in self._memories:
                del self._memories[session_id]
            # Also delete from database
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM working_memories WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()

    def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        with self._lock:
            if session_id in self._memories:
                return True
            # Check database
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT 1 FROM working_memories WHERE session_id = ?",
                (session_id,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours from database.

        Note: Does not remove from in-memory cache.
        """
        import time
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM working_memories WHERE updated_at < ?", (cutoff_iso,))
        conn.commit()
        conn.close()
