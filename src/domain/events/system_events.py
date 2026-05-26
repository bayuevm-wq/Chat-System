"""
System / infrastructure domain events.

Events emitted when cluster nodes register, send heartbeats,
or shut down.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.events.base import DomainEvent


@dataclass
class NodeRegisteredEvent(DomainEvent):
    """Raised when a new node joins the cluster.

    Attributes:
        node_id: Unique identifier of the registering node.
        host: Hostname or IP address of the node.
        port: Port the node is listening on.
    """

    node_id: str | None = None
    host: str | None = None
    port: int | None = None

    @classmethod
    def create(
        cls,
        node_id: str,
        host: str,
        port: int,
        *,
        source_node: str | None = None,
    ) -> NodeRegisteredEvent:
        """Build a ``NodeRegisteredEvent`` with the correct event_type.

        Args:
            node_id: Unique node identifier.
            host: Hostname or IP.
            port: Listening port.
            source_node: Optional originating node.

        Returns:
            A fully populated ``NodeRegisteredEvent``.
        """
        payload: dict[str, Any] = {
            "node_id": node_id,
            "host": host,
            "port": port,
        }
        return cls(
            event_type="node.registered",
            payload=payload,
            source_node=source_node,
            node_id=node_id,
            host=host,
            port=port,
        )


@dataclass
class NodeHeartbeatEvent(DomainEvent):
    """Periodic heartbeat from a cluster node.

    Attributes:
        node_id: Unique identifier of the node.
        connections_count: Number of active WebSocket connections on the node.
    """

    node_id: str | None = None
    connections_count: int = 0

    @classmethod
    def create(
        cls,
        node_id: str,
        connections_count: int,
        *,
        source_node: str | None = None,
    ) -> NodeHeartbeatEvent:
        """Build a ``NodeHeartbeatEvent`` with the correct event_type.

        Args:
            node_id: Unique node identifier.
            connections_count: Current connection count.
            source_node: Optional originating node.

        Returns:
            A fully populated ``NodeHeartbeatEvent``.
        """
        payload: dict[str, Any] = {
            "node_id": node_id,
            "connections_count": connections_count,
        }
        return cls(
            event_type="node.heartbeat",
            payload=payload,
            source_node=source_node,
            node_id=node_id,
            connections_count=connections_count,
        )


@dataclass
class NodeShutdownEvent(DomainEvent):
    """Raised when a node is gracefully shutting down.

    Attributes:
        node_id: Unique identifier of the departing node.
    """

    node_id: str | None = None

    @classmethod
    def create(
        cls,
        node_id: str,
        *,
        source_node: str | None = None,
    ) -> NodeShutdownEvent:
        """Build a ``NodeShutdownEvent`` with the correct event_type.

        Args:
            node_id: Unique node identifier.
            source_node: Optional originating node.

        Returns:
            A fully populated ``NodeShutdownEvent``.
        """
        payload: dict[str, Any] = {
            "node_id": node_id,
        }
        return cls(
            event_type="node.shutdown",
            payload=payload,
            source_node=source_node,
            node_id=node_id,
        )
