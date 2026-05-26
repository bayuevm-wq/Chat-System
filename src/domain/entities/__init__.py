"""
Domain entities — the core business objects of the chat system.

Re-exports every entity so that consumers can do::

    from src.domain.entities import User, Message, Room, ...
"""

from __future__ import annotations

from src.domain.entities.message import Message
from src.domain.entities.notification import Notification
from src.domain.entities.room import Room, RoomMember
from src.domain.entities.session import UserSession
from src.domain.entities.user import User

__all__ = [
    "Message",
    "Notification",
    "Room",
    "RoomMember",
    "User",
    "UserSession",
]
