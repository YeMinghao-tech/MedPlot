"""Chat routes for conversation."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel, Field

from src.api.routers._shared import get_session_store
from src.agent.planner.router import Router
from src.api.models.chat import ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


# Session store (shared with session router)
_session_store = get_session_store()

router = APIRouter(tags=["chat"])


def get_router(request: Request) -> Router:
    """Get router from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        Router instance.

    Raises:
        HTTPException: If router not initialized.
    """
    router_instance: Optional[Router] = getattr(request.app.state, 'router', None)
    if router_instance is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Please try again later."
        )
    return router_instance


@router.post("/{session_id}", response_model=ChatResponse)
async def chat(session_id: str, message: ChatMessage, request: Request) -> ChatResponse:
    """Send a chat message and get response.

    Args:
        session_id: Session identifier.
        message: Chat message with validated content.
        request: FastAPI request.

    Returns:
        ChatResponse with assistant message.
    """
    if session_id not in _session_store._memories:
        raise HTTPException(status_code=404, detail="Session not found")

    content = message.content

    # Get working memory
    memory = _session_store.get(session_id)
    memory.add_turn("user", content)

    # Route the message
    chat_router = get_router(request)
    patient_id = memory.patient_id

    result = chat_router.route(content, patient_id=patient_id)

    # Add assistant response to history
    memory.add_turn("assistant", result["response"])

    return ChatResponse(
        session_id=session_id,
        intent=result["intent"],
        state=result["state"],
        response=result["response"],
    )


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
async def websocket_chat(websocket: WebSocket, session_id: str, request: Request):
    """WebSocket chat endpoint for streaming responses.

    Args:
        websocket: WebSocket connection.
        session_id: Session identifier.
        request: FastAPI request.
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
            chat_router = get_router(request)
            result = chat_router.route(content, patient_id=memory.patient_id)

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
