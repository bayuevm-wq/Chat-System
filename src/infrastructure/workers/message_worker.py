"""
Offline message delivery worker.

Processes the offline message queue using Redis Streams, attempting to
deliver messages to users when they come online. Implements exponential
backoff retry with dead-letter queue escalation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import get_settings
from src.shared.constants import RedisPrefix, WSEventType

logger = logging.getLogger(__name__)


class OfflineMessageWorker:
    """Processes offline messages from Redis Streams with retry logic."""

    def __init__(
        self,
        stream_processor: Any,
        connection_manager: Any,
        cache_service: Any,
    ) -> None:
        self._stream = stream_processor
        self._manager = connection_manager
        self._cache = cache_service
        self._running = False
        self._task: asyncio.Task[None] | None = None

        settings = get_settings()
        self._max_retries = settings.OFFLINE_MESSAGE_MAX_RETRIES
        self._base_delay = settings.OFFLINE_MESSAGE_RETRY_BASE_DELAY

    async def start(self) -> None:
        """Start the offline message processing loop."""
        self._running = True
        await self._stream.ensure_group(RedisPrefix.STREAM_OFFLINE)
        self._task = asyncio.create_task(
            self._processing_loop(), name="offline-message-worker"
        )
        logger.info("Offline message worker started")

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Offline message worker stopped")

    async def _processing_loop(self) -> None:
        """Main processing loop — dequeue and attempt delivery."""
        while self._running:
            try:
                messages = await self._stream.dequeue(
                    RedisPrefix.STREAM_OFFLINE, count=10, block_ms=5000
                )
                for msg_id, data in messages:
                    await self._process_message(msg_id, data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker loop error", extra={"error": str(e)})
                await asyncio.sleep(5)

    async def _process_message(
        self, message_id: str, data: dict[str, Any]
    ) -> None:
        """Attempt to deliver a single offline message.

        If the user is online, send via WebSocket and acknowledge.
        If still offline, check retry count and either re-enqueue
        with backoff or move to the dead letter queue.
        """
        user_id = data.get("user_id", "")
        message_data = data.get("message_data", {})
        retry_count = int(data.get("retry_count", 0))

        # Check if user is now online on this node
        if self._manager.is_user_connected(user_id):
            try:
                await self._manager.send_to_user(user_id, {
                    "type": WSEventType.MESSAGE_NEW,
                    **message_data,
                })
                await self._stream.acknowledge(RedisPrefix.STREAM_OFFLINE, message_id)
                logger.debug("Offline message delivered", extra={"user_id": user_id})
                return
            except Exception as e:
                logger.warning("Delivery failed", extra={"user_id": user_id, "error": str(e)})

        # User still offline — retry or dead-letter
        if retry_count >= self._max_retries:
            await self._stream.move_to_dead_letter(
                RedisPrefix.STREAM_OFFLINE, message_id, data
            )
            logger.warning(
                "Message moved to dead letter queue",
                extra={"user_id": user_id, "retries": retry_count},
            )
        else:
            # Re-enqueue with incremented retry count and backoff delay
            delay = self._base_delay * (2 ** retry_count)
            await asyncio.sleep(min(delay, 300))  # Cap at 5 minutes
            data["retry_count"] = retry_count + 1
            await self._stream.enqueue(RedisPrefix.STREAM_OFFLINE, data)
            await self._stream.acknowledge(RedisPrefix.STREAM_OFFLINE, message_id)
