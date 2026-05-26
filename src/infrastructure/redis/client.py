"""Redis client with async connection pooling and health checks.

Manages a singleton :class:`RedisClient` backed by ``redis.asyncio``
with connection pooling, structured logging, and built-in retry on
publish operations.

Usage::

    from src.infrastructure.redis.client import get_redis_client

    client = get_redis_client()
    await client.connect()
    ok = await client.ping()
    await client.publish("channel", '{"msg": "hi"}')
    await client.disconnect()
"""

from __future__ import annotations

import redis.asyncio as redis
import structlog

from src.config import get_settings
from src.shared.retry import async_retry

logger = structlog.get_logger(__name__)


class RedisClient:
    """Async Redis client with managed connection pool.

    Args:
        url: Redis connection URL (e.g. ``redis://localhost:6379/0``).
        max_connections: Maximum pool size.
    """

    __slots__ = ("_url", "_max_connections", "_pool", "_client")

    def __init__(self, url: str, max_connections: int = 20) -> None:
        self._url = url
        self._max_connections = max_connections
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    # ── Lifecycle ───────────────────────────────────────────────

    async def connect(self) -> None:
        """Create the connection pool and underlying Redis client.

        Raises:
            redis.ConnectionError: If the initial connection fails.
        """
        if self._client is not None:
            logger.debug("redis_already_connected", url=self._url)
            return

        settings = get_settings()
        self._pool = redis.ConnectionPool.from_url(
            self._url,
            max_connections=self._max_connections,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            decode_responses=True,
        )
        self._client = redis.Redis.from_pool(self._pool)

        # Validate connectivity
        await self._client.ping()
        logger.info(
            "redis_connected",
            url=self._url,
            max_connections=self._max_connections,
        )

    async def disconnect(self) -> None:
        """Gracefully close the Redis client and connection pool."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                logger.warning("redis_close_error", exc_info=True)
            finally:
                self._client = None
                self._pool = None
                logger.info("redis_disconnected", url=self._url)

    # ── Health ──────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Check whether the Redis server is reachable.

        Returns:
            ``True`` if the server responds to ``PING``, ``False`` otherwise.
        """
        try:
            if self._client is None:
                return False
            return bool(await self._client.ping())
        except (redis.ConnectionError, redis.TimeoutError, OSError):
            logger.warning("redis_ping_failed", exc_info=True)
            return False

    # ── Client accessor ─────────────────────────────────────────

    @property
    def client(self) -> redis.Redis:
        """Return the underlying ``redis.Redis`` instance.

        Raises:
            RuntimeError: If :meth:`connect` has not been called yet.
        """
        if self._client is None:
            raise RuntimeError(
                "RedisClient is not connected. Call `await connect()` first."
            )
        return self._client

    # ── Pub/Sub helpers ─────────────────────────────────────────

    @async_retry()
    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a Redis Pub/Sub channel with retry.

        Args:
            channel: Channel name to publish on.
            message: Serialised message payload.

        Returns:
            Number of subscribers that received the message.
        """
        result: int = await self.client.publish(channel, message)
        logger.debug("redis_publish", channel=channel, receivers=result)
        return result

    async def subscribe(self, channel: str) -> redis.client.PubSub:
        """Create and return a PubSub instance subscribed to *channel*.

        Args:
            channel: Channel to subscribe to.

        Returns:
            A ``PubSub`` instance already subscribed to the channel.
        """
        pubsub: redis.client.PubSub = self.client.pubsub()
        await pubsub.subscribe(channel)
        logger.debug("redis_subscribed", channel=channel)
        return pubsub


# ── Module-level singleton ──────────────────────────────────────
_instance: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """Return the module-level :class:`RedisClient` singleton.

    The instance is lazily created using application settings. Call
    ``await get_redis_client().connect()`` during application startup.

    Returns:
        The shared ``RedisClient`` instance.
    """
    global _instance  # noqa: PLW0603
    if _instance is None:
        settings = get_settings()
        _instance = RedisClient(
            url=settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
    return _instance
