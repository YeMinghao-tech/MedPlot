"""Chat routes for conversation."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.routers._shared import get_session_store
from src.agent.planner.router import Router


# Session store (shared with session router)
_session_store = get_session_store()

router = APIRouter(tags=["chat"])


# Global router instance
_router_instance: Optional[Router] = None


def get_router() -> Router:
    """Get or create the router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = Router()
    return _router_instance


@router.post("/{session_id}")
async def chat(session_id: str, message: dict) -> dict:
    """Send a chat message and get response.

    Args:
        session_id: Session identifier.
        message: Message dict with 'content' field.

    Returns:
        Response dict with assistant message.
    """
    if session_id not in _session_store._memories:
        raise HTTPException(status_code=404, detail="Session not found")

    content = message.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")

    # Get working memory
    memory = _session_store.get(session_id)
    memory.add_turn("user", content)

    # Route the message
    router = get_router()
    patient_id = memory.patient_id

    result = router.route(content, patient_id=patient_id)

    # Add assistant response to history
    memory.add_turn("assistant", result["response"])

    return {
        "session_id": session_id,
        "intent": result["intent"],
        "state": result["state"],
        "response": result["response"],
    }


@router.get("/{session_id}/history")
async def get_history(session_id: str, limit: int = 50) -> dict:
    """Get conversation history.

    Args:
        session_id: Session identifier.
        limit: Maximum number of turns to return.

    Returns:
        History dict with messages.
    """
    if session_id not in _session_store._memories:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = _session_store.get(session_id)
    recent = memory.get_recent_messages(limit)

    return {
        "session_id": session_id,
        "messages": [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ],
    }


@router.websocket("/{session_id}/ws")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket chat endpoint for streaming responses.

    Args:
        websocket: WebSocket connection.
        session_id: Session identifier.
    """
    if session_id not in _session_store._memories:
        memory = _session_store.get(session_id)

    memory = _session_store.get(session_id)

    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            content = data.get("content", "")

            if not content:
                continue

            # Add to history
            memory.add_turn("user", content)

            # Route
            router = get_router()
            result = router.route(content, patient_id=memory.patient_id)

            # Send response
            await websocket.send_json({
                "intent": result["intent"],
                "state": result["state"],
                "response": result["response"],
            })

            # Add assistant response to history
            memory.add_turn("assistant", result["response"])

    except WebSocketDisconnect:
        pass
