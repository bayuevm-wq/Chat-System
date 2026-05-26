"""
WebSocket connection manager with per-client bounded queues.

Manages all active WebSocket connections across this node, providing:
- Per-client message queues with backpressure handling
- Dedicated writer coroutines to prevent head-of-line blocking
- Room-based message routing
- Connection lifecycle management
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import orjson
from fastapi import WebSocket

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Tracks a single WebSocket connection and its resources."""

    websocket: WebSocket
    user_id: str
    device_id: str
    queue: asyncio.Queue[bytes]  # Bounded message queue
    send_task: asyncio.Task[None] | None = None  # Dedicated writer coroutine
    rooms: set[str] = field(default_factory=set)


class ConnectionManager:
    """Manages all WebSocket connections on this node.

    Uses per-client bounded queues for backpressure:
    - Each connection gets a dedicated asyncio.Queue(maxsize=N)
    - A writer coroutine per connection drains the queue
    - When a queue is full, the oldest message is dropped (backpressure)
    - This prevents a slow client from blocking message delivery to fast clients
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._queue_size = settings.WS_MESSAGE_QUEUE_SIZE
        self._max_per_user = settings.WS_MAX_CONNECTIONS_PER_USER

        # user_id → {device_id: ConnectionInfo}
        self._connections: dict[str, dict[str, ConnectionInfo]] = {}

        # room_id → set of user_ids (local to this node)
        self._room_members: dict[str, set[str]] = {}

    async def connect(
        self, websocket: WebSocket, user_id: str, device_id: str
    ) -> ConnectionInfo:
        """Register a new WebSocket connection.

        Args:
            websocket: The FastAPI WebSocket instance.
            user_id: The authenticated user's UUID string.
            device_id: Client device identifier.

        Returns:
            ConnectionInfo for the new connection.
        """
        await websocket.accept()

        # Enforce per-user connection limit
        if user_id in self._connections:
            if len(self._connections[user_id]) >= self._max_per_user:
                # Close the oldest connection
                oldest_device = next(iter(self._connections[user_id]))
                await self.disconnect(user_id, oldest_device)

        # Create bounded queue and connection info
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self._queue_size)
        conn = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            device_id=device_id,
            queue=queue,
        )

        # Start dedicated writer coroutine
        conn.send_task = asyncio.create_task(
            self._send_loop(conn), name=f"ws-send-{user_id}-{device_id}"
        )

        # Register connection
        if user_id not in self._connections:
            self._connections[user_id] = {}
        self._connections[user_id][device_id] = conn

        logger.info(
            "WebSocket connected",
            extra={"user_id": user_id, "device_id": device_id, "total": self.connection_count},
        )
        return conn

    async def disconnect(self, user_id: str, device_id: str) -> None:
        """Remove a WebSocket connection and clean up resources.

        Args:
            user_id: The user's UUID string.
            device_id: The device identifier.
        """
        user_conns = self._connections.get(user_id, {})
        conn = user_conns.pop(device_id, None)
        if conn:
            # Cancel writer task
            if conn.send_task and not conn.send_task.done():
                conn.send_task.cancel()
                try:
                    await conn.send_task
                except asyncio.CancelledError:
                    pass

            # Remove from rooms
            for room_id in conn.rooms:
                room_users = self._room_members.get(room_id, set())
                room_users.discard(user_id)
                if not room_users:
                    self._room_members.pop(room_id, None)

            # Try to close WebSocket gracefully
            try:
                await conn.websocket.close()
            except Exception:
                pass

        # Clean up empty user entry
        if user_id in self._connections and not self._connections[user_id]:
            del self._connections[user_id]

        logger.info(
            "WebSocket disconnected",
            extra={"user_id": user_id, "device_id": device_id, "total": self.connection_count},
        )

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Send a message to all connections of a specific user.

        Args:
            user_id: Target user's UUID string.
            message: Message dict to send.
        """
        user_conns = self._connections.get(user_id, {})
        msg_bytes = orjson.dumps(message)
        for conn in user_conns.values():
            self._enqueue(conn, msg_bytes)

    async def send_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude_user: str | None = None,
    ) -> None:
        """Send a message to all local connections in a room.

        Args:
            room_id: Target room UUID string.
            message: Message dict to send.
            exclude_user: Optional user to exclude (e.g., the sender).
        """
        user_ids = self._room_members.get(room_id, set())
        msg_bytes = orjson.dumps(message)
        for uid in user_ids:
            if uid == exclude_user:
                continue
            user_conns = self._connections.get(uid, {})
            for conn in user_conns.values():
                self._enqueue(conn, msg_bytes)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to ALL connections on this node.

        Args:
            message: Message dict to broadcast.
        """
        msg_bytes = orjson.dumps(message)
        for user_conns in self._connections.values():
            for conn in user_conns.values():
                self._enqueue(conn, msg_bytes)

    def add_to_room(self, user_id: str, room_id: str) -> None:
        """Register a user as a member of a room on this node.

        Args:
            user_id: User UUID string.
            room_id: Room UUID string.
        """
        if room_id not in self._room_members:
            self._room_members[room_id] = set()
        self._room_members[room_id].add(user_id)

        # Tag the connection with the room
        for conn in self._connections.get(user_id, {}).values():
            conn.rooms.add(room_id)

    def remove_from_room(self, user_id: str, room_id: str) -> None:
        """Remove a user from a room on this node."""
        room_users = self._room_members.get(room_id, set())
        room_users.discard(user_id)
        if not room_users:
            self._room_members.pop(room_id, None)

        for conn in self._connections.get(user_id, {}).values():
            conn.rooms.discard(room_id)

    def get_connected_user_ids(self) -> set[str]:
        """Get all user IDs with active connections on this node."""
        return set(self._connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections on this node."""
        return user_id in self._connections and bool(self._connections[user_id])

    @property
    def connection_count(self) -> int:
        """Total number of active WebSocket connections on this node."""
        return sum(len(conns) for conns in self._connections.values())

    # ── Internal Methods ────────────────────────────────────────

    def _enqueue(self, conn: ConnectionInfo, msg_bytes: bytes) -> None:
        """Enqueue a message to a connection's bounded queue.

        Implements backpressure by dropping the oldest message when full.
        """
        if conn.queue.full():
            try:
                conn.queue.get_nowait()  # Drop oldest (backpressure)
            except asyncio.QueueEmpty:
                pass
        try:
            conn.queue.put_nowait(msg_bytes)
        except asyncio.QueueFull:
            logger.warning(
                "Message queue overflow",
                extra={"user_id": conn.user_id, "device_id": conn.device_id},
            )

    async def _send_loop(self, conn: ConnectionInfo) -> None:
        """Dedicated writer coroutine for a single connection.

        Continuously drains the connection's queue and sends messages
        over the WebSocket. Exits on disconnect or cancellation.
        """
        try:
            while True:
                msg_bytes = await conn.queue.get()
                try:
                    await conn.websocket.send_bytes(msg_bytes)
                except Exception:
                    # Connection died — break the loop
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                "Send loop error",
                extra={"user_id": conn.user_id, "error": str(e)},
            )
