"""
Abstract event bus interface (port).

Defines the contract for the distributed event bus used for cross-node
message propagation and real-time event broadcasting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class IEventBus(ABC):
    """Port for distributed event publishing and subscription."""

    @abstractmethod
    async def publish_message(self, room_id: str, message: dict[str, Any]) -> None:
        """Publish a chat message to a room channel (durable + real-time)."""
        ...

    @abstractmethod
    async def publish_presence(self, event: dict[str, Any]) -> None:
        """Broadcast a presence change event to all nodes."""
        ...

    @abstractmethod
    async def publish_system(self, event: dict[str, Any]) -> None:
        """Broadcast a system-wide event to all nodes."""
        ...

    @abstractmethod
    async def publish_to_node(self, node_id: str, event: dict[str, Any]) -> None:
        """Send an event directly to a specific node."""
        ...

    @abstractmethod
    async def subscribe_room(self, room_id: str, callback: Callable[..., Any]) -> None:
        """Subscribe to messages in a specific room."""
        ...

    @abstractmethod
    async def subscribe_presence(self, callback: Callable[..., Any]) -> None:
        """Subscribe to presence update events."""
        ...

    @abstractmethod
    async def subscribe_node(self, node_id: str, callback: Callable[..., Any]) -> None:
        """Subscribe to events directed at this node."""
        ...

    @abstractmethod
    async def get_room_history(
        self, room_id: str, count: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve recent message history from durable storage."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop all subscriptions and clean up resources."""
        ...
