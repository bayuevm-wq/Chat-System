"""
User entity.

Represents an authenticated user of the distributed chat system,
including profile information, presence state, and optional E2E
encryption public key.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.shared.constants import UserStatus
from src.shared.utils import generate_id, utc_now


@dataclass
class User:
    """A registered user in the chat system.

    Attributes:
        id: Unique identifier (UUID v4). Assigned on creation if *None*.
        username: Unique login handle.
        email: Unique email address.
        display_name: Optional human-friendly display name.
        password_hash: Hashed password (never stored in plain text).
        avatar_url: URL to the user's profile picture.
        status: Current presence status.
        public_key: Optional public key for end-to-end encryption.
        is_active: Whether the account is enabled.
        last_seen_at: Timestamp of the user's last activity.
        created_at: When the entity was created.
        updated_at: When the entity was last modified.
    """

    username: str
    email: str
    password_hash: str
    id: uuid.UUID | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: UserStatus = UserStatus.OFFLINE
    public_key: str | None = None
    is_active: bool = True
    last_seen_at: datetime | None = None
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

    # ── helpers ──────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize the user to a plain dictionary.

        Sensitive fields (``password_hash``) are deliberately excluded.

        Returns:
            A JSON-safe dictionary of public user data.
        """
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "status": str(self.status),
            "public_key": self.public_key,
            "is_active": self.is_active,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
