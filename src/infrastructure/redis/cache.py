"""Cache service for sessions, presence, typing, room members, and node registry.

All keys are namespaced via :class:`~src.shared.constants.RedisPrefix` to
prevent collisions.  Batch operations use Redis pipelines for efficiency.

Usage::

    from src.infrastructure.redis.client import get_redis_client
    from src.infrastructure.redis.cache import CacheService

    cache = CacheService(get_redis_client())
    await cache.store_session("sess-1", {"user_id": "u1"}, ttl=3600)
    await cache.set_presence("u1", "online")
"""

from __future__ import annotations

from typing import Any

import orjson
import redis.asyncio as redis
import structlog

from src.infrastructure.redis.client import RedisClient
from src.shared.constants import RedisPrefix
from src.shared.retry import async_retry

logger = structlog.get_logger(__name__)


class CacheService:
    """High-level cache operations backed by Redis.

    Args:
        redis_client: A connected :class:`RedisClient` instance.
    """

    __slots__ = ("_redis",)

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    # ── Helpers ─────────────────────────────────────────────────

    @property
    def _client(self) -> redis.Redis:
        return self._redis.client

    @staticmethod
    def _encode(data: dict[str, Any] | list[str]) -> str:
        """Serialize to JSON via orjson."""
        return orjson.dumps(data).decode("utf-8")

    @staticmethod
    def _decode(raw: str | bytes | None) -> Any:
        """Deserialize JSON; returns ``None`` on absent/invalid data."""
        if raw is None:
            return None
        return orjson.loads(raw)

    # ────────────────────────────────────────────────────────────
    # Session management
    # ────────────────────────────────────────────────────────────

    @async_retry()
    async def store_session(
        self, session_id: str, user_data: dict[str, Any], ttl: int
    ) -> None:
        """Persist a user session with a TTL.

        Args:
            session_id: Unique session identifier.
            user_data: Arbitrary user-associated data.
            ttl: Time-to-live in seconds.
        """
        key = f"{RedisPrefix.SESSION}{session_id}"
        await self._client.set(key, self._encode(user_data), ex=ttl)
        logger.debug("cache_session_stored", session_id=session_id, ttl=ttl)

    @async_retry()
    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID.

        Args:
            session_id: Session to look up.

        Returns:
            The stored session data, or ``None`` if expired / missing.
        """
        key = f"{RedisPrefix.SESSION}{session_id}"
        raw = await self._client.get(key)
        return self._decode(raw)

    @async_retry()
    async def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session to remove.
        """
        key = f"{RedisPrefix.SESSION}{session_id}"
        await self._client.delete(key)
        logger.debug("cache_session_deleted", session_id=session_id)

    # ────────────────────────────────────────────────────────────
    # Presence (TTL-based auto-expire)
    # ────────────────────────────────────────────────────────────

    @async_retry()
    async def set_presence(
        self, user_id: str, status: str, ttl: int = 60
    ) -> None:
        """Set a user's presence status with auto-expire.

        Args:
            user_id: User identifier.
            status: Presence status string (e.g. ``"online"``).
            ttl: Seconds before auto-expiry.
        """
        key = f"{RedisPrefix.PRESENCE}{user_id}"
        await self._client.set(key, status, ex=ttl)
        logger.debug("cache_presence_set", user_id=user_id, status=status)

    @async_retry()
    async def get_presence(self, user_id: str) -> str | None:
        """Retrieve a user's current presence status.

        Args:
            user_id: User to query.

        Returns:
            Status string or ``None`` if not present / expired.
        """
        key = f"{RedisPrefix.PRESENCE}{user_id}"
        return await self._client.get(key)

    @async_retry()
    async def heartbeat(self, user_id: str, ttl: int = 60) -> None:
        """Refresh the TTL on a user's presence key.

        Args:
            user_id: User whose presence to keep alive.
            ttl: New TTL in seconds.
        """
        key = f"{RedisPrefix.PRESENCE}{user_id}"
        await self._client.expire(key, ttl)

    @async_retry()
    async def get_online_users(self, user_ids: list[str]) -> list[str]:
        """Check which users from a list are currently online.

        Uses a Redis pipeline to batch ``EXISTS`` checks efficiently.

        Args:
            user_ids: List of user IDs to check.

        Returns:
            Subset of *user_ids* that have an active presence key.
        """
        if not user_ids:
            return []

        pipe = self._client.pipeline(transaction=False)
        keys = [f"{RedisPrefix.PRESENCE}{uid}" for uid in user_ids]
        for key in keys:
            pipe.exists(key)
        results: list[int] = await pipe.execute()

        return [uid for uid, exists in zip(user_ids, results) if exists]

    @async_retry()
    async def remove_presence(self, user_id: str) -> None:
        """Remove a user's presence key immediately.

        Args:
            user_id: User to mark as offline.
        """
        key = f"{RedisPrefix.PRESENCE}{user_id}"
        await self._client.delete(key)
        logger.debug("cache_presence_removed", user_id=user_id)

    # ────────────────────────────────────────────────────────────
    # Typing indicators
    # ────────────────────────────────────────────────────────────

    @async_retry()
    async def set_typing(
        self, user_id: str, room_id: str, ttl: int = 5
    ) -> None:
        """Mark a user as currently typing in a room.

        Args:
            user_id: User who is typing.
            room_id: Room in which the user is typing.
            ttl: Auto-expire in seconds.
        """
        key = f"{RedisPrefix.TYPING}{room_id}:{user_id}"
        await self._client.set(key, "1", ex=ttl)

    @async_retry()
    async def get_typing_users(self, room_id: str) -> list[str]:
        """Return a list of user IDs currently typing in a room.

        Uses ``SCAN`` to find all typing keys for the given room.

        Args:
            room_id: Room to query.

        Returns:
            List of user IDs with active typing indicators.
        """
        prefix = f"{RedisPrefix.TYPING}{room_id}:"
        user_ids: list[str] = []
        async for key in self._client.scan_iter(match=f"{prefix}*", count=100):
            # key looks like "typing:room_id:user_id"
            key_str = key if isinstance(key, str) else key.decode("utf-8")
            user_id = key_str.removeprefix(prefix)
            if user_id:
                user_ids.append(user_id)
        return user_ids

    # ────────────────────────────────────────────────────────────
    # Room membership cache
    # ────────────────────────────────────────────────────────────

    @async_retry()
    async def cache_room_members(
        self, room_id: str, member_ids: list[str], ttl: int = 300
    ) -> None:
        """Cache the list of room members.

        Args:
            room_id: Room whose members to cache.
            member_ids: List of member user IDs.
            ttl: Cache lifetime in seconds.
        """
        key = f"{RedisPrefix.ROOM_MEMBERS}{room_id}"
        await self._client.set(key, self._encode(member_ids), ex=ttl)
        logger.debug(
            "cache_room_members_set", room_id=room_id, count=len(member_ids)
        )

    @async_retry()
    async def get_cached_room_members(self, room_id: str) -> list[str] | None:
        """Retrieve cached room members.

        Args:
            room_id: Room to query.

        Returns:
            List of member IDs, or ``None`` if the cache entry is missing.
        """
        key = f"{RedisPrefix.ROOM_MEMBERS}{room_id}"
        raw = await self._client.get(key)
        return self._decode(raw)

    @async_retry()
    async def invalidate_room_members(self, room_id: str) -> None:
        """Remove the cached member list for a room.

        Args:
            room_id: Room whose cache entry to invalidate.
        """
        key = f"{RedisPrefix.ROOM_MEMBERS}{room_id}"
        await self._client.delete(key)
        logger.debug("cache_room_members_invalidated", room_id=room_id)

    # ────────────────────────────────────────────────────────────
    # Node registry
    # ────────────────────────────────────────────────────────────

    @async_retry()
    async def register_node(
        self, node_id: str, info: dict[str, Any], ttl: int = 60
    ) -> None:
        """Register an application node with metadata and a TTL.

        Args:
            node_id: Unique node identifier.
            info: Node metadata (e.g. host, port, started_at).
            ttl: Heartbeat expiry in seconds.
        """
        key = f"{RedisPrefix.NODE}{node_id}"
        await self._client.set(key, self._encode(info), ex=ttl)
        logger.debug("cache_node_registered", node_id=node_id, ttl=ttl)

    @async_retry()
    async def get_active_nodes(self) -> list[dict[str, Any]]:
        """Discover all currently registered nodes.

        Uses ``SCAN`` to iterate over node keys so the operation is
        non-blocking even with many keys.

        Returns:
            List of node info dicts.
        """
        prefix = f"{RedisPrefix.NODE}"
        nodes: list[dict[str, Any]] = []

        # Collect keys first, then fetch values in a pipeline
        keys: list[str] = []
        async for key in self._client.scan_iter(match=f"{prefix}*", count=100):
            key_str = key if isinstance(key, str) else key.decode("utf-8")
            # Exclude sub-namespaces like "node:heartbeat:..."
            if key_str.startswith(RedisPrefix.NODE_HEARTBEAT):
                continue
            keys.append(key_str)

        if not keys:
            return nodes

        pipe = self._client.pipeline(transaction=False)
        for key in keys:
            pipe.get(key)
        values: list[str | None] = await pipe.execute()

        for key, raw in zip(keys, values):
            if raw is not None:
                try:
                    info = self._decode(raw)
                    info["node_id"] = key.removeprefix(prefix)
                    nodes.append(info)
                except orjson.JSONDecodeError:
                    logger.warning("cache_invalid_node_data", key=key)

        return nodes

    @async_retry()
    async def node_heartbeat(self, node_id: str, ttl: int = 60) -> None:
        """Refresh the TTL on a registered node.

        Args:
            node_id: Node whose registration to keep alive.
            ttl: New TTL in seconds.
        """
        key = f"{RedisPrefix.NODE}{node_id}"
        await self._client.expire(key, ttl)
