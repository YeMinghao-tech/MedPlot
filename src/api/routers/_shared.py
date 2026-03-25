"""Shared session store for API routers."""

from src.agent.memory.working_memory import WorkingMemoryStore

# Shared session store (singleton)
_session_store = WorkingMemoryStore()

# Shared session metadata
_session_metadata = {}


def get_session_store() -> WorkingMemoryStore:
    """Get the shared session store."""
    return _session_store


def get_session_metadata() -> dict:
    """Get the shared session metadata dict."""
    return _session_metadata
