"""UserPresence value object — aggregated presence state for a user."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from src.shared.constants import UserStatus


@dataclass(frozen=True, slots=True)
class UserPresence:
    """Immutable snapshot of a user's presence state.

    Aggregates presence across multiple devices/sessions.
    """

    user_id: uuid.UUID
    status: UserStatus = UserStatus.OFFLINE
    last_seen_at: datetime | None = None
    active_sessions: int = field(default=0)

    def is_online(self) -> bool:
        """Check if the user has at least one active session."""
        return self.status in (UserStatus.ONLINE, UserStatus.AWAY, UserStatus.BUSY)

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize to dictionary for API responses."""
        return {
            "user_id": str(self.user_id),
            "status": self.status.value,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "active_sessions": self.active_sessions,
        }
