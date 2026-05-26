"""
Password hashing using bcrypt.

Provides secure password hashing and verification with configurable
cost factor for production deployments.
"""

from __future__ import annotations

import bcrypt

from src.config import get_settings


class PasswordHasher:
    """Secure password hashing and verification using bcrypt."""

    def __init__(self) -> None:
        settings = get_settings()
        self._rounds = settings.BCRYPT_ROUNDS

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password.

        Args:
            password: The plaintext password.

        Returns:
            bcrypt hash string.
        """
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        Args:
            password: The plaintext password to check.
            hashed: The stored bcrypt hash.

        Returns:
            True if the password matches the hash.
        """
        return bcrypt.checkpw(
            password.encode("utf-8"), hashed.encode("utf-8")
        )
