"""
FastAPI dependency injection wiring.

Provides all dependency factories for injecting services, repositories,
and infrastructure components into API route handlers.
"""

from __future__ import annotations

from typing import Annotated, Any, AsyncGenerator

import jwt
from fastapi import Depends, Header, Query, Request, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.chat_service import ChatService
from src.application.services.notification_service import NotificationService
from src.application.services.presence_service import PresenceService
from src.application.services.room_service import RoomService
from src.infrastructure.database.connection import async_session_factory
from src.infrastructure.database.repositories.message_repo import MessageRepository
from src.infrastructure.database.repositories.room_repo import RoomRepository
from src.infrastructure.database.repositories.user_repo import UserRepository
from src.infrastructure.security.encryption import EncryptionService
from src.infrastructure.security.jwt_handler import JWTHandler
from src.infrastructure.security.password import PasswordHasher


# ── Database Session ────────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session with auto commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Repositories ────────────────────────────────────────────────

def get_user_repo(session: DBSession) -> UserRepository:
    """Get user repository with injected session."""
    return UserRepository(session)


def get_message_repo(session: DBSession) -> MessageRepository:
    """Get message repository with injected session."""
    return MessageRepository(session)


def get_room_repo(session: DBSession) -> RoomRepository:
    """Get room repository with injected session."""
    return RoomRepository(session)


UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
MessageRepo = Annotated[MessageRepository, Depends(get_message_repo)]
RoomRepo = Annotated[RoomRepository, Depends(get_room_repo)]


# ── Security ────────────────────────────────────────────────────

def get_jwt_handler(request: Request) -> JWTHandler:
    """Get JWT handler with optional cache service from app state."""
    cache = getattr(request.app.state, "cache_service", None)
    return JWTHandler(cache_service=cache)


def get_password_hasher() -> PasswordHasher:
    """Get password hasher."""
    return PasswordHasher()


def get_encryption_service() -> EncryptionService:
    """Get encryption service."""
    return EncryptionService()


JWTDep = Annotated[JWTHandler, Depends(get_jwt_handler)]
PasswordDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
EncryptionDep = Annotated[EncryptionService, Depends(get_encryption_service)]


# ── Infrastructure from App State ───────────────────────────────

def get_cache_service(request: Request) -> Any:
    """Get cache service from app state."""
    return request.app.state.cache_service


def get_event_bus(request: Request) -> Any:
    """Get event bus from app state."""
    return request.app.state.event_bus


def get_stream_processor(request: Request) -> Any:
    """Get stream processor from app state."""
    return request.app.state.stream_processor


def get_connection_manager(request: Request) -> Any:
    """Get WebSocket connection manager from app state."""
    return request.app.state.connection_manager


CacheDep = Annotated[Any, Depends(get_cache_service)]
EventBusDep = Annotated[Any, Depends(get_event_bus)]
StreamDep = Annotated[Any, Depends(get_stream_processor)]
ConnManagerDep = Annotated[Any, Depends(get_connection_manager)]


# ── Application Services ───────────────────────────────────────

def get_auth_service(
    user_repo: UserRepo,
    jwt_handler: JWTDep,
    password_hasher: PasswordDep,
    cache_service: CacheDep,
    encryption_service: EncryptionDep,
) -> AuthService:
    """Get auth service with all dependencies injected."""
    return AuthService(user_repo, jwt_handler, password_hasher, cache_service, encryption_service)


def get_chat_service(
    message_repo: MessageRepo,
    room_repo: RoomRepo,
    event_bus: EventBusDep,
    cache_service: CacheDep,
) -> ChatService:
    """Get chat service with all dependencies injected."""
    return ChatService(message_repo, room_repo, event_bus, cache_service)


def get_presence_service(
    cache_service: CacheDep,
    event_bus: EventBusDep,
    user_repo: UserRepo,
) -> PresenceService:
    """Get presence service with all dependencies injected."""
    return PresenceService(cache_service, event_bus, user_repo)


def get_room_service(
    room_repo: RoomRepo,
    cache_service: CacheDep,
    event_bus: EventBusDep,
) -> RoomService:
    """Get room service with all dependencies injected."""
    return RoomService(room_repo, cache_service, event_bus)


def get_notification_service(
    stream_processor: StreamDep,
    cache_service: CacheDep,
) -> NotificationService:
    """Get notification service with all dependencies injected."""
    return NotificationService(stream_processor, cache_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
PresenceServiceDep = Annotated[PresenceService, Depends(get_presence_service)]
RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
NotifServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


# ── Authentication Dependencies ─────────────────────────────────

async def get_current_user(
    request: Request,
    authorization: str = Header(..., description="Bearer {token}"),
) -> dict[str, Any]:
    """Extract and validate JWT from the Authorization header.

    Args:
        request: FastAPI request.
        authorization: Authorization header value.

    Returns:
        Decoded token payload with user information.

    Raises:
        HTTPException: If token is missing, invalid, or expired.
    """
    from fastapi import HTTPException

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    try:
        jwt_handler = get_jwt_handler(request)
        payload = jwt_handler.decode_token(token)

        if payload.get("type") not in ("access", "ws"):
            raise HTTPException(status_code=401, detail="Invalid token type")

        if await jwt_handler.is_blacklisted(payload.get("jti", "")):
            raise HTTPException(status_code=401, detail="Token has been revoked")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for WebSocket auth"),
) -> dict[str, Any] | None:
    """Validate JWT for WebSocket connections BEFORE accepting.

    Args:
        websocket: FastAPI WebSocket.
        token: JWT token from query parameter.

    Returns:
        Decoded payload, or None if invalid (connection will be closed).
    """
    try:
        jwt_handler = JWTHandler()
        payload = jwt_handler.decode_token(token)

        if payload.get("type") not in ("ws", "access"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return payload

    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
