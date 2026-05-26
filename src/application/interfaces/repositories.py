"""
Abstract repository interfaces (ports).

These define the contracts that infrastructure adapters must implement,
enabling dependency inversion and clean separation between domain
logic and persistence concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID


class IUserRepository(ABC):
    """Port for user persistence operations."""

    @abstractmethod
    async def create(self, user_data: dict[str, Any]) -> Any:
        """Create a new user record."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Any | None:
        """Fetch user by primary key."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        """Fetch user by email address."""
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> Any | None:
        """Fetch user by username."""
        ...

    @abstractmethod
    async def update(self, user_id: UUID, **kwargs: Any) -> Any:
        """Update user fields."""
        ...

    @abstractmethod
    async def update_last_seen(self, user_id: UUID, timestamp: datetime) -> None:
        """Update the user's last-seen timestamp."""
        ...

    @abstractmethod
    async def exists(self, username: str | None = None, email: str | None = None) -> bool:
        """Check if a user exists by username or email."""
        ...


class IMessageRepository(ABC):
    """Port for message persistence operations."""

    @abstractmethod
    async def create(self, message_data: dict[str, Any]) -> Any:
        """Persist a new message."""
        ...

    @abstractmethod
    async def get_by_id(self, message_id: int) -> Any | None:
        """Fetch message by primary key."""
        ...

    @abstractmethod
    async def get_by_room(
        self,
        room_id: UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[Any]:
        """Fetch paginated messages for a room, newest first."""
        ...

    @abstractmethod
    async def search(
        self,
        room_id: UUID,
        query: str,
        limit: int = 50,
    ) -> list[Any]:
        """Full-text search within a room's messages."""
        ...

    @abstractmethod
    async def soft_delete(self, message_id: int) -> bool:
        """Soft-delete a message (mark as deleted)."""
        ...

    @abstractmethod
    async def mark_edited(self, message_id: int, new_content: str) -> Any | None:
        """Update message content and mark as edited."""
        ...

    @abstractmethod
    async def create_delivery(
        self, message_id: int, user_id: UUID, status: str = "pending"
    ) -> Any:
        """Create a delivery tracking record."""
        ...

    @abstractmethod
    async def update_delivery_status(
        self,
        message_id: int,
        user_id: UUID,
        status: str,
        timestamp: datetime | None = None,
    ) -> None:
        """Update delivery status for a message/user pair."""
        ...

    @abstractmethod
    async def get_pending_deliveries(self, user_id: UUID) -> list[Any]:
        """Get all pending deliveries for a user."""
        ...

    @abstractmethod
    async def create_offline_message(self, message_id: int, user_id: UUID) -> Any:
        """Queue a message for offline delivery."""
        ...

    @abstractmethod
    async def get_offline_messages(self, user_id: UUID) -> list[Any]:
        """Get all pending offline messages for a user."""
        ...

    @abstractmethod
    async def update_offline_status(
        self,
        offline_id: UUID,
        status: str,
        next_retry: datetime | None = None,
    ) -> None:
        """Update offline message status and retry schedule."""
        ...


class IRoomRepository(ABC):
    """Port for room and membership persistence operations."""

    @abstractmethod
    async def create(self, room_data: dict[str, Any]) -> Any:
        """Create a new room."""
        ...

    @abstractmethod
    async def get_by_id(self, room_id: UUID) -> Any | None:
        """Fetch room by primary key."""
        ...

    @abstractmethod
    async def get_user_rooms(self, user_id: UUID) -> list[Any]:
        """Get all rooms a user is a member of."""
        ...

    @abstractmethod
    async def add_member(
        self, room_id: UUID, user_id: UUID, role: str = "member"
    ) -> Any:
        """Add a member to a room."""
        ...

    @abstractmethod
    async def remove_member(self, room_id: UUID, user_id: UUID) -> None:
        """Remove a member from a room."""
        ...

    @abstractmethod
    async def get_members(self, room_id: UUID) -> list[Any]:
        """Get all members of a room."""
        ...

    @abstractmethod
    async def get_member(self, room_id: UUID, user_id: UUID) -> Any | None:
        """Get a specific member record."""
        ...

    @abstractmethod
    async def is_member(self, room_id: UUID, user_id: UUID) -> bool:
        """Check if a user is a member of a room."""
        ...

    @abstractmethod
    async def update_last_read(
        self, room_id: UUID, user_id: UUID, timestamp: datetime
    ) -> None:
        """Update the last-read timestamp for a member."""
        ...

    @abstractmethod
    async def get_unread_count(self, room_id: UUID, user_id: UUID) -> int:
        """Count unread messages for a member in a room."""
        ...

    @abstractmethod
    async def get_or_create_direct_room(
        self, user_id_1: UUID, user_id_2: UUID
    ) -> Any:
        """Get or create a direct message room between two users."""
        ...
