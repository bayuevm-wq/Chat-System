"""
WebSocket event handler.

Routes incoming WebSocket events to the appropriate application service
methods and returns structured response events.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.shared.constants import UserStatus, WSEventType

logger = logging.getLogger(__name__)


class WebSocketEventHandler:
    """Routes incoming WebSocket events to application services.

    Maps event types from the WebSocket protocol specification to
    the corresponding service methods, handling errors gracefully
    and returning response events for the client.
    """

    def __init__(
        self,
        chat_service: Any,
        presence_service: Any,
        room_service: Any,
        connection_manager: Any,
        event_bus: Any,
    ) -> None:
        self._chat = chat_service
        self._presence = presence_service
        self._room = room_service
        self._manager = connection_manager
        self._event_bus = event_bus

        # Event type → handler mapping
        self._handlers: dict[str, Any] = {
            WSEventType.MESSAGE_SEND: self._handle_message_send,
            WSEventType.MESSAGE_READ: self._handle_message_read,
            WSEventType.TYPING_START: self._handle_typing_start,
            WSEventType.TYPING_STOP: self._handle_typing_stop,
            WSEventType.PRESENCE_UPDATE: self._handle_presence_update,
            WSEventType.PRESENCE_HEARTBEAT: self._handle_heartbeat,
            WSEventType.ROOM_JOIN: self._handle_room_join,
            WSEventType.ROOM_LEAVE: self._handle_room_leave,
        }

    async def handle_event(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Route an incoming WebSocket event to the appropriate handler.

        Args:
            user_id: The authenticated user's UUID string.
            event: Parsed event dict with 'type' and optional data fields.

        Returns:
            Response event dict to send back, or None.
        """
        event_type = event.get("type", "")
        handler = self._handlers.get(event_type)

        if not handler:
            logger.warning("Unknown event type", extra={"type": event_type, "user_id": user_id})
            return {
                "type": WSEventType.ERROR,
                "code": "UNKNOWN_EVENT",
                "message": f"Unknown event type: {event_type}",
            }

        try:
            return await handler(user_id, event)
        except Exception as e:
            logger.error(
                "Event handler error",
                extra={"type": event_type, "user_id": user_id, "error": str(e)},
                exc_info=True,
            )
            return {
                "type": WSEventType.ERROR,
                "code": "HANDLER_ERROR",
                "message": str(e),
                "event_type": event_type,
            }

    async def _handle_message_send(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle message.send event — send a message to a room."""
        room_id = event.get("room_id", "")
        content = event.get("content", "")
        message_type = event.get("message_type", "text")
        reply_to = event.get("reply_to")
        encrypted = event.get("encrypted", False)

        result = await self._chat.send_message(
            room_id=UUID(room_id),
            sender_id=UUID(user_id),
            content=content,
            message_type=message_type,
            reply_to=reply_to,
            encrypted=encrypted,
        )
        return {
            "type": WSEventType.MESSAGE_ACK,
            "message_id": result["message_id"],
            "room_id": room_id,
            "status": "sent",
            "created_at": result["created_at"],
        }

    async def _handle_message_read(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle message.read event — mark a message as read."""
        room_id = event.get("room_id", "")
        message_id = event.get("message_id")

        await self._chat.mark_read(
            room_id=UUID(room_id),
            message_id=int(message_id),
            user_id=UUID(user_id),
        )
        return None  # Read receipts broadcast via event bus

    async def _handle_typing_start(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle typing.start event."""
        room_id = event.get("room_id", "")
        await self._presence.set_typing(user_id, room_id, is_typing=True)
        return None

    async def _handle_typing_stop(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle typing.stop event."""
        room_id = event.get("room_id", "")
        await self._presence.set_typing(user_id, room_id, is_typing=False)
        return None

    async def _handle_presence_update(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle presence.update event — change user status."""
        status_str = event.get("status", "online")
        try:
            status = UserStatus(status_str)
        except ValueError:
            return {
                "type": WSEventType.ERROR,
                "code": "INVALID_STATUS",
                "message": f"Invalid status: {status_str}",
            }

        await self._presence.update_status(user_id, status)
        return None

    async def _handle_heartbeat(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle presence.heartbeat event — refresh presence TTL."""
        await self._presence.heartbeat(user_id)
        return {"type": WSEventType.PONG}

    async def _handle_room_join(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle room.join event — join a chat room."""
        room_id = event.get("room_id", "")
        result = await self._room.join_room(UUID(room_id), UUID(user_id))

        # Register locally for message routing
        self._manager.add_to_room(user_id, room_id)

        # Subscribe to room's Redis channel
        await self._event_bus.subscribe_room(
            room_id,
            lambda rid, msg: self._manager.send_to_room(rid, msg),
        )

        return {
            "type": WSEventType.ROOM_UPDATED,
            "event": "joined",
            "room_id": room_id,
            **result,
        }

    async def _handle_room_leave(
        self, user_id: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle room.leave event — leave a chat room."""
        room_id = event.get("room_id", "")
        await self._room.leave_room(UUID(room_id), UUID(user_id))
        self._manager.remove_from_room(user_id, room_id)
        return {
            "type": WSEventType.ROOM_UPDATED,
            "event": "left",
            "room_id": room_id,
        }
