"""
Room repository — data-access layer for chat rooms and room membership.

Uses SQLAlchemy 2.0 ``select()`` / ``update()`` / ``delete()`` statement API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    MessageModel,
    RoomMemberModel,
    RoomModel,
)
from src.shared.constants import RoomRole, RoomType


class RoomRepository:
    """Async repository for rooms and room-membership operations.

    Parameters
    ----------
    session:
        An active :class:`AsyncSession`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Room CRUD ──────────────────────────────────────────────

    async def create(self, room_data: dict[str, Any]) -> RoomModel:
        """Insert a new room.

        Parameters
        ----------
        room_data:
            Column-name → value mapping (must include ``type``).

        Returns
        -------
        RoomModel
            The flushed room instance.
        """
        room = RoomModel(**room_data)
        self._session.add(room)
        await self._session.flush()
        return room

    async def get_by_id(self, room_id: uuid.UUID) -> RoomModel | None:
        """Fetch a room by primary key.

        Returns ``None`` if the room does not exist or has been deactivated.
        """
        stmt = select(RoomModel).where(
            RoomModel.id == room_id,
            RoomModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_rooms(self, user_id: uuid.UUID) -> list[RoomModel]:
        """Return all active rooms the user is a member of.

        Parameters
        ----------
        user_id:
            The user whose rooms to retrieve.

        Returns
        -------
        list[RoomModel]
            Rooms ordered by most recent activity (``updated_at DESC``).
        """
        stmt = (
            select(RoomModel)
            .join(RoomMemberModel, RoomMemberModel.room_id == RoomModel.id)
            .where(
                RoomMemberModel.user_id == user_id,
                RoomModel.is_active.is_(True),
            )
            .order_by(RoomModel.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Membership ─────────────────────────────────────────────

    async def add_member(
        self,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = RoomRole.MEMBER,
    ) -> RoomMemberModel:
        """Add a user to a room.

        Parameters
        ----------
        room_id:
            Target room.
        user_id:
            User to add.
        role:
            Membership role (default ``'member'``).

        Returns
        -------
        RoomMemberModel
            The flushed membership record.
        """
        member = RoomMemberModel(
            room_id=room_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def remove_member(
        self, room_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Remove a user from a room.

        Returns
        -------
        bool
            ``True`` if the membership was found and deleted.
        """
        stmt = delete(RoomMemberModel).where(
            RoomMemberModel.room_id == room_id,
            RoomMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (result.rowcount or 0) > 0

    async def get_members(
        self, room_id: uuid.UUID
    ) -> list[RoomMemberModel]:
        """Return all members of a room.

        Results are ordered by ``joined_at ASC`` (earliest first).
        """
        stmt = (
            select(RoomMemberModel)
            .where(RoomMemberModel.room_id == room_id)
            .order_by(RoomMemberModel.joined_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_member(
        self, room_id: uuid.UUID, user_id: uuid.UUID
    ) -> RoomMemberModel | None:
        """Fetch a specific membership record."""
        stmt = select(RoomMemberModel).where(
            RoomMemberModel.room_id == room_id,
            RoomMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_member(
        self, room_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Check whether a user belongs to a room."""
        member = await self.get_member(room_id, user_id)
        return member is not None

    # ── Read tracking ──────────────────────────────────────────

    async def update_last_read(
        self,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        timestamp: datetime,
    ) -> None:
        """Update the ``last_read_at`` cursor for a member.

        Parameters
        ----------
        room_id:
            Target room.
        user_id:
            Target user.
        timestamp:
            The ``created_at`` of the most recently read message.
        """
        stmt = (
            update(RoomMemberModel)
            .where(
                RoomMemberModel.room_id == room_id,
                RoomMemberModel.user_id == user_id,
            )
            .values(last_read_at=timestamp)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_unread_count(
        self, room_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        """Count messages in *room_id* created after the user's last read cursor.

        Returns
        -------
        int
            Number of unread (non-deleted) messages, ``0`` if the user
            has not yet set a read cursor (treats all as unread-from-epoch).
        """
        # Fetch the user's read cursor
        member = await self.get_member(room_id, user_id)
        if member is None:
            return 0

        stmt = select(func.count(MessageModel.id)).where(
            MessageModel.room_id == room_id,
            MessageModel.is_deleted.is_(False),
        )

        if member.last_read_at is not None:
            stmt = stmt.where(MessageModel.created_at > member.last_read_at)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ── Direct messages ────────────────────────────────────────

    async def get_or_create_direct_room(
        self,
        user_id_1: uuid.UUID,
        user_id_2: uuid.UUID,
    ) -> RoomModel:
        """Find or create a direct-message room between two users.

        If a ``direct`` room already exists containing exactly
        *user_id_1* and *user_id_2*, it is returned. Otherwise a new
        room is created and both users are added as members.

        Parameters
        ----------
        user_id_1:
            First participant.
        user_id_2:
            Second participant.

        Returns
        -------
        RoomModel
            The existing or newly created DM room.
        """
        # Look for an existing direct room shared by both users.
        # We join room_members twice — once per user — and filter
        # to rooms of type 'direct'.
        alias_1 = RoomMemberModel.__table__.alias("m1")
        alias_2 = RoomMemberModel.__table__.alias("m2")

        stmt = (
            select(RoomModel)
            .join(alias_1, alias_1.c.room_id == RoomModel.id)
            .join(alias_2, alias_2.c.room_id == RoomModel.id)
            .where(
                RoomModel.type == RoomType.DIRECT,
                RoomModel.is_active.is_(True),
                alias_1.c.user_id == user_id_1,
                alias_2.c.user_id == user_id_2,
            )
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        # Create a new direct room
        room = RoomModel(type=RoomType.DIRECT, created_by=user_id_1)
        self._session.add(room)
        await self._session.flush()

        # Add both participants
        self._session.add_all([
            RoomMemberModel(
                room_id=room.id,
                user_id=user_id_1,
                role=RoomRole.MEMBER,
            ),
            RoomMemberModel(
                room_id=room.id,
                user_id=user_id_2,
                role=RoomRole.MEMBER,
            ),
        ])
        await self._session.flush()

        return room
