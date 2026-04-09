"""Session management routes."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from src.api.routers._shared import get_session_store, get_session_metadata


# Get shared instances
_session_store = get_session_store()
_session_metadata = get_session_metadata()


def _create_session_metadata(session_id: str, patient_id: Optional[str] = None) -> dict:
    """Create session metadata."""
    now = datetime.now()
    return {
        "session_id": session_id,
        "patient_id": patient_id,
        "created_at": now.isoformat(),
        "last_activity": now.isoformat(),
        "status": "active",
    }


router = APIRouter(tags=["sessions"])


@router.post("", status_code=201)
async def create_session(patient_id: Optional[str] = None) -> dict:
    """Create a new session.

    Args:
        patient_id: Optional patient identifier.

    Returns:
        Session info with session_id.
    """
    session_id = str(uuid.uuid4())

    # Create working memory
    memory = _session_store.get(session_id)
    memory.patient_id = patient_id

    # Store metadata
    _session_metadata[session_id] = _create_session_metadata(session_id, patient_id)

    return {
        "session_id": session_id,
        "patient_id": patient_id,
        "created_at": _session_metadata[session_id]["created_at"],
    }


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session information.

    Args:
        session_id: Session identifier.

    Returns:
        Session metadata.

    Raises:
        HTTPException: If session not found.
    """
    if session_id not in _session_metadata:
        raise HTTPException(status_code=404, detail="Session not found")

    return _session_metadata[session_id]


@router.get("")
async def list_sessions(
    patient_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """List sessions with pagination, optionally filtered by patient.

    Args:
        patient_id: Optional patient filter.
        limit: Maximum number of sessions to return.
        offset: Number of sessions to skip for pagination.

    Returns:
        Dict with sessions list and pagination info.
    """
    sessions = list(_session_metadata.values())

    if patient_id:
        sessions = [s for s in sessions if s.get("patient_id") == patient_id]

    # Sort by last_activity descending
    sessions.sort(key=lambda x: x["last_activity"], reverse=True)

    total = len(sessions)
    paginated = sessions[offset:offset + limit]

    return {
        "sessions": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session.

    Args:
        session_id: Session identifier.

    Returns:
        Success message.

    Raises:
        HTTPException: If session not found.
    """
    if session_id not in _session_metadata:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up
    _session_store.delete(session_id)
    del _session_metadata[session_id]

    return {"message": "Session deleted"}


@router.patch("/{session_id}/activity")
async def update_activity(session_id: str) -> dict:
    """Update session last activity timestamp.

    Args:
        session_id: Session identifier.

    Returns:
        Updated session info.

    Raises:
        HTTPException: If session not found.
    """
    if session_id not in _session_metadata:
        raise HTTPException(status_code=404, detail="Session not found")

    _session_metadata[session_id]["last_activity"] = datetime.now().isoformat()

    return _session_metadata[session_id]
