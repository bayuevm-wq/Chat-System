"""
Application-wide constants.

Centralizes all magic strings, default values, and configuration constants
used across the distributed chat system.
"""

from __future__ import annotations

from enum import StrEnum


# ── User Status ─────────────────────────────────────────────────
class UserStatus(StrEnum):
    """Possible user presence states."""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


# ── Room Types ──────────────────────────────────────────────────
class RoomType(StrEnum):
    """Types of chat rooms."""
    PUBLIC = "public"
    PRIVATE = "private"
    DIRECT = "direct"


# ── Room Roles ──────────────────────────────────────────────────
class RoomRole(StrEnum):
    """Member roles within a room."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


# ── Message Types ───────────────────────────────────────────────
class MessageType(StrEnum):
    """Types of message content."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


# ── Delivery Status ────────────────────────────────────────────
class DeliveryStatus(StrEnum):
    """Message delivery states."""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# ── Offline Message Status ──────────────────────────────────────
class OfflineMessageStatus(StrEnum):
    """Offline message queue states."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    DEAD_LETTER = "dead_letter"


# ── Notification Types ──────────────────────────────────────────
class NotificationType(StrEnum):
    """Types of push notifications."""
    MESSAGE = "message"
    MENTION = "mention"
    ROOM_INVITE = "room_invite"
    SYSTEM = "system"


# ── WebSocket Event Types ───────────────────────────────────────
class WSEventType(StrEnum):
    """WebSocket event type identifiers for client ↔ server communication."""

    # Client → Server
    MESSAGE_SEND = "message.send"
    MESSAGE_READ = "message.read"
    TYPING_START = "typing.start"
    TYPING_STOP = "typing.stop"
    PRESENCE_UPDATE = "presence.update"
    PRESENCE_HEARTBEAT = "presence.heartbeat"
    ROOM_JOIN = "room.join"
    ROOM_LEAVE = "room.leave"

    # Server → Client
    CONNECTED = "connected"
    MESSAGE_NEW = "message.new"
    MESSAGE_ACK = "message.ack"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_READ_RECEIPT = "message.read_receipt"
    TYPING_INDICATOR = "typing.indicator"
    PRESENCE_CHANGE = "presence.change"
    ROOM_UPDATED = "room.updated"
    NOTIFICATION = "notification"
    ERROR = "error"
    PONG = "pong"


# ── Redis Key Prefixes ─────────────────────────────────────────
class RedisPrefix:
    """Redis key namespace prefixes to avoid collisions."""
    SESSION = "session:"
    PRESENCE = "presence:"
    TYPING = "typing:"
    NODE = "node:"
    NODE_HEARTBEAT = "node:heartbeat:"
    ROOM_MEMBERS = "room:members:"
    USER_ROOMS = "user:rooms:"
    RATE_LIMIT = "ratelimit:"

    # Pub/Sub channels
    PUBSUB_CHAT = "pubsub:chat:"
    PUBSUB_PRESENCE = "pubsub:presence:updates"
    PUBSUB_NODE = "pubsub:node:"
    PUBSUB_SYSTEM = "pubsub:system:broadcast"

    # Stream keys
    STREAM_CHAT = "stream:chat:"
    STREAM_OFFLINE = "stream:offline_messages"
    STREAM_NOTIFICATIONS = "stream:notifications"
    STREAM_DEAD_LETTER = "stream:dead_letter"


# ── Defaults ────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
MAX_ROOM_NAME_LENGTH = 100
MAX_USERNAME_LENGTH = 50
MAX_MESSAGE_LENGTH = 10_000
PRESENCE_TTL_SECONDS = 60
TYPING_TTL_SECONDS = 5
NODE_HEARTBEAT_TTL_SECONDS = 60
SESSION_TOKEN_BYTES = 32
MAX_STREAM_LENGTH = 10_000  # Trim Redis streams to this length per room
