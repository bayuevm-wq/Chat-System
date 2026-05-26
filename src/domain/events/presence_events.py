"""
Presence-related domain events.

Events emitted when users come online, go offline, change status,
or send heartbeat pings to maintain their presence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.events.base import DomainEvent


@dataclass
class UserOnlineEvent(DomainEvent):
    """Raised when a user establishes a new active connection.

    Attributes:
        user_id: UUID string of the user who came online.
        node_id: The cluster node handling the connection.
        device_id: Client device fingerprint.
    """

    user_id: str | None = None
    node_id: str | None = None
    device_id: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        node_id: str,
        device_id: str,
        *,
        source_node: str | None = None,
    ) -> UserOnlineEvent:
        """Build a ``UserOnlineEvent`` with the correct event_type.

        Args:
            user_id: UUID string of the user.
            node_id: Cluster node identifier.
            device_id: Client device identifier.
            source_node: Optional originating node.

        Returns:
            A fully populated ``UserOnlineEvent``.
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "node_id": node_id,
            "device_id": device_id,
        }
        return cls(
            event_type="presence.online",
            payload=payload,
            source_node=source_node,
            user_id=user_id,
            node_id=node_id,
            device_id=device_id,
        )


@dataclass
class UserOfflineEvent(DomainEvent):
    """Raised when a user disconnects or their session expires.

    Attributes:
        user_id: UUID string of the user who went offline.
        last_seen_at: ISO 8601 timestamp of the user's last activity.
    """

    user_id: str | None = None
    last_seen_at: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        last_seen_at: str,
        *,
        source_node: str | None = None,
    ) -> UserOfflineEvent:
        """Build a ``UserOfflineEvent`` with the correct event_type.

        Args:
            user_id: UUID string of the user.
            last_seen_at: ISO 8601 timestamp.
            source_node: Optional originating node.

        Returns:
            A fully populated ``UserOfflineEvent``.
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "last_seen_at": last_seen_at,
        }
        return cls(
            event_type="presence.offline",
            payload=payload,
            source_node=source_node,
            user_id=user_id,
            last_seen_at=last_seen_at,
        )


@dataclass
class UserStatusChangedEvent(DomainEvent):
    """Raised when a user explicitly changes their presence status.

    Attributes:
        user_id: UUID string of the user.
        old_status: Previous status value.
        new_status: Updated status value.
    """

    user_id: str | None = None
    old_status: str | None = None
    new_status: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        old_status: str,
        new_status: str,
        *,
        source_node: str | None = None,
    ) -> UserStatusChangedEvent:
        """Build a ``UserStatusChangedEvent`` with the correct event_type.

        Args:
            user_id: UUID string of the user.
            old_status: The previous status string.
            new_status: The new status string.
            source_node: Optional originating node.

        Returns:
            A fully populated ``UserStatusChangedEvent``.
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "old_status": old_status,
            "new_status": new_status,
        }
        return cls(
            event_type="presence.status_changed",
            payload=payload,
            source_node=source_node,
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
        )


@dataclass
class HeartbeatEvent(DomainEvent):
    """Periodic heartbeat from a user to maintain presence.

    Attributes:
        user_id: UUID string of the user.
        node_id: Cluster node the heartbeat originated from.
    """

    user_id: str | None = None
    node_id: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        node_id: str,
        *,
        source_node: str | None = None,
    ) -> HeartbeatEvent:
        """Build a ``HeartbeatEvent`` with the correct event_type.

        Args:
            user_id: UUID string of the user.
            node_id: Cluster node identifier.
            source_node: Optional originating node.

        Returns:
            A fully populated ``HeartbeatEvent``.
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "node_id": node_id,
        }
        return cls(
            event_type="presence.heartbeat",
            payload=payload,
            source_node=source_node,
            user_id=user_id,
            node_id=node_id,
        )
