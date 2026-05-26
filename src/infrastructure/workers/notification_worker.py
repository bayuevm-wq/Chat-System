"""
Notification worker.

Processes queued notifications from Redis Streams and delivers them
to online users via WebSocket, or logs them for push delivery.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.shared.constants import RedisPrefix, WSEventType

logger = logging.getLogger(__name__)


class NotificationWorker:
    """Processes notification events from Redis Streams."""

    def __init__(
        self, stream_processor: Any, connection_manager: Any
    ) -> None:
        self._stream = stream_processor
        self._manager = connection_manager
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the notification processing loop."""
        self._running = True
        await self._stream.ensure_group(RedisPrefix.STREAM_NOTIFICATIONS)
        self._task = asyncio.create_task(
            self._processing_loop(), name="notification-worker"
        )
        logger.info("Notification worker started")

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification worker stopped")

    async def _processing_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                messages = await self._stream.dequeue(
                    RedisPrefix.STREAM_NOTIFICATIONS, count=50, block_ms=5000
                )
                for msg_id, data in messages:
                    await self._process_notification(msg_id, data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Notification worker error", extra={"error": str(e)})
                await asyncio.sleep(5)

    async def _process_notification(
        self, message_id: str, data: dict[str, Any]
    ) -> None:
        """Process a single notification event."""
        user_id = data.get("user_id", "")
        notif_type = data.get("type", "system")
        payload = data.get("payload", {})

        if self._manager.is_user_connected(user_id):
            await self._manager.send_to_user(user_id, {
                "type": WSEventType.NOTIFICATION,
                "notification_type": notif_type,
                "payload": payload,
            })

        await self._stream.acknowledge(RedisPrefix.STREAM_NOTIFICATIONS, message_id)
        logger.debug("Notification processed", extra={"user_id": user_id, "type": notif_type})
