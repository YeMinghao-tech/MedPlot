"""Chat routes for conversation."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.routers._shared import get_session_store
from src.agent.planner.router import Router
from src.libs.llm.llm_factory import LLMFactory
from src.libs.his.his_factory import HISFactory
from src.tools.his_orchestrator.schedule_service import ScheduleService
from src.tools.his_orchestrator.dept_service import DepartmentService
from src.tools.his_orchestrator.booking_service import BookingService
from src.core.settings import load_settings


# Session store (shared with session router)
_session_store = get_session_store()

router = APIRouter(tags=["chat"])


# Global router instance
_router_instance: Optional[Router] = None


def get_router() -> Router:
    """Get or create the router instance."""
    global _router_instance
    if _router_instance is None:
        try:
            settings = load_settings("config/settings.yaml")
            print(f"[DEBUG] Settings loaded: llm.api_key={'set' if settings.llm.api_key else 'None'}")

            # Create LLM client if available
            if settings and settings.llm and settings.llm.api_key:
                print(f"[DEBUG] Creating LLM client with provider={settings.llm.provider}, model={settings.llm.model}")
                llm_client = LLMFactory.create(settings)
                print(f"[DEBUG] LLM client created: {llm_client}")
            else:
                print("[DEBUG] No LLM config, llm_client will be None")
                llm_client = None

            # Create HIS services
            his_client = None
            if settings and settings.his:
                try:
                    his_client = HISFactory.create(settings)
                    print(f"[DEBUG] HIS client created: {his_client}")
                except Exception as e:
                    print(f"[DEBUG] HIS client error: {e}")

            # Create services
            schedule_service = ScheduleService(his_client) if his_client else None
            dept_service = DepartmentService(his_client) if his_client else None
            booking_service = BookingService(his_client) if his_client else None

            _router_instance = Router(
                llm_client=llm_client,
                schedule_service=schedule_service,
                department_service=dept_service,
                booking_service=booking_service,
            )
            print(f"[DEBUG] Router created with llm_client={llm_client}, booking_service={booking_service}")
        except Exception as e:
            print(f"[ERROR] Error creating router: {e}")
            import traceback
            traceback.print_exc()
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
