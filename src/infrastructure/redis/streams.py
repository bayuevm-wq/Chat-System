"""Redis Streams queue processor with consumer groups and dead-letter support.

Provides a :class:`StreamProcessor` that wraps Redis consumer-group
semantics (``XGROUP``, ``XREADGROUP``, ``XACK``, ``XPENDING``) for
reliable, at-least-once message processing with automatic dead-letter
routing for failed messages.

Usage::

    from src.infrastructure.redis.client import get_redis_client
    from src.infrastructure.redis.streams import StreamProcessor

    proc = StreamProcessor(
        redis_client=get_redis_client(),
        consumer_group="workers",
        consumer_name="worker-1",
    )
    await proc.ensure_group("stream:notifications")
    msg_id = await proc.enqueue("stream:notifications", {"type": "email"})

    async def handler(msg_id: str, data: dict) -> None:
        print(f"Processing {msg_id}: {data}")

    await proc.process_loop("stream:notifications", handler)
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

import orjson
import redis.asyncio as redis
import structlog

from src.infrastructure.redis.client import RedisClient
from src.shared.constants import MAX_STREAM_LENGTH, RedisPrefix
from src.shared.retry import async_retry

logger = structlog.get_logger(__name__)

# Type alias for the processing handler
StreamHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class StreamProcessor:
    """Redis Streams consumer-group processor.

    Args:
        redis_client: Connected :class:`RedisClient`.
        consumer_group: Name of the consumer group.
        consumer_name: Unique name for this consumer within the group.
    """

    __slots__ = (
        "_redis",
        "_group",
        "_consumer",
        "_running",
        "_processed_count",
        "_failed_count",
    )

    def __init__(
        self,
        redis_client: RedisClient,
        consumer_group: str,
        consumer_name: str,
    ) -> None:
        self._redis = redis_client
        self._group = consumer_group
        self._consumer = consumer_name
        self._running = False
        self._processed_count: int = 0
        self._failed_count: int = 0

    # ── Properties ──────────────────────────────────────────────

    @property
    def processed_count(self) -> int:
        """Total number of successfully processed messages."""
        return self._processed_count

    @property
    def failed_count(self) -> int:
        """Total number of failed messages."""
        return self._failed_count

    @property
    def _client(self) -> redis.Redis:
        return self._redis.client

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _encode(data: dict[str, Any]) -> str:
        return orjson.dumps(data).decode("utf-8")

    @staticmethod
    def _decode(raw: str | bytes) -> dict[str, Any]:
        return orjson.loads(raw)

    # ── Consumer group management ───────────────────────────────

    async def ensure_group(self, stream: str) -> None:
        """Create the consumer group for *stream* if it does not exist.

        Gracefully handles the ``BUSYGROUP`` error when the group has
        already been created by another process.

        Args:
            stream: Redis stream key.
        """
        try:
            await self._client.xgroup_create(
                stream, self._group, id="0", mkstream=True,
            )
            logger.info(
                "stream_group_created",
                stream=stream,
                group=self._group,
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug(
                    "stream_group_exists",
                    stream=stream,
                    group=self._group,
                )
            else:
                raise

    # ── Enqueue / Dequeue ───────────────────────────────────────

    @async_retry()
    async def enqueue(self, stream: str, data: dict[str, Any]) -> str:
        """Append a message to a stream (``XADD``).

        The stream is automatically trimmed to ``MAX_STREAM_LENGTH``
        entries (approximate).

        Args:
            stream: Target stream key.
            data: Payload to store.

        Returns:
            The auto-generated stream message ID.
        """
        message_id: bytes | str = await self._client.xadd(
            stream,
            {"data": self._encode(data)},
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )
        logger.debug("stream_enqueued", stream=stream, message_id=str(message_id))
        return str(message_id)

    @async_retry()
    async def dequeue(
        self,
        stream: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read new messages via ``XREADGROUP`` (blocking).

        Args:
            stream: Stream to read from.
            count: Maximum number of messages per read.
            block_ms: Milliseconds to block if no messages are available.

        Returns:
            List of ``(message_id, data_dict)`` tuples.
        """
        response = await self._client.xreadgroup(
            groupname=self._group,
            consumername=self._consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )

        if not response:
            return []

        messages: list[tuple[str, dict[str, Any]]] = []
        for _stream_name, entries in response:
            for entry_id, fields in entries:
                try:
                    data = self._decode(fields["data"])
                    messages.append((str(entry_id), data))
                except (KeyError, orjson.JSONDecodeError):
                    logger.warning(
                        "stream_invalid_entry",
                        stream=stream,
                        entry_id=str(entry_id),
                    )
        return messages

    # ── Acknowledgement ─────────────────────────────────────────

    @async_retry()
    async def acknowledge(self, stream: str, message_id: str) -> None:
        """Acknowledge a successfully processed message (``XACK``).

        Args:
            stream: Stream the message belongs to.
            message_id: ID of the message to acknowledge.
        """
        await self._client.xack(stream, self._group, message_id)

    # ── Pending inspection ──────────────────────────────────────

    @async_retry()
    async def get_pending(self, stream: str) -> list[dict[str, Any]]:
        """Return pending (un-ACKed) message summaries (``XPENDING``).

        Args:
            stream: Stream to inspect.

        Returns:
            List of pending message info dicts with keys:
            ``message_id``, ``consumer``, ``idle_ms``, ``delivery_count``.
        """
        info = await self._client.xpending_range(
            stream, self._group, min="-", max="+", count=100,
        )
        return [
            {
                "message_id": str(entry["message_id"]),
                "consumer": str(entry["consumer"]),
                "idle_ms": entry["time_since_delivered"],
                "delivery_count": entry["times_delivered"],
            }
            for entry in info
        ]

    # ── Dead-letter queue ───────────────────────────────────────

    @async_retry()
    async def move_to_dead_letter(
        self, stream: str, message_id: str, data: dict[str, Any]
    ) -> None:
        """Move a permanently failed message to the dead-letter stream.

        Writes the original payload (plus provenance metadata) to
        ``stream:dead_letter`` and acknowledges the source message.

        Args:
            stream: Original stream the message came from.
            message_id: Original message ID.
            data: Original message payload.
        """
        dlq_entry = {
            "original_stream": stream,
            "original_id": message_id,
            "data": self._encode(data),
        }
        await self._client.xadd(
            RedisPrefix.STREAM_DEAD_LETTER,
            dlq_entry,
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )
        await self._client.xack(stream, self._group, message_id)
        self._failed_count += 1
        logger.warning(
            "stream_dead_lettered",
            stream=stream,
            message_id=message_id,
        )

    # ── Continuous processing loop ──────────────────────────────

    async def process_loop(
        self,
        stream: str,
        handler: StreamHandler,
        *,
        batch_size: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Run a continuous read-process-ACK loop.

        For each message the *handler* is invoked.  If the handler
        raises an exception the message is retried up to *max_retries*
        times before being moved to the dead-letter queue.

        Args:
            stream: Stream to consume from.
            handler: Async callable ``(message_id, data) -> None``.
            batch_size: Messages to read per ``XREADGROUP`` call.
            max_retries: Max handler failures before dead-lettering.
        """
        self._running = True
        await self.ensure_group(stream)
        retry_counts: dict[str, int] = {}

        logger.info(
            "stream_processor_started",
            stream=stream,
            group=self._group,
            consumer=self._consumer,
        )

        try:
            while self._running:
                try:
                    messages = await self.dequeue(
                        stream, count=batch_size, block_ms=5000,
                    )
                except (redis.ConnectionError, redis.TimeoutError):
                    logger.warning("stream_processor_connection_error", exc_info=True)
                    await asyncio.sleep(1)
                    continue

                for msg_id, data in messages:
                    try:
                        await handler(msg_id, data)
                        await self.acknowledge(stream, msg_id)
                        self._processed_count += 1
                        retry_counts.pop(msg_id, None)
                    except Exception:
                        retries = retry_counts.get(msg_id, 0) + 1
                        retry_counts[msg_id] = retries
                        logger.exception(
                            "stream_handler_error",
                            stream=stream,
                            message_id=msg_id,
                            retry=retries,
                        )
                        if retries >= max_retries:
                            await self.move_to_dead_letter(stream, msg_id, data)
                            retry_counts.pop(msg_id, None)
        except asyncio.CancelledError:
            logger.info("stream_processor_cancelled", stream=stream)
        finally:
            self._running = False
            logger.info(
                "stream_processor_stopped",
                stream=stream,
                processed=self._processed_count,
                failed=self._failed_count,
            )

    # ── Lifecycle ───────────────────────────────────────────────

    def stop(self) -> None:
        """Signal the processing loop to stop after the current batch."""
        self._running = False
        logger.info(
            "stream_processor_stop_requested",
            group=self._group,
            consumer=self._consumer,
        )
