"""
Notification service.

Manages push notification simulation — queuing notifications for offline
users, dispatching notification events via streams.
"""

from __future__ import annotations

import logging
from typing import Any

from src.shared.constants import RedisPrefix

logger = logging.getLogger(__name__)


class NotificationService:
    """Queues and dispatches notification events."""

    def __init__(self, stream_processor: Any, cache_service: Any) -> None:
        self._stream = stream_processor
        self._cache = cache_service

    async def send_notification(
        self, user_id: str, notif_type: str, payload: dict[str, Any]
    ) -> None:
        """Enqueue a notification to the notification stream.

        Args:
            user_id: Target user's UUID string.
            notif_type: Notification type (message, mention, room_invite, system).
            payload: Notification payload data.
        """
        await self._stream.enqueue(
            RedisPrefix.STREAM_NOTIFICATIONS,
            {
                "user_id": user_id,
                "type": notif_type,
                "payload": payload,
            },
        )
        logger.debug("Notification queued", extra={"user_id": user_id, "type": notif_type})

    async def notify_offline_user(
        self, user_id: str, message_data: dict[str, Any]
    ) -> None:
        """Queue a message notification for an offline user.

        Args:
            user_id: Offline user's UUID string.
            message_data: Message details to include in notification.
        """
        await self._stream.enqueue(
            RedisPrefix.STREAM_OFFLINE,
            {
                "user_id": user_id,
                "message_data": message_data,
            },
        )
        logger.debug("Offline notification queued", extra={"user_id": user_id})

    async def get_pending_notifications(self, user_id: str) -> list[dict[str, Any]]:
        """Get pending notifications count/list for a user (from cache/stream).

        Args:
            user_id: User's UUID string.

        Returns:
            List of pending notification dicts.
        """
        # In a full implementation, this would read from the notification stream
        # For now, return empty — notifications are pushed via WebSocket
        return []
