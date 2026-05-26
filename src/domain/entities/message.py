"""
Message entity.

Represents a single chat message within a room, supporting text,
media, replies, editing, soft-deletion, and optional end-to-end
encrypted content.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.shared.constants import MessageType
from src.shared.utils import utc_now


@dataclass
class Message:
    """A chat message sent within a room.

    Attributes:
        id: Auto-incremented integer identifier (assigned by the database).
        room_id: The room this message belongs to.
        sender_id: UUID of the user who sent the message.
        content: Plain-text (or rendered) message body.
        encrypted_content: Optional E2E-encrypted payload.
        message_type: The kind of content this message carries.
        reply_to: Optional ID of the message this is a reply to.
        is_edited: Whether the content has been edited after sending.
        edited_at: Timestamp of the most recent edit.
        is_deleted: Whether the message has been soft-deleted.
        deleted_at: Timestamp of soft-deletion.
        metadata: Arbitrary key/value metadata (file size, mime type, etc.).
        created_at: When the message was created.
    """

    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    id: int | None = None
    encrypted_content: str | None = None
    message_type: MessageType = MessageType.TEXT
    reply_to: int | None = None
    is_edited: bool = False
    edited_at: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Assign defaults for auto-generated fields."""
        if self.created_at is None:
            self.created_at = utc_now()

    # ── mutations ────────────────────────────────────────────────

    def soft_delete(self) -> None:
        """Mark the message as deleted without removing it from storage.

        Sets ``is_deleted`` to *True* and records the deletion timestamp.
        """
        self.is_deleted = True
        self.deleted_at = utc_now()

    def edit(self, new_content: str) -> None:
        """Replace the message content and mark it as edited.

        Args:
            new_content: The updated message body.
        """
        self.content = new_content
        self.is_edited = True
        self.edited_at = utc_now()

    # ── serialization ────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message to a JSON-safe dictionary.

        Returns:
            Dictionary representation of all message fields.
        """
        return {
            "id": self.id,
            "room_id": str(self.room_id),
            "sender_id": str(self.sender_id),
            "content": self.content,
            "encrypted_content": self.encrypted_content,
            "message_type": str(self.message_type),
            "reply_to": self.reply_to,
            "is_edited": self.is_edited,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
