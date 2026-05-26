"""
Dead letter queue processor.

Handles messages that have exceeded their retry limits, providing
logging for manual review and optional manual retry capability.
"""

from __future__ import annotations

import logging
from typing import Any

from src.shared.constants import RedisPrefix

logger = logging.getLogger(__name__)


class DeadLetterProcessor:
    """Processes and monitors the dead letter queue."""

    def __init__(self, stream_processor: Any) -> None:
        self._stream = stream_processor

    async def process_dead_letters(self) -> list[dict[str, Any]]:
        """Scan and log all messages in the dead letter queue.

        Returns:
            List of dead letter message dicts.
        """
        await self._stream.ensure_group(RedisPrefix.STREAM_DEAD_LETTER)
        messages = await self._stream.dequeue(
            RedisPrefix.STREAM_DEAD_LETTER, count=100, block_ms=1000
        )

        results = []
        for msg_id, data in messages:
            logger.warning(
                "Dead letter message",
                extra={"message_id": msg_id, "data": data},
            )
            results.append({"id": msg_id, **data})
            await self._stream.acknowledge(RedisPrefix.STREAM_DEAD_LETTER, msg_id)

        return results

    async def retry_dead_letter(
        self, message_id: str, data: dict[str, Any]
    ) -> None:
        """Manually retry a dead letter message by re-enqueuing it.

        Args:
            message_id: The dead letter message ID.
            data: The message data to re-enqueue.
        """
        data["retry_count"] = 0  # Reset retry count
        await self._stream.enqueue(RedisPrefix.STREAM_OFFLINE, data)
        logger.info("Dead letter retried", extra={"message_id": message_id})
