"""
Chat-related domain events.

Events emitted when messages are sent, delivered, read, or when
a user starts/stops typing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.events.base import DomainEvent


@dataclass
class MessageSentEvent(DomainEvent):
    """Raised when a new message is persisted in a room.

    Attributes:
        message_id: Identifier of the sent message.
        room_id: Room the message was posted to.
        sender_id: UUID string of the sender.
        content: Plain-text message body.
        message_type: Message type label (text, image, file, system).
    """

    message_id: int | None = None
    room_id: str | None = None
    sender_id: str | None = None
    content: str | None = None
    message_type: str | None = None

    @classmethod
    def create(
        cls,
        message_id: int,
        room_id: str,
        sender_id: str,
        content: str,
        message_type: str,
        *,
        source_node: str | None = None,
    ) -> MessageSentEvent:
        """Build a ``MessageSentEvent`` with the correct event_type.

        Args:
            message_id: The database ID of the message.
            room_id: UUID string of the target room.
            sender_id: UUID string of the sender.
            content: The message body.
            message_type: E.g. ``"text"``, ``"image"``.
            source_node: Optional originating node.

        Returns:
            A fully populated ``MessageSentEvent``.
        """
        payload: dict[str, Any] = {
            "message_id": message_id,
            "room_id": room_id,
            "sender_id": sender_id,
            "content": content,
            "message_type": message_type,
        }
        return cls(
            event_type="message.sent",
            payload=payload,
            source_node=source_node,
            message_id=message_id,
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
        )


@dataclass
class MessageDeliveredEvent(DomainEvent):
    """Raised when a message has been delivered to a recipient.

    Attributes:
        message_id: The delivered message's ID.
        user_id: UUID string of the recipient.
        room_id: UUID string of the room.
    """

    message_id: int | None = None
    user_id: str | None = None
    room_id: str | None = None

    @classmethod
    def create(
        cls,
        message_id: int,
        user_id: str,
        room_id: str,
        *,
        source_node: str | None = None,
    ) -> MessageDeliveredEvent:
        """Build a ``MessageDeliveredEvent`` with the correct event_type.

        Args:
            message_id: The database ID of the message.
            user_id: UUID string of the recipient.
            room_id: UUID string of the room.
            source_node: Optional originating node.

        Returns:
            A fully populated ``MessageDeliveredEvent``.
        """
        payload: dict[str, Any] = {
            "message_id": message_id,
            "user_id": user_id,
            "room_id": room_id,
        }
        return cls(
            event_type="message.delivered",
            payload=payload,
            source_node=source_node,
            message_id=message_id,
            user_id=user_id,
            room_id=room_id,
        )


@dataclass
class MessageReadEvent(DomainEvent):
    """Raised when a user marks a message as read.

    Attributes:
        message_id: The read message's ID.
        user_id: UUID string of the reader.
        room_id: UUID string of the room.
    """

    message_id: int | None = None
    user_id: str | None = None
    room_id: str | None = None

    @classmethod
    def create(
        cls,
        message_id: int,
        user_id: str,
        room_id: str,
        *,
        source_node: str | None = None,
    ) -> MessageReadEvent:
        """Build a ``MessageReadEvent`` with the correct event_type.

        Args:
            message_id: The database ID of the message.
            user_id: UUID string of the reader.
            room_id: UUID string of the room.
            source_node: Optional originating node.

        Returns:
            A fully populated ``MessageReadEvent``.
        """
        payload: dict[str, Any] = {
            "message_id": message_id,
            "user_id": user_id,
            "room_id": room_id,
        }
        return cls(
            event_type="message.read",
            payload=payload,
            source_node=source_node,
            message_id=message_id,
            user_id=user_id,
            room_id=room_id,
        )


@dataclass
class TypingEvent(DomainEvent):
    """Raised when a user starts or stops typing in a room.

    Attributes:
        room_id: UUID string of the room.
        user_id: UUID string of the typing user.
        is_typing: ``True`` when the user starts typing, ``False`` when they stop.
    """

    room_id: str | None = None
    user_id: str | None = None
    is_typing: bool = False

    @classmethod
    def create(
        cls,
        room_id: str,
        user_id: str,
        is_typing: bool,
        *,
        source_node: str | None = None,
    ) -> TypingEvent:
        """Build a ``TypingEvent`` with the correct event_type.

        Args:
            room_id: UUID string of the room.
            user_id: UUID string of the typing user.
            is_typing: Whether the user is currently typing.
            source_node: Optional originating node.

        Returns:
            A fully populated ``TypingEvent``.
        """
        payload: dict[str, Any] = {
            "room_id": room_id,
            "user_id": user_id,
            "is_typing": is_typing,
        }
        return cls(
            event_type="typing.indicator",
            payload=payload,
            source_node=source_node,
            room_id=room_id,
            user_id=user_id,
            is_typing=is_typing,
        )
