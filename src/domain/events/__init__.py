"""
Domain events — immutable records of things that happened.

Re-exports every event class so consumers can do::

    from src.domain.events import MessageSentEvent, UserOnlineEvent, ...
"""

from __future__ import annotations

from src.domain.events.base import DomainEvent
from src.domain.events.chat_events import (
    MessageDeliveredEvent,
    MessageReadEvent,
    MessageSentEvent,
    TypingEvent,
)
from src.domain.events.presence_events import (
    HeartbeatEvent,
    UserOfflineEvent,
    UserOnlineEvent,
    UserStatusChangedEvent,
)
from src.domain.events.room_events import (
    RoomCreatedEvent,
    UserJoinedRoomEvent,
    UserLeftRoomEvent,
)
from src.domain.events.system_events import (
    NodeHeartbeatEvent,
    NodeRegisteredEvent,
    NodeShutdownEvent,
)

__all__ = [
    # base
    "DomainEvent",
    # chat
    "MessageDeliveredEvent",
    "MessageReadEvent",
    "MessageSentEvent",
    "TypingEvent",
    # presence
    "HeartbeatEvent",
    "UserOfflineEvent",
    "UserOnlineEvent",
    "UserStatusChangedEvent",
    # room
    "RoomCreatedEvent",
    "UserJoinedRoomEvent",
    "UserLeftRoomEvent",
    # system
    "NodeHeartbeatEvent",
    "NodeRegisteredEvent",
    "NodeShutdownEvent",
]
