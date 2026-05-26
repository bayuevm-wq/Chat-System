"""
SQLAlchemy 2.0 ORM models for the Distributed Chat System.

Defines the relational schema for users, sessions, rooms, room members,
messages, message deliveries, offline messages, and notifications.
All models use the ``Mapped[]`` / ``mapped_column()`` API and reference
the shared ``Base`` from :mod:`src.infrastructure.database.connection`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.connection import Base
from src.shared.constants import (
    DeliveryStatus,
    MessageType,
    NotificationType,
    OfflineMessageStatus,
    RoomRole,
    RoomType,
    UserStatus,
)


# ── Users ──────────────────────────────────────────────────────
class UserModel(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique user identifier (UUID v4).",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique login handle.",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique email address.",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User-chosen display name.",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to profile avatar image.",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt password hash.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=UserStatus.OFFLINE,
        server_default=UserStatus.OFFLINE,
        nullable=False,
        comment="Current presence status.",
    )
    public_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="PEM-encoded RSA public key for E2E encryption.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Soft-disable flag.",
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last activity.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Account creation timestamp.",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
        comment="Last profile update timestamp.",
    )

    # ── Relationships ──
    sessions: Mapped[list[SessionModel]] = relationship(
        "SessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sent_messages: Mapped[list[MessageModel]] = relationship(
        "MessageModel",
        back_populates="sender",
        lazy="noload",
    )
    room_memberships: Mapped[list[RoomMemberModel]] = relationship(
        "RoomMemberModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    notifications: Mapped[list[NotificationModel]] = relationship(
        "NotificationModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<UserModel id={self.id!s} username={self.username!r}>"


# ── Sessions ───────────────────────────────────────────────────
class SessionModel(Base):
    """Active authentication session (one per device)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Session identifier.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning user.",
    )
    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Client-reported device identifier.",
    )
    node_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Chat-system node handling this session.",
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="SHA-256 hash of the refresh token.",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP (v4 or v6).",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiry timestamp.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Session creation timestamp.",
    )

    # ── Relationships ──
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="sessions",
    )

    def __repr__(self) -> str:
        return f"<SessionModel id={self.id!s} user_id={self.user_id!s}>"


