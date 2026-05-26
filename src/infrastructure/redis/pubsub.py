"""Hybrid Pub/Sub + Streams event bus for real-time messaging.

Implements a dual-write pattern: every chat message is persisted to a
Redis Stream (durability & history) **and** broadcast via Pub/Sub
(low-latency fan-out).  Presence and system events use Pub/Sub only.

Usage::

    from src.infrastructure.redis.client import get_redis_client
    from src.infrastructure.redis.pubsub import EventBus

    bus = EventBus(get_redis_client(), node_id="node-abc123")
    await bus.publish_message("room-1", {"text": "hello"})
    history = await bus.get_room_history("room-1", count=25)
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Coroutine

import orjson
import redis.asyncio as redis
import structlog

from src.infrastructure.redis.client import RedisClient
from src.shared.constants import MAX_STREAM_LENGTH, RedisPrefix
from src.shared.retry import async_retry

logger = structlog.get_logger(__name__)

# Type alias for subscription callbacks
MessageCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Hybrid Pub/Sub + Streams event bus.

    Args:
        redis_client: Connected :class:`RedisClient` instance.
        node_id: Unique identifier for this application node.
    """

    __slots__ = (
        "_redis",
        "_node_id",
        "_pubsubs",
        "_tasks",
        "_running",
    )

    def __init__(self, redis_client: RedisClient, node_id: str) -> None:
        self._redis = redis_client
        self._node_id = node_id
        self._pubsubs: list[redis.client.PubSub] = []
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    # ── Serialisation helpers ───────────────────────────────────

    @staticmethod
    def _serialize(data: dict[str, Any]) -> str:
        """Serialize a dict to a JSON string using orjson."""
        return orjson.dumps(data).decode("utf-8")

    @staticmethod
    def _deserialize(raw: str | bytes) -> dict[str, Any]:
        """Deserialize a JSON string/bytes back to a dict."""
        return orjson.loads(raw)

    def _add_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inject correlation_id and origin node into the payload."""
        enriched = dict(data)
        enriched.setdefault("correlation_id", uuid.uuid4().hex)
        enriched.setdefault("origin_node", self._node_id)
        return enriched

    # ── Publishing ──────────────────────────────────────────────

    @async_retry()
    async def publish_message(self, room_id: str, message: dict[str, Any]) -> None:
        """Dual-write a chat message to Stream + Pub/Sub.

        1. ``XADD stream:chat:{room_id}`` for durability (trimmed).
        2. ``PUBLISH pubsub:chat:{room_id}`` for real-time delivery.

        Args:
            room_id: Target chat room identifier.
            message: Message payload dict.
        """
        enriched = self._add_metadata(message)
        stream_key = f"{RedisPrefix.STREAM_CHAT}{room_id}"
        channel = f"{RedisPrefix.PUBSUB_CHAT}{room_id}"
        payload = self._serialize(enriched)

        client = self._redis.client

        # Durable write — append to stream with auto-trim
        message_id: bytes | str = await client.xadd(
            stream_key,
            {"data": payload},
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )

        # Real-time broadcast
        await client.publish(channel, payload)

        logger.debug(
            "event_bus_message_published",
            room_id=room_id,
            stream_id=str(message_id),
            correlation_id=enriched.get("correlation_id"),
        )

    @async_retry()
    async def publish_presence(self, event: dict[str, Any]) -> None:
        """Publish a presence event to the global presence channel.

        Args:
            event: Presence event payload.
        """
        enriched = self._add_metadata(event)
        await self._redis.client.publish(
            RedisPrefix.PUBSUB_PRESENCE,
            self._serialize(enriched),
        )
        logger.debug("event_bus_presence_published", event_type=event.get("type"))

    @async_retry()
    async def publish_system(self, event: dict[str, Any]) -> None:
        """Publish a system-wide broadcast event.

        Args:
            event: System event payload.
        """
        enriched = self._add_metadata(event)
        await self._redis.client.publish(
            RedisPrefix.PUBSUB_SYSTEM,
            self._serialize(enriched),
        )
        logger.debug("event_bus_system_published", event_type=event.get("type"))

    @async_retry()
    async def publish_to_node(self, node_id: str, event: dict[str, Any]) -> None:
        """Send an event directly to a specific node.

        Args:
            node_id: Destination node identifier.
            event: Event payload.
        """
        enriched = self._add_metadata(event)
        channel = f"{RedisPrefix.PUBSUB_NODE}{node_id}"
        await self._redis.client.publish(channel, self._serialize(enriched))
        logger.debug("event_bus_node_published", target_node=node_id)

    # ── Subscribing ─────────────────────────────────────────────

    async def _listen_loop(
        self,
        pubsub: redis.client.PubSub,
        callback: MessageCallback,
        label: str,
    ) -> None:
        """Internal loop that reads messages from a PubSub and invokes *callback*.

        Runs until :attr:`_running` is set to ``False`` or the task is cancelled.
        """
        logger.info("event_bus_listener_started", label=label)
        try:
            while self._running:
                try:
                    raw_msg = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    if raw_msg is None:
                        continue
                    data = self._deserialize(raw_msg["data"])
                    await callback(data)
                except asyncio.CancelledError:
                    raise
                except orjson.JSONDecodeError:
                    logger.warning("event_bus_invalid_json", label=label, raw=raw_msg)
                except Exception:
                    logger.exception("event_bus_listener_error", label=label)
                    await asyncio.sleep(0.5)
        finally:
            logger.info("event_bus_listener_stopped", label=label)

    async def subscribe_room(
        self, room_id: str, callback: MessageCallback
    ) -> asyncio.Task[None]:
        """Subscribe to a single room's Pub/Sub channel.

        Args:
            room_id: Room to subscribe to.
            callback: Async function invoked with each message dict.

        Returns:
            The background ``asyncio.Task`` running the listener.
        """
        channel = f"{RedisPrefix.PUBSUB_CHAT}{room_id}"
        pubsub = await self._redis.subscribe(channel)
        self._pubsubs.append(pubsub)
        task = asyncio.create_task(
            self._listen_loop(pubsub, callback, f"room:{room_id}"),
        )
        self._tasks.append(task)
        return task

    async def subscribe_presence(self, callback: MessageCallback) -> asyncio.Task[None]:
        """Subscribe to the global presence channel.

        Args:
            callback: Async function invoked with each presence event.

        Returns:
            The background ``asyncio.Task``.
        """
        pubsub = await self._redis.subscribe(RedisPrefix.PUBSUB_PRESENCE)
        self._pubsubs.append(pubsub)
        task = asyncio.create_task(
            self._listen_loop(pubsub, callback, "presence"),
        )
        self._tasks.append(task)
        return task

    async def subscribe_node(
        self, node_id: str, callback: MessageCallback
    ) -> asyncio.Task[None]:
        """Subscribe to a node-specific channel.

        Args:
            node_id: Node whose channel to subscribe to.
            callback: Async function invoked with each event.

        Returns:
            The background ``asyncio.Task``.
        """
        channel = f"{RedisPrefix.PUBSUB_NODE}{node_id}"
        pubsub = await self._redis.subscribe(channel)
        self._pubsubs.append(pubsub)
        task = asyncio.create_task(
            self._listen_loop(pubsub, callback, f"node:{node_id}"),
        )
        self._tasks.append(task)
        return task

    # ── Batch startup ───────────────────────────────────────────

    async def start_subscriptions(
        self,
        room_ids: list[str],
        message_callback: MessageCallback,
        presence_callback: MessageCallback,
        node_callback: MessageCallback,
    ) -> None:
        """Start all subscription loops as background tasks.

        Subscribes to every room in *room_ids*, the presence channel,
        and this node's direct channel.

        Args:
            room_ids: Rooms to subscribe to.
            message_callback: Handler for room messages.
            presence_callback: Handler for presence events.
            node_callback: Handler for node-directed events.
        """
        self._running = True
        for room_id in room_ids:
            await self.subscribe_room(room_id, message_callback)
        await self.subscribe_presence(presence_callback)
        await self.subscribe_node(self._node_id, node_callback)
        logger.info(
            "event_bus_subscriptions_started",
            rooms=len(room_ids),
            node_id=self._node_id,
        )

    # ── Stream history ──────────────────────────────────────────

    @async_retry()
    async def get_room_history(
        self, room_id: str, count: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve recent messages from a room's stream.

        Uses ``XREVRANGE`` so the newest messages come first, then
        reverses the result for chronological order.

        Args:
            room_id: Room to query.
            count: Maximum number of messages to return.

        Returns:
            List of message dicts in chronological order.
        """
        stream_key = f"{RedisPrefix.STREAM_CHAT}{room_id}"
        entries: list[tuple[str, dict[str, str]]] = await self._redis.client.xrevrange(
            stream_key, count=count,
        )

        messages: list[dict[str, Any]] = []
        for entry_id, fields in reversed(entries):
            try:
                payload = self._deserialize(fields["data"])
                payload["stream_id"] = entry_id
                messages.append(payload)
            except (KeyError, orjson.JSONDecodeError):
                logger.warning(
                    "event_bus_invalid_stream_entry",
                    stream=stream_key,
                    entry_id=entry_id,
                )
        return messages

    # ── Shutdown ────────────────────────────────────────────────

    async def stop(self) -> None:
        """Cancel all subscription tasks and unsubscribe."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        for pubsub in self._pubsubs:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:
                logger.warning("event_bus_pubsub_close_error", exc_info=True)
        self._pubsubs.clear()

        logger.info("event_bus_stopped", node_id=self._node_id)
