"""Working memory for short-term conversation context."""

from dataclasses import dataclass, field
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
        turn = ConversationTurn(role=role, content=content)
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


class WorkingMemoryStore:
    """Store for working memories (in-memory for current session)."""

    def __init__(self):
        """Initialize the store."""
        self._memories: Dict[str, WorkingMemory] = {}

    def get(self, session_id: str) -> WorkingMemory:
        """Get or create working memory for session."""
        if session_id not in self._memories:
            self._memories[session_id] = WorkingMemory(session_id=session_id)
        return self._memories[session_id]

    def delete(self, session_id: str):
        """Delete working memory for session."""
        if session_id in self._memories:
            del self._memories[session_id]

    def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self._memories