# ── Rooms ──────────────────────────────────────────────────────
class RoomModel(Base):
    """Chat room (public, private, or direct message)."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            f"type IN ('{RoomType.PUBLIC}', '{RoomType.PRIVATE}', '{RoomType.DIRECT}')",
            name="valid_room_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Room identifier.",
    )
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Human-readable room name (null for DMs).",
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Room type: public | private | direct.",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created the room.",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional room description.",
    )
    max_members: Mapped[int] = mapped_column(
        Integer,
        default=500,
        server_default="500",
        nullable=False,
        comment="Maximum number of room members.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Soft-delete flag.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Room creation timestamp.",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp.",
    )

    # ── Relationships ──
    creator: Mapped[UserModel | None] = relationship(
        "UserModel",
        foreign_keys=[created_by],
        lazy="noload",
    )
    members: Mapped[list[RoomMemberModel]] = relationship(
        "RoomMemberModel",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    messages: Mapped[list[MessageModel]] = relationship(
        "MessageModel",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<RoomModel id={self.id!s} name={self.name!r} type={self.type!r}>"


# ── Room Members ───────────────────────────────────────────────
class RoomMemberModel(Base):
    """Many-to-many association between rooms and users with role metadata."""

    __tablename__ = "room_members"

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Room FK.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="User FK.",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=RoomRole.MEMBER,
        server_default=RoomRole.MEMBER,
        nullable=False,
        comment="Member role: owner | admin | member.",
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when user joined the room.",
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last message timestamp the user has read up to.",
    )
    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether the user has muted this room.",
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Whether push notifications are enabled.",
    )

    # ── Relationships ──
    room: Mapped[RoomModel] = relationship(
        "RoomModel",
        back_populates="members",
    )
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="room_memberships",
    )

    def __repr__(self) -> str:
        return (
            f"<RoomMemberModel room_id={self.room_id!s} "
            f"user_id={self.user_id!s} role={self.role!r}>"
        )


# ── Messages ──────────────────────────────────────────────────
class MessageModel(Base):
    """Individual chat message within a room."""

    __tablename__ = "messages"
    __table_args__ = (
        # Composite index for paginated room timeline queries
        Index(
            "ix_messages_room_id_created_at",
            "room_id",
            "created_at",
            postgresql_using="btree",
        ),
        # GIN index for PostgreSQL full-text search on content
        Index(
            "ix_messages_content_fts",
            func.to_tsvector("english", "content"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing message ID (BigInt for scale).",
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Room this message belongs to.",
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who sent the message.",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Plaintext message body.",
    )
    encrypted_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="E2E-encrypted message payload.",
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        default=MessageType.TEXT,
        server_default=MessageType.TEXT,
        nullable=False,
        comment="Message type: text | image | file | system.",
    )
    reply_to: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent message ID for threaded replies.",
    )
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether the message has been edited.",
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last edit.",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Soft-delete flag.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of deletion.",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="Arbitrary JSON metadata (attachments, link previews, etc.).",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Message creation timestamp.",
    )

    # ── Relationships ──
    room: Mapped[RoomModel] = relationship(
        "RoomModel",
        back_populates="messages",
    )
    sender: Mapped[UserModel | None] = relationship(
        "UserModel",
        back_populates="sent_messages",
    )
    parent_message: Mapped[MessageModel | None] = relationship(
        "MessageModel",
        remote_side=[id],
        lazy="noload",
    )
    deliveries: Mapped[list[MessageDeliveryModel]] = relationship(
        "MessageDeliveryModel",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<MessageModel id={self.id} room_id={self.room_id!s} "
            f"type={self.message_type!r}>"
        )


# ── Message Deliveries ────────────────────────────────────────
class MessageDeliveryModel(Base):
    """Per-user delivery tracking for a message."""

    __tablename__ = "message_deliveries"
    __table_args__ = (
        Index("ix_message_deliveries_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Delivery record identifier.",
    )
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        comment="Delivered message FK.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Recipient user FK.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING,
        nullable=False,
        comment="Delivery status: pending | delivered | read | failed.",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="Number of delivery retry attempts.",
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when message was delivered.",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when message was read.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp.",
    )

    # ── Relationships ──
    message: Mapped[MessageModel] = relationship(
        "MessageModel",
        back_populates="deliveries",
    )
    user: Mapped[UserModel] = relationship("UserModel", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<MessageDeliveryModel id={self.id!s} "
            f"message_id={self.message_id} status={self.status!r}>"
        )


# ── Offline Messages ──────────────────────────────────────────
class OfflineMessageModel(Base):
    """Queued message for a user who was offline at send time."""

    __tablename__ = "offline_messages"
    __table_args__ = (
        Index("ix_offline_messages_status_next_retry", "status", "next_retry_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Offline queue entry identifier.",
    )
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        comment="Queued message FK.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Recipient user FK.",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="Delivery retry attempts so far.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=OfflineMessageStatus.PENDING,
        server_default=OfflineMessageStatus.PENDING,
        nullable=False,
        comment="Queue status: pending | processing | delivered | dead_letter.",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Scheduled next retry timestamp.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp.",
    )

    # ── Relationships ──
    message: Mapped[MessageModel] = relationship("MessageModel", lazy="joined")
    user: Mapped[UserModel] = relationship("UserModel", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<OfflineMessageModel id={self.id!s} "
            f"user_id={self.user_id!s} status={self.status!r}>"
        )


# ── Notifications ─────────────────────────────────────────────
class NotificationModel(Base):
    """Push / in-app notification for a user."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Notification identifier.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Recipient user FK.",
    )
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Notification type: message | mention | room_invite | system.",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Arbitrary notification payload.",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether the user has seen this notification.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Notification creation timestamp.",
    )

    # ── Relationships ──
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="notifications",
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationModel id={self.id!s} "
            f"user_id={self.user_id!s} type={self.type!r}>"
        )
