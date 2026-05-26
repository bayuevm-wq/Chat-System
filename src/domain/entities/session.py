"""
UserSession entity.

Tracks an authenticated session for a specific user on a specific
device, bound to a particular node in the distributed cluster.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.shared.utils import generate_id, utc_now


@dataclass
class UserSession:
    """An active authenticated session.

    Attributes:
        id: Unique session identifier (UUID v4).
        user_id: The user this session belongs to.
        device_id: Client-supplied device fingerprint.
        node_id: The cluster node currently handling this session.
        token_hash: SHA-256 hash of the session token.
        ip_address: Client IP address at session creation time.
        expires_at: When the session token expires.
        created_at: When the session was created.
    """

    user_id: uuid.UUID
    device_id: str
    node_id: str
    token_hash: str
    expires_at: datetime
    id: uuid.UUID | None = None
    ip_address: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Assign defaults for auto-generated fields."""
        if self.id is None:
            self.id = generate_id()
        if self.created_at is None:
            self.created_at = utc_now()

    # ── helpers ──────────────────────────────────────────────────

    def is_expired(self) -> bool:
        """Check whether the session has passed its expiry time.

        Returns:
            *True* if the current UTC time is past ``expires_at``.
        """
        return utc_now() >= self.expires_at
