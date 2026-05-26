"""
Chat service.

Core messaging logic — sending messages, delivery tracking, read receipts,
message history retrieval, search, and offline message queuing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.exceptions import AuthorizationError, EntityNotFoundError
from src.shared.constants import WSEventType
from src.shared.utils import sanitize_input, utc_now

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates message sending, delivery, and history retrieval."""

    def __init__(
        self,
        message_repo: Any,
        room_repo: Any,
        event_bus: Any,
        cache_service: Any,
    ) -> None:
        self._message_repo = message_repo
        self._room_repo = room_repo
        self._event_bus = event_bus
        self._cache = cache_service

    async def send_message(
        self,
        room_id: UUID,
        sender_id: UUID,
        content: str,
        message_type: str = "text",
        reply_to: int | None = None,
        encrypted: bool = False,
    ) -> dict[str, Any]:
        """Send a message to a room.

        Validates membership, persists the message, publishes via event bus,
        and tracks delivery for each room member.

        Args:
            room_id: Target room UUID.
            sender_id: Sender's user UUID.
            content: Message content.
            message_type: Type of message (text, image, file, system).
            reply_to: Optional message ID being replied to.
            encrypted: Whether the content is already encrypted.

        Returns:
            Dict with message details and delivery status.

        Raises:
            AuthorizationError: If sender is not a room member.
        """
        # Verify membership
        is_member = await self._room_repo.is_member(room_id, sender_id)
        if not is_member:
            raise AuthorizationError("You are not a member of this room")

        # Sanitize and persist
        clean_content = sanitize_input(content) if not encrypted else content
        msg_data: dict[str, Any] = {
            "room_id": room_id,
            "sender_id": sender_id,
            "content": clean_content if not encrypted else None,
            "encrypted_content": clean_content if encrypted else None,
            "message_type": message_type,
            "reply_to": reply_to,
        }
        message = await self._message_repo.create(msg_data)

        # Build event payload
        now = utc_now()
        event_payload = {
            "type": WSEventType.MESSAGE_NEW,
            "message_id": message.id,
            "room_id": str(room_id),
            "sender_id": str(sender_id),
            "content": clean_content,
            "message_type": message_type,
            "reply_to": reply_to,
            "created_at": now.isoformat(),
        }

        # Publish to event bus (cross-node broadcast)
        await self._event_bus.publish_message(str(room_id), event_payload)

        # Track delivery for room members
        members = await self._room_repo.get_members(room_id)
        for member in members:
            member_user_id = member.user_id if hasattr(member, "user_id") else member
            if member_user_id != sender_id:
                try:
                    await self._message_repo.create_delivery(
                        message.id, member_user_id, status="pending"
                    )
                except Exception:
                    logger.warning(
                        "Failed to create delivery record",
                        extra={"message_id": message.id, "user_id": str(member_user_id)},
                    )

        logger.info(
            "Message sent",
            extra={"message_id": message.id, "room_id": str(room_id)},
        )

        return {
            "message_id": message.id,
            "room_id": str(room_id),
            "sender_id": str(sender_id),
            "content": clean_content,
            "message_type": message_type,
            "created_at": now.isoformat(),
            "status": "sent",
        }

    async def get_messages(
        self,
        room_id: UUID,
        user_id: UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get paginated message history for a room.

        Args:
            room_id: Room UUID.
            user_id: Requesting user's UUID (for membership check).
            limit: Max messages to return.
            before: Cursor for pagination.

        Returns:
            List of message dicts, newest first.
        """
        if not await self._room_repo.is_member(room_id, user_id):
            raise AuthorizationError("You are not a member of this room")

        messages = await self._message_repo.get_by_room(room_id, limit=limit, before=before)
        return [
            {
                "message_id": m.id,
                "room_id": str(m.room_id),
                "sender_id": str(m.sender_id),
                "content": m.content or m.encrypted_content,
                "message_type": m.message_type,
                "reply_to": m.reply_to,
                "is_edited": m.is_edited,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    async def mark_read(
        self, room_id: UUID, message_id: int, user_id: UUID
    ) -> None:
        """Mark a message as read and update room last_read timestamp.

        Args:
            room_id: Room UUID.
            message_id: Message ID being read.
            user_id: User marking the message as read.
        """
        now = utc_now()
        await self._message_repo.update_delivery_status(
            message_id, user_id, "read", timestamp=now
        )
        await self._room_repo.update_last_read(room_id, user_id, now)

        # Broadcast read receipt
        await self._event_bus.publish_message(str(room_id), {
            "type": WSEventType.MESSAGE_READ_RECEIPT,
            "message_id": message_id,
            "user_id": str(user_id),
            "room_id": str(room_id),
            "read_at": now.isoformat(),
        })

    async def search_messages(
        self,
        room_id: UUID,
        query: str,
        user_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Full-text search within a room's messages.

        Args:
            room_id: Room UUID.
            query: Search query string.
            user_id: Requesting user's UUID.
            limit: Max results.

        Returns:
            List of matching message dicts.
        """
        if not await self._room_repo.is_member(room_id, user_id):
            raise AuthorizationError("You are not a member of this room")

        messages = await self._message_repo.search(room_id, query, limit=limit)
        return [
            {
                "message_id": m.id,
                "room_id": str(m.room_id),
                "sender_id": str(m.sender_id),
                "content": m.content,
                "message_type": m.message_type,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    async def delete_message(self, message_id: int, user_id: UUID) -> bool:
        """Soft-delete a message (only the sender can delete).

        Args:
            message_id: Message ID to delete.
            user_id: User attempting the delete.

        Returns:
            True if successfully deleted.

        Raises:
            AuthorizationError: If user is not the message sender.
            EntityNotFoundError: If message doesn't exist.
        """
        message = await self._message_repo.get_by_id(message_id)
        if not message:
            raise EntityNotFoundError("Message", str(message_id))
        if message.sender_id != user_id:
            raise AuthorizationError("You can only delete your own messages")

        return await self._message_repo.soft_delete(message_id)

    async def edit_message(
        self, message_id: int, user_id: UUID, new_content: str
    ) -> dict[str, Any] | None:
        """Edit a message (only the sender can edit).

        Args:
            message_id: Message ID to edit.
            user_id: User attempting the edit.
            new_content: New message content.

        Returns:
            Updated message dict, or None.

        Raises:
            AuthorizationError: If user is not the sender.
        """
        message = await self._message_repo.get_by_id(message_id)
        if not message:
            raise EntityNotFoundError("Message", str(message_id))
        if message.sender_id != user_id:
            raise AuthorizationError("You can only edit your own messages")

        clean_content = sanitize_input(new_content)
        updated = await self._message_repo.mark_edited(message_id, clean_content)
        if updated:
            return {
                "message_id": updated.id,
                "content": updated.content,
                "is_edited": True,
                "edited_at": updated.edited_at.isoformat() if updated.edited_at else None,
            }
        return None
