"""
Notification entity.

Represents a push-style notification delivered to a user (e.g.
new message alerts, room invitations, system announcements).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.shared.constants import NotificationType
from src.shared.utils import generate_id, utc_now


@dataclass
class Notification:
    """A notification destined for a specific user.

    Attributes:
        id: Unique notification identifier (UUID v4).
        user_id: The recipient user.
        type: Category of the notification.
        payload: Arbitrary JSON-safe data describing the notification.
        is_read: Whether the user has acknowledged the notification.
        created_at: When the notification was created.
    """

    user_id: uuid.UUID
    type: NotificationType
    payload: dict[str, Any] = field(default_factory=dict)
    id: uuid.UUID | None = None
    is_read: bool = False
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Assign defaults for auto-generated fields."""
        if self.id is None:
            self.id = generate_id()
        if self.created_at is None:
            self.created_at = utc_now()
