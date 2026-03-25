"""In-memory Working Memory implementation."""

import threading
from typing import Any, Dict, Optional

from src.libs.memory.base_memory import BaseWorkingMemory


class InMemoryWorkingMemory(BaseWorkingMemory):
    """Thread-safe in-memory implementation of Working Memory."""

    def __init__(self):
        """Initialize in-memory working memory."""
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get working memory state for a session."""
        with self._lock:
            return self._store.get(session_id)

    def set(self, session_id: str, state: Dict[str, Any]) -> None:
        """Set working memory state for a session."""
        with self._lock:
            self._store[session_id] = state

    def delete(self, session_id: str) -> None:
        """Delete working memory for a session."""
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]

    def clear(self) -> None:
        """Clear all working memory."""
        with self._lock:
            self._store.clear()
