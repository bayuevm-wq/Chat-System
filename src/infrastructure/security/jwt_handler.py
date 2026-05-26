"""
JWT token handler.

Manages creation, validation, and blacklisting of JWT tokens
for access, refresh, and WebSocket authentication flows.
Uses PyJWT (NOT python-jose which is unmaintained).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from src.config import get_settings


class JWTHandler:
    """Handles JWT token lifecycle — creation, validation, and blacklisting.

    Supports three token types:
    - **access**: Short-lived tokens for API authentication.
    - **refresh**: Long-lived tokens for obtaining new access tokens.
    - **ws**: Very short-lived tokens for WebSocket connection auth.
    """

    def __init__(self, cache_service: Any | None = None) -> None:
        settings = get_settings()
        self._secret = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_ttl = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self._refresh_ttl = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        self._ws_ttl = timedelta(minutes=settings.JWT_WS_TOKEN_EXPIRE_MINUTES)
        self._cache = cache_service  # Optional Redis-backed blacklist

    def create_access_token(
        self, user_id: str, extra: dict[str, Any] | None = None
    ) -> str:
        """Create a short-lived access token.

        Args:
            user_id: The user's UUID string.
            extra: Additional claims to include in the payload.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "exp": now + self._access_ttl,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access",
            **(extra or {}),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a long-lived refresh token.

        Args:
            user_id: The user's UUID string.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "exp": now + self._refresh_ttl,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_ws_token(self, user_id: str) -> str:
        """Create a very short-lived WebSocket connection token.

        This token is used to authenticate WebSocket connections.
        Client should request this via REST API, then pass it as
        a query parameter when connecting to the WebSocket.

        Args:
            user_id: The user's UUID string.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "exp": now + self._ws_ttl,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "ws",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: The encoded JWT string.

        Returns:
            Decoded payload dictionary.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is malformed or invalid.
        """
        return jwt.decode(
            token,
            self._secret,
            algorithms=[self._algorithm],
            options={"require": ["sub", "exp", "iat", "jti", "type"]},
        )

    async def blacklist_token(self, token_id: str, ttl: int) -> None:
        """Add a token ID to the blacklist (via Redis).

        Args:
            token_id: The JWT's jti claim.
            ttl: Time-to-live in seconds (should match token expiry).
        """
        if self._cache:
            await self._cache.store_session(f"blacklist:{token_id}", {"revoked": True}, ttl)

    async def is_blacklisted(self, token_id: str) -> bool:
        """Check if a token has been revoked.

        Args:
            token_id: The JWT's jti claim.

        Returns:
            True if the token is blacklisted.
        """
        if self._cache:
            result = await self._cache.get_session(f"blacklist:{token_id}")
            return result is not None
        return False
