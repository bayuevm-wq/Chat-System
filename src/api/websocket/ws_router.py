"""
WebSocket endpoint router.

Handles the full WebSocket lifecycle: JWT authentication before accept,
connection registration, event routing, heartbeat, and graceful disconnect
with presence cleanup.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import orjson
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from src.config import get_settings
from src.infrastructure.security.jwt_handler import JWTHandler
from src.infrastructure.websocket.handlers import WebSocketEventHandler
from src.shared.constants import WSEventType

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
) -> None:
    """Main WebSocket endpoint for real-time chat communication.

    Flow:
    1. Validate JWT BEFORE accepting the connection
    2. Accept and register with ConnectionManager
    3. Set user online, load rooms, send connected event
    4. Main loop: receive events, route through handler
    5. Heartbeat coroutine runs in parallel
    6. On disconnect: cleanup, set offline
    """
    # ── Step 1: Authenticate before accepting ───────────────────
    try:
        jwt_handler = JWTHandler()
        payload = jwt_handler.decode_token(token)
        if payload.get("type") not in ("ws", "access"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["sub"]
    device_id = f"device-{uuid.uuid4().hex[:8]}"
    settings = get_settings()

    # ── Step 2: Get services from app state ─────────────────────
    app = websocket.app
    connection_manager = app.state.connection_manager
    event_bus = app.state.event_bus
    cache_service = app.state.cache_service

    # Build event handler with services
    # (simplified — in production, use DI container)
    from src.infrastructure.database.connection import async_session_factory
    from src.infrastructure.database.repositories.message_repo import MessageRepository
    from src.infrastructure.database.repositories.room_repo import RoomRepository
    from src.infrastructure.database.repositories.user_repo import UserRepository
    from src.application.services.chat_service import ChatService
    from src.application.services.presence_service import PresenceService
    from src.application.services.room_service import RoomService

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        message_repo = MessageRepository(session)
        room_repo = RoomRepository(session)

        chat_service = ChatService(message_repo, room_repo, event_bus, cache_service)
        presence_service = PresenceService(cache_service, event_bus, user_repo)
        room_service = RoomService(room_repo, cache_service, event_bus)

        event_handler = WebSocketEventHandler(
            chat_service=chat_service,
            presence_service=presence_service,
            room_service=room_service,
            connection_manager=connection_manager,
            event_bus=event_bus,
        )

        # ── Step 3: Connect and initialize ──────────────────────
        conn = await connection_manager.connect(websocket, user_id, device_id)

        try:
            # Set user online
            await presence_service.set_online(user_id, settings.NODE_ID, device_id)

            # Load user's rooms and register locally
            user_rooms = await room_service.get_user_rooms(uuid.UUID(user_id))
            for room in user_rooms:
                connection_manager.add_to_room(user_id, room["id"])

            # Send connected event
            await connection_manager.send_to_user(user_id, {
                "type": WSEventType.CONNECTED,
                "session_id": device_id,
                "user_id": user_id,
                "rooms": user_rooms,
                "node_id": settings.NODE_ID,
            })

            # ── Step 4: Start heartbeat coroutine ───────────────
            heartbeat_task = asyncio.create_task(
                _heartbeat_loop(websocket, settings.WS_HEARTBEAT_INTERVAL),
                name=f"heartbeat-{user_id}",
            )

            # ── Step 5: Main event loop ─────────────────────────
            try:
                while True:
                    raw = await websocket.receive_text()
                    try:
                        event = orjson.loads(raw)
                    except Exception:
                        await connection_manager.send_to_user(user_id, {
                            "type": WSEventType.ERROR,
                            "code": "INVALID_JSON",
                            "message": "Message must be valid JSON",
                        })
                        continue

                    # Route event through handler
                    response = await event_handler.handle_event(user_id, event)
                    if response:
                        await connection_manager.send_to_user(user_id, response)

                    # Commit any DB changes from this event
                    await session.commit()

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", extra={"user_id": user_id})
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        finally:
            # ── Step 6: Cleanup ─────────────────────────────────
            await connection_manager.disconnect(user_id, device_id)

            # Set offline if no other connections remain
            if not connection_manager.is_user_connected(user_id):
                try:
                    await presence_service.set_offline(user_id)
                    await session.commit()
                except Exception:
                    pass


async def _heartbeat_loop(websocket: WebSocket, interval: int) -> None:
    """Send periodic ping messages to detect dead connections.

    Args:
        websocket: The WebSocket connection.
        interval: Seconds between heartbeats.
    """
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_bytes(orjson.dumps({"type": "ping"}))
    except asyncio.CancelledError:
        pass
    except Exception:
        pass  # Connection dead, will be cleaned up by main loop
