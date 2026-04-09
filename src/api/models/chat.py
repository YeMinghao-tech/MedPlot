"""Pydantic models for chat API."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message request model."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message content"
    )


class ChatResponse(BaseModel):
    """Chat message response model."""

    session_id: str
    intent: str
    state: str
    response: str
