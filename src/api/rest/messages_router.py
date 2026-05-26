"""
Messages REST API router.

Endpoints for message history retrieval, search, editing, and deletion.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.dependencies import ChatServiceDep, CurrentUser

router = APIRouter(prefix="/api/messages", tags=["Messages"])


class EditMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


@router.get("/{room_id}")
async def get_messages(
    room_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None),
):
    """Get paginated message history for a room."""
    return await chat_service.get_messages(
        room_id=room_id,
        user_id=UUID(current_user["sub"]),
        limit=limit,
        before=before,
    )


@router.get("/{room_id}/search")
async def search_messages(
    room_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Full-text search within a room's messages."""
    return await chat_service.search_messages(
        room_id=room_id,
        query=q,
        user_id=UUID(current_user["sub"]),
        limit=limit,
    )


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    """Soft-delete a message (only the sender can delete)."""
    await chat_service.delete_message(message_id, UUID(current_user["sub"]))


@router.patch("/{message_id}")
async def edit_message(
    message_id: int,
    body: EditMessageRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    """Edit a message (only the sender can edit)."""
    return await chat_service.edit_message(
        message_id, UUID(current_user["sub"]), body.content
    )
