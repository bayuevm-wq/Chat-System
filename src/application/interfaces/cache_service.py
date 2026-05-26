"""
Abstract cache service interface (port).

Defines the contract for caching operations including sessions,
presence tracking, typing indicators, and room membership caching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ICacheService(ABC):
    """Port for caching and ephemeral state management."""

    # ── Session Management ──────────────────────────────────────
    @abstractmethod
    async def store_session(self, session_id: str, user_data: dict[str, Any], ttl: int) -> None:
        """Store a user session with TTL."""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        ...

    # ── Presence ────────────────────────────────────────────────
    @abstractmethod
    async def set_presence(self, user_id: str, status: str, ttl: int = 60) -> None:
        """Set user presence with auto-expire TTL."""
        ...

    @abstractmethod
    async def get_presence(self, user_id: str) -> str | None:
        """Get user's current presence status."""
        ...

    @abstractmethod
    async def heartbeat(self, user_id: str, ttl: int = 60) -> None:
        """Refresh presence TTL (keepalive)."""
        ...

    @abstractmethod
    async def get_online_users(self, user_ids: list[str]) -> list[str]:
        """Check which users from a list are currently online."""
        ...

    @abstractmethod
    async def remove_presence(self, user_id: str) -> None:
        """Remove user presence (mark offline)."""
        ...

    # ── Typing Indicators ───────────────────────────────────────
    @abstractmethod
    async def set_typing(self, user_id: str, room_id: str, ttl: int = 5) -> None:
        """Set typing indicator with short TTL."""
        ...

    @abstractmethod
    async def get_typing_users(self, room_id: str) -> list[str]:
        """Get list of users currently typing in a room."""
        ...

    # ── Room Membership Cache ───────────────────────────────────
    @abstractmethod
    async def cache_room_members(
        self, room_id: str, member_ids: list[str], ttl: int = 300
    ) -> None:
        """Cache room membership list."""
        ...

    @abstractmethod
    async def get_cached_room_members(self, room_id: str) -> list[str] | None:
        """Get cached room members, or None if cache miss."""
        ...

    @abstractmethod
    async def invalidate_room_members(self, room_id: str) -> None:
        """Invalidate room membership cache."""
        ...

    # ── Node Registry ───────────────────────────────────────────
    @abstractmethod
    async def register_node(
        self, node_id: str, info: dict[str, Any], ttl: int = 60
    ) -> None:
        """Register this node in the cluster registry."""
        ...

    @abstractmethod
    async def get_active_nodes(self) -> list[dict[str, Any]]:
        """List all active nodes in the cluster."""
        ...

    @abstractmethod
    async def node_heartbeat(self, node_id: str, ttl: int = 60) -> None:
        """Refresh node registration TTL."""
        ...
