"""
Async SQLAlchemy database connection management.

Sets up the async engine, session factory, and declarative base with
a consistent naming convention for all auto-generated constraints.
Provides helpers to initialize (create tables) and tear down the engine.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

# ── Naming convention for auto-generated constraints ───────────
# Keeps Alembic migrations deterministic and human-readable.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Uses a shared ``MetaData`` instance with a naming convention so that
    constraints produced by Alembic auto-generate have predictable names.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ── Engine & session factory (lazily initialised) ──────────────
_settings = get_settings()

engine = create_async_engine(
    _settings.DATABASE_URL,
    pool_size=_settings.DB_POOL_SIZE,
    max_overflow=_settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_timeout=_settings.DB_POOL_TIMEOUT,
    echo=_settings.DB_ECHO,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Session dependency (FastAPI / general use) ─────────────────
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` that auto-commits on success or rolls back.

    Usage as a FastAPI dependency::

        @app.get("/users")
        async def list_users(session: AsyncSession = Depends(get_session)):
            ...

    The session is closed automatically when the generator exits.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Lifecycle helpers ──────────────────────────────────────────
async def init_db() -> None:
    """Create all tables defined in :attr:`Base.metadata`.

    Intended for development / testing bootstrapping.  In production,
    prefer Alembic migrations (``alembic upgrade head``).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the async engine and release all pooled connections."""
    await engine.dispose()
