"""
Room and RoomMember entities.

A *Room* is a conversation space (public channel, private group, or
direct message). A *RoomMember* represents a user's membership and
role within a room.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from src.shared.constants import RoomRole, RoomType
from src.shared.utils import generate_id, utc_now


@dataclass
class Room:
    """A chat room that groups users and their messages.

    Attributes:
        id: Unique room identifier (UUID v4).
        name: Human-readable room name (may be *None* for DM rooms).
        type: The kind of room (public, private, direct).
        created_by: UUID of the user who created the room.
        description: Optional longer description of the room's purpose.
        max_members: Upper limit on simultaneous members.
        is_active: Whether the room is currently active (not archived).
        created_at: When the room was created.
        updated_at: When the room was last modified.
    """

    type: RoomType
    name: str | None = None
    id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    description: str | None = None
    max_members: int = 500
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Assign defaults for auto-generated fields."""
        if self.id is None:
            self.id = generate_id()
        if self.created_at is None:
            self.created_at = utc_now()
        if self.updated_at is None:
            self.updated_at = self.created_at


@dataclass
class RoomMember:
    """A user's membership record within a specific room.

    Attributes:
        room_id: The room the user belongs to.
        user_id: The user who is a member.
        role: The member's role within the room.
        joined_at: When the user joined the room.
        last_read_at: Timestamp of the last message the user has read.
        is_muted: Whether the user has muted notifications for this room.
        notifications_enabled: Whether push notifications are active.
    """

    room_id: uuid.UUID
    user_id: uuid.UUID
    role: RoomRole = RoomRole.MEMBER
    joined_at: datetime | None = None
    last_read_at: datetime | None = None
    is_muted: bool = False
    notifications_enabled: bool = True

    def __post_init__(self) -> None:
        """Assign defaults for auto-generated fields."""
        if self.joined_at is None:
            self.joined_at = utc_now()
