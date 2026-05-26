"""
Application configuration using Pydantic Settings.

Loads settings from environment variables and .env file with validation,
type coercion, and sensible defaults for all configuration parameters.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Distributed Chat System.

    All settings are loaded from environment variables (or a .env file).
    This class provides type-safe access with validation and defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    APP_NAME: str = "distributed-chat-system"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    NODE_ID: str = Field(default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}")
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database (PostgreSQL) ───────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://chatuser:chatpass@localhost:5432/chatdb"
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=200)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5)
    DB_ECHO: bool = False

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=5)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1)
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # ── JWT Authentication ──────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    JWT_WS_TOKEN_EXPIRE_MINUTES: int = Field(default=5, ge=1)

    # ── Security ────────────────────────────────────────────────
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=31)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
    RATE_LIMIT_BURST: int = Field(default=10, ge=1)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── WebSocket ───────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, ge=10, le=120)
    WS_MAX_CONNECTIONS_PER_USER: int = Field(default=5, ge=1)
    WS_MESSAGE_QUEUE_SIZE: int = Field(default=100, ge=10)
    WS_MAX_MESSAGE_SIZE: int = Field(default=65536, ge=1024)

    # ── Workers ─────────────────────────────────────────────────
    OFFLINE_MESSAGE_MAX_RETRIES: int = Field(default=5, ge=1)
    OFFLINE_MESSAGE_RETRY_BASE_DELAY: int = Field(default=5, ge=1)
    NOTIFICATION_BATCH_SIZE: int = Field(default=50, ge=1)
    DEAD_LETTER_RETENTION_DAYS: int = Field(default=30, ge=1)

    # ── Observability ───────────────────────────────────────────
    METRICS_ENABLED: bool = True
    TRACING_ENABLED: bool = False
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4317"

    # ── Encryption (Simplified E2E) ─────────────────────────────
    RSA_KEY_SIZE: int = Field(default=2048, ge=1024)

    # ── Computed Properties ─────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        """Warn if using the default JWT secret (insecure)."""
        if v == "CHANGE_ME_IN_PRODUCTION":
            import warnings
            warnings.warn(
                "Using default JWT_SECRET_KEY — this is insecure! "
                "Set a proper secret in production.",
                UserWarning,
                stacklevel=2,
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
