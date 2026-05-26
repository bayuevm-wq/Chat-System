"""
Presence service.

Manages online/offline detection, heartbeat, user status updates,
and typing indicators using Redis TTL-based presence tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from src.shared.constants import PRESENCE_TTL_SECONDS, TYPING_TTL_SECONDS, UserStatus, WSEventType
from src.shared.utils import utc_now

logger = logging.getLogger(__name__)


class PresenceService:
    """Manages user presence state across the distributed cluster."""

    def __init__(
        self,
        cache_service: Any,
        event_bus: Any,
        user_repo: Any,
    ) -> None:
        self._cache = cache_service
        self._event_bus = event_bus
        self._user_repo = user_repo

    async def set_online(
        self, user_id: str, node_id: str, device_id: str
    ) -> None:
        """Mark a user as online and broadcast presence change.

        Args:
            user_id: User's UUID string.
            node_id: The server node handling this connection.
            device_id: Client device identifier.
        """
        await self._cache.set_presence(
            user_id, UserStatus.ONLINE, ttl=PRESENCE_TTL_SECONDS
        )
        await self._event_bus.publish_presence({
            "type": WSEventType.PRESENCE_CHANGE,
            "user_id": user_id,
            "status": UserStatus.ONLINE,
            "node_id": node_id,
            "device_id": device_id,
        })
        logger.info("User online", extra={"user_id": user_id, "node_id": node_id})

    async def set_offline(self, user_id: str) -> None:
        """Mark a user as offline and record last-seen timestamp.

        Args:
            user_id: User's UUID string.
        """
        now = utc_now()
        await self._cache.remove_presence(user_id)

        try:
            from uuid import UUID
            await self._user_repo.update_last_seen(UUID(user_id), now)
        except Exception:
            logger.warning("Failed to update last_seen", extra={"user_id": user_id})

        await self._event_bus.publish_presence({
            "type": WSEventType.PRESENCE_CHANGE,
            "user_id": user_id,
            "status": UserStatus.OFFLINE,
            "last_seen_at": now.isoformat(),
        })
        logger.info("User offline", extra={"user_id": user_id})

    async def heartbeat(self, user_id: str) -> None:
        """Refresh the user's presence TTL (keepalive).

        Args:
            user_id: User's UUID string.
        """
        await self._cache.heartbeat(user_id, ttl=PRESENCE_TTL_SECONDS)

    async def update_status(self, user_id: str, status: UserStatus) -> None:
        """Update a user's status (online/away/busy).

        Args:
            user_id: User's UUID string.
            status: New user status.
        """
        old_status = await self._cache.get_presence(user_id)
        await self._cache.set_presence(user_id, status, ttl=PRESENCE_TTL_SECONDS)

        await self._event_bus.publish_presence({
            "type": WSEventType.PRESENCE_CHANGE,
            "user_id": user_id,
            "status": status,
            "old_status": old_status or UserStatus.OFFLINE,
        })

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Get a user's current presence status.

        Args:
            user_id: User's UUID string.

        Returns:
            Dict with status and last_seen timestamp.
        """
        status = await self._cache.get_presence(user_id)
        last_seen = None
        if not status or status == UserStatus.OFFLINE:
            try:
                from uuid import UUID
                user = await self._user_repo.get_by_id(UUID(user_id))
                if user and user.last_seen_at:
                    last_seen = user.last_seen_at.isoformat()
            except Exception:
                pass

        return {
            "user_id": user_id,
            "status": status or UserStatus.OFFLINE,
            "last_seen_at": last_seen,
        }

    async def get_online_users(self, user_ids: list[str]) -> list[str]:
        """Check which users from a list are currently online.

        Args:
            user_ids: List of user UUID strings.

        Returns:
            List of user IDs that are currently online.
        """
        return await self._cache.get_online_users(user_ids)

    async def set_typing(
        self, user_id: str, room_id: str, is_typing: bool
    ) -> None:
        """Set or clear a typing indicator for a user in a room.

        Args:
            user_id: User's UUID string.
            room_id: Room UUID string.
            is_typing: Whether the user is currently typing.
        """
        if is_typing:
            await self._cache.set_typing(user_id, room_id, ttl=TYPING_TTL_SECONDS)
        # Typing indicators auto-expire via TTL; no explicit "stop" needed

        await self._event_bus.publish_message(room_id, {
            "type": WSEventType.TYPING_INDICATOR,
            "room_id": room_id,
            "user_id": user_id,
            "is_typing": is_typing,
        })
