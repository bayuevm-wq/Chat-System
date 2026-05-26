"""
Rooms REST API router.

Endpoints for room creation, listing, joining, leaving, and member management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser, RoomServiceDep

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


class CreateRoomRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="public", pattern="^(public|private|direct)$")
    description: str | None = None
    max_members: int = Field(default=500, ge=2, le=10000)


@router.post("/", status_code=201)
async def create_room(
    body: CreateRoomRequest, current_user: CurrentUser, room_service: RoomServiceDep
):
    """Create a new chat room."""
    return await room_service.create_room(
        name=body.name,
        room_type=body.type,
        created_by=UUID(current_user["sub"]),
        description=body.description,
        max_members=body.max_members,
    )


@router.get("/")
async def list_rooms(current_user: CurrentUser, room_service: RoomServiceDep):
    """List all rooms the current user is a member of."""
    return await room_service.get_user_rooms(UUID(current_user["sub"]))


@router.get("/{room_id}")
async def get_room(
    room_id: UUID, current_user: CurrentUser, room_service: RoomServiceDep
):
    """Get room details."""
    return await room_service.get_room(room_id, UUID(current_user["sub"]))


@router.post("/{room_id}/join")
async def join_room(
    room_id: UUID, current_user: CurrentUser, room_service: RoomServiceDep
):
    """Join a room."""
    return await room_service.join_room(room_id, UUID(current_user["sub"]))


@router.post("/{room_id}/leave", status_code=204)
async def leave_room(
    room_id: UUID, current_user: CurrentUser, room_service: RoomServiceDep
):
    """Leave a room."""
    await room_service.leave_room(room_id, UUID(current_user["sub"]))


@router.get("/{room_id}/members")
async def get_members(
    room_id: UUID, current_user: CurrentUser, room_service: RoomServiceDep
):
    """List room members."""
    return await room_service.get_room_members(room_id)
