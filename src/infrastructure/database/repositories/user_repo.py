"""
User repository — data-access layer for user accounts.

Encapsulates all database queries related to user CRUD, lookup, and
presence tracking. Uses SQLAlchemy 2.0 ``select()`` statement API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import UserModel


class UserRepository:
    """Async repository for :class:`UserModel` operations.

    Parameters
    ----------
    session:
        An active :class:`AsyncSession` — typically injected via
        ``Depends(get_session)`` in FastAPI route handlers.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Create ─────────────────────────────────────────────────
    async def create(self, user_data: dict[str, Any]) -> UserModel:
        """Insert a new user row.

        Parameters
        ----------
        user_data:
            Dictionary of column values (must include at least
            ``username``, ``email``, and ``password_hash``).

        Returns
        -------
        UserModel
            The newly created (and flushed) user instance.
        """
        user = UserModel(**user_data)
        self._session.add(user)
        await self._session.flush()
        return user

    # ── Read ───────────────────────────────────────────────────
    async def get_by_id(self, user_id: uuid.UUID) -> UserModel | None:
        """Fetch a user by primary key.

        Returns ``None`` if no user with *user_id* exists.
        """
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """Fetch a user by email address (case-insensitive)."""
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserModel | None:
        """Fetch a user by username (case-insensitive)."""
        stmt = select(UserModel).where(UserModel.username == username.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Update ─────────────────────────────────────────────────
    async def update(
        self, user_id: uuid.UUID, **kwargs: Any
    ) -> UserModel | None:
        """Partially update a user record.

        Parameters
        ----------
        user_id:
            Target user PK.
        **kwargs:
            Column-name → new-value pairs to update.

        Returns
        -------
        UserModel | None
            The refreshed user, or ``None`` if *user_id* was not found.
        """
        if not kwargs:
            return await self.get_by_id(user_id)

        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**kwargs)
            .returning(UserModel)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.flush()
        return row

    async def update_last_seen(
        self, user_id: uuid.UUID, timestamp: datetime
    ) -> None:
        """Touch the user's ``last_seen_at`` field.

        Parameters
        ----------
        user_id:
            Target user PK.
        timestamp:
            The moment to record as last activity.
        """
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_seen_at=timestamp)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    # ── Existence check ────────────────────────────────────────
    async def exists(
        self,
        username: str | None = None,
        email: str | None = None,
    ) -> bool:
        """Return ``True`` if a user with the given username **or** email exists.

        At least one of *username* / *email* must be provided.

        Raises
        ------
        ValueError
            If neither argument is supplied.
        """
        if username is None and email is None:
            raise ValueError("At least one of 'username' or 'email' is required.")

        conditions = []
        if username is not None:
            conditions.append(UserModel.username == username.lower())
        if email is not None:
            conditions.append(UserModel.email == email.lower())

        stmt = select(exists().where(or_(*conditions)))
        result = await self._session.execute(stmt)
        return bool(result.scalar())
