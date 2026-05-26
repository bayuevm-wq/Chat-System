"""
Room-related domain events.

Events emitted when rooms are created or users join/leave rooms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.events.base import DomainEvent


@dataclass
class RoomCreatedEvent(DomainEvent):
    """Raised when a new room is created.

    Attributes:
        room_id: UUID string of the newly created room.
        name: Human-readable room name (may be *None* for DMs).
        type: Room type label (public, private, direct).
        created_by: UUID string of the room creator.
    """

    room_id: str | None = None
    name: str | None = None
    type: str | None = None
    created_by: str | None = None

    @classmethod
    def create(
        cls,
        room_id: str,
        name: str | None,
        type: str,
        created_by: str,
        *,
        source_node: str | None = None,
    ) -> RoomCreatedEvent:
        """Build a ``RoomCreatedEvent`` with the correct event_type.

        Args:
            room_id: UUID string of the room.
            name: Room name.
            type: Room type label.
            created_by: UUID string of the creator.
            source_node: Optional originating node.

        Returns:
            A fully populated ``RoomCreatedEvent``.
        """
        payload: dict[str, Any] = {
            "room_id": room_id,
            "name": name,
            "type": type,
            "created_by": created_by,
        }
        return cls(
            event_type="room.created",
            payload=payload,
            source_node=source_node,
            room_id=room_id,
            name=name,
            type=type,
            created_by=created_by,
        )


@dataclass
class UserJoinedRoomEvent(DomainEvent):
    """Raised when a user joins a room.

    Attributes:
        room_id: UUID string of the room.
        user_id: UUID string of the user who joined.
        role: The role assigned to the user in the room.
    """

    room_id: str | None = None
    user_id: str | None = None
    role: str | None = None

    @classmethod
    def create(
        cls,
        room_id: str,
        user_id: str,
        role: str,
        *,
        source_node: str | None = None,
    ) -> UserJoinedRoomEvent:
        """Build a ``UserJoinedRoomEvent`` with the correct event_type.

        Args:
            room_id: UUID string of the room.
            user_id: UUID string of the joining user.
            role: Role label (e.g. ``"member"``, ``"admin"``).
            source_node: Optional originating node.

        Returns:
            A fully populated ``UserJoinedRoomEvent``.
        """
        payload: dict[str, Any] = {
            "room_id": room_id,
            "user_id": user_id,
            "role": role,
        }
        return cls(
            event_type="room.user_joined",
            payload=payload,
            source_node=source_node,
            room_id=room_id,
            user_id=user_id,
            role=role,
        )


@dataclass
class UserLeftRoomEvent(DomainEvent):
    """Raised when a user leaves a room.

    Attributes:
        room_id: UUID string of the room.
        user_id: UUID string of the user who left.
    """

    room_id: str | None = None
    user_id: str | None = None

    @classmethod
    def create(
        cls,
        room_id: str,
        user_id: str,
        *,
        source_node: str | None = None,
    ) -> UserLeftRoomEvent:
        """Build a ``UserLeftRoomEvent`` with the correct event_type.

        Args:
            room_id: UUID string of the room.
            user_id: UUID string of the leaving user.
            source_node: Optional originating node.

        Returns:
            A fully populated ``UserLeftRoomEvent``.
        """
        payload: dict[str, Any] = {
            "room_id": room_id,
            "user_id": user_id,
        }
        return cls(
            event_type="room.user_left",
            payload=payload,
            source_node=source_node,
            room_id=room_id,
            user_id=user_id,
        )
