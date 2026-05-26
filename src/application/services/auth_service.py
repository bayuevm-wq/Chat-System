"""
Authentication service.

Handles user registration, login, token management, and session lifecycle.
Orchestrates between user repository, JWT handler, password hasher, and cache.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.domain.exceptions import AuthenticationError, DuplicateEntityError
from src.infrastructure.security.encryption import EncryptionService
from src.infrastructure.security.jwt_handler import JWTHandler
from src.infrastructure.security.password import PasswordHasher
from src.shared.utils import generate_id, utc_now

logger = logging.getLogger(__name__)


class AuthService:
    """Orchestrates authentication and session management."""

    def __init__(
        self,
        user_repo: Any,
        jwt_handler: JWTHandler,
        password_hasher: PasswordHasher,
        cache_service: Any,
        encryption_service: EncryptionService | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._jwt = jwt_handler
        self._hasher = password_hasher
        self._cache = cache_service
        self._encryption = encryption_service

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Register a new user account.

        Args:
            username: Unique username.
            email: Unique email address.
            password: Plaintext password (will be hashed).
            display_name: Optional display name.

        Returns:
            Dict with user data and authentication tokens.

        Raises:
            DuplicateEntityError: If username or email already exists.
        """
        # Check for existing user
        if await self._user_repo.exists(username=username):
            raise DuplicateEntityError("User", "username")
        if await self._user_repo.exists(email=email):
            raise DuplicateEntityError("User", "email")

        # Hash password and generate encryption keys
        password_hash = self._hasher.hash_password(password)
        public_key = None
        if self._encryption:
            pub, _priv = self._encryption.generate_key_pair()
            public_key = pub

        # Create user in database
        user = await self._user_repo.create({
            "id": generate_id(),
            "username": username,
            "email": email,
            "display_name": display_name or username,
            "password_hash": password_hash,
            "public_key": public_key,
        })

        user_id = str(user.id)
        access_token = self._jwt.create_access_token(user_id)
        refresh_token = self._jwt.create_refresh_token(user_id)

        logger.info("User registered", extra={"user_id": user_id, "username": username})

        return {
            "user": {
                "id": user_id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate a user with email and password.

        Args:
            email: User's email address.
            password: Plaintext password.

        Returns:
            Dict with user data and tokens.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not self._hasher.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        user_id = str(user.id)
        access_token = self._jwt.create_access_token(user_id)
        refresh_token = self._jwt.create_refresh_token(user_id)

        logger.info("User logged in", extra={"user_id": user_id})

        return {
            "user": {
                "id": user_id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def refresh_token(self, refresh_token_str: str) -> dict[str, Any]:
        """Exchange a valid refresh token for a new access token.

        Args:
            refresh_token_str: The refresh JWT string.

        Returns:
            Dict with new access token.

        Raises:
            AuthenticationError: If the refresh token is invalid or blacklisted.
        """
        try:
            payload = self._jwt.decode_token(refresh_token_str)
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {e}") from e

        if payload.get("type") != "refresh":
            raise AuthenticationError("Token is not a refresh token")

        if await self._jwt.is_blacklisted(payload["jti"]):
            raise AuthenticationError("Token has been revoked")

        user_id = payload["sub"]
        new_access_token = self._jwt.create_access_token(user_id)

        return {"access_token": new_access_token}

    async def logout(self, token_id: str) -> None:
        """Revoke a token by adding it to the blacklist.

        Args:
            token_id: The JWT's jti claim.
        """
        # Blacklist for the remainder of the token's TTL (conservative: 24h)
        await self._jwt.blacklist_token(token_id, ttl=86400)
        logger.info("Token revoked", extra={"token_id": token_id})

    async def get_ws_token(self, user_id: str) -> str:
        """Generate a short-lived WebSocket authentication token.

        Args:
            user_id: The user's UUID string.

        Returns:
            Short-lived JWT for WebSocket connection.
        """
        return self._jwt.create_ws_token(user_id)

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a JWT and check blacklist.

        Args:
            token: The JWT string.

        Returns:
            Decoded token payload.

        Raises:
            AuthenticationError: If token is invalid, expired, or blacklisted.
        """
        try:
            payload = self._jwt.decode_token(token)
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}") from e

        if await self._jwt.is_blacklisted(payload.get("jti", "")):
            raise AuthenticationError("Token has been revoked")

        return payload
