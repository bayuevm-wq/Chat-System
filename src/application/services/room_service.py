"""
Room service.

Manages chat room lifecycle — creation, membership, direct messages,
and room metadata operations.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.domain.exceptions import (
    AuthorizationError,
    EntityNotFoundError,
    RoomFullError,
)
from src.shared.constants import RoomType, WSEventType
from src.shared.utils import generate_id

logger = logging.getLogger(__name__)


class RoomService:
    """Orchestrates room creation, membership, and metadata."""

    def __init__(self, room_repo: Any, cache_service: Any, event_bus: Any) -> None:
        self._room_repo = room_repo
        self._cache = cache_service
        self._event_bus = event_bus

    async def create_room(
        self,
        name: str,
        room_type: str,
        created_by: UUID,
        description: str | None = None,
        max_members: int = 500,
    ) -> dict[str, Any]:
        """Create a new chat room and add the creator as owner.

        Returns:
            Dict with room details.
        """
        room = await self._room_repo.create({
            "id": generate_id(),
            "name": name,
            "type": room_type,
            "created_by": created_by,
            "description": description,
            "max_members": max_members,
        })
        # Add creator as owner
        await self._room_repo.add_member(room.id, created_by, role="owner")
        await self._cache.invalidate_room_members(str(room.id))

        await self._event_bus.publish_system({
            "type": WSEventType.ROOM_UPDATED,
            "event": "room_created",
            "room_id": str(room.id),
            "name": name,
            "created_by": str(created_by),
        })

        logger.info("Room created", extra={"room_id": str(room.id), "name": name})
        return {
            "id": str(room.id),
            "name": room.name,
            "type": room.type,
            "description": room.description,
            "max_members": room.max_members,
            "created_by": str(room.created_by),
        }

    async def join_room(self, room_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Join an existing room.

        Raises:
            EntityNotFoundError: If room doesn't exist.
            RoomFullError: If room is at capacity.
        """
        room = await self._room_repo.get_by_id(room_id)
        if not room:
            raise EntityNotFoundError("Room", str(room_id))

        if room.type == RoomType.DIRECT:
            raise AuthorizationError("Cannot join direct message rooms")

        members = await self._room_repo.get_members(room_id)
        if len(members) >= room.max_members:
            raise RoomFullError(str(room_id))

        if await self._room_repo.is_member(room_id, user_id):
            return {"room_id": str(room_id), "status": "already_member"}

        await self._room_repo.add_member(room_id, user_id)
        await self._cache.invalidate_room_members(str(room_id))

        await self._event_bus.publish_message(str(room_id), {
            "type": WSEventType.ROOM_UPDATED,
            "event": "user_joined",
            "room_id": str(room_id),
            "user_id": str(user_id),
        })

        return {"room_id": str(room_id), "status": "joined"}

    async def leave_room(self, room_id: UUID, user_id: UUID) -> None:
        """Leave a room."""
        await self._room_repo.remove_member(room_id, user_id)
        await self._cache.invalidate_room_members(str(room_id))

        await self._event_bus.publish_message(str(room_id), {
            "type": WSEventType.ROOM_UPDATED,
            "event": "user_left",
            "room_id": str(room_id),
            "user_id": str(user_id),
        })

    async def get_room(self, room_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Get room details with membership check."""
        room = await self._room_repo.get_by_id(room_id)
        if not room:
            raise EntityNotFoundError("Room", str(room_id))
        if not await self._room_repo.is_member(room_id, user_id):
            raise AuthorizationError("You are not a member of this room")

        return {
            "id": str(room.id),
            "name": room.name,
            "type": room.type,
            "description": room.description,
            "max_members": room.max_members,
            "is_active": room.is_active,
        }

    async def get_user_rooms(self, user_id: UUID) -> list[dict[str, Any]]:
        """Get all rooms the user is a member of."""
        rooms = await self._room_repo.get_user_rooms(user_id)
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "type": r.type,
                "description": r.description,
            }
            for r in rooms
        ]

    async def get_room_members(self, room_id: UUID) -> list[dict[str, Any]]:
        """Get all members of a room."""
        members = await self._room_repo.get_members(room_id)
        return [
            {
                "user_id": str(m.user_id),
                "role": m.role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ]

    async def get_or_create_dm(
        self, user_id_1: UUID, user_id_2: UUID
    ) -> dict[str, Any]:
        """Get or create a direct message room between two users."""
        room = await self._room_repo.get_or_create_direct_room(user_id_1, user_id_2)
        return {
            "id": str(room.id),
            "name": room.name,
            "type": RoomType.DIRECT,
        }
