"""
Message repository — data-access layer for chat messages, deliveries,
and the offline-message queue.

All queries use SQLAlchemy 2.0 ``select()`` / ``update()`` statement API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    MessageDeliveryModel,
    MessageModel,
    OfflineMessageModel,
)
from src.shared.constants import DeliveryStatus, OfflineMessageStatus


class MessageRepository:
    """Async repository for messages, deliveries, and offline queue.

    Parameters
    ----------
    session:
        An active :class:`AsyncSession`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Messages ───────────────────────────────────────────────

    async def create(self, message_data: dict[str, Any]) -> MessageModel:
        """Insert a new message.

        Parameters
        ----------
        message_data:
            Column-name → value mapping (must include ``room_id``,
            ``sender_id``, and either ``content`` or ``encrypted_content``).

        Returns
        -------
        MessageModel
            The flushed message with its auto-generated ``id``.
        """
        message = MessageModel(**message_data)
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_by_id(self, message_id: int) -> MessageModel | None:
        """Fetch a single message by primary key."""
        stmt = select(MessageModel).where(MessageModel.id == message_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_room(
        self,
        room_id: uuid.UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[MessageModel]:
        """Return messages in a room, newest-first, with cursor pagination.

        Parameters
        ----------
        room_id:
            Target room.
        limit:
            Maximum number of messages to return (default 50).
        before:
            If supplied, only return messages created **before** this
            timestamp (exclusive upper bound for backward pagination).

        Returns
        -------
        list[MessageModel]
            Messages ordered by ``created_at DESC``.
        """
        stmt = (
            select(MessageModel)
            .where(MessageModel.room_id == room_id)
            .where(MessageModel.is_deleted.is_(False))
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.where(MessageModel.created_at < before)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        room_id: uuid.UUID,
        query: str,
        limit: int = 50,
    ) -> list[MessageModel]:
        """Full-text search on message content within a room.

        Uses PostgreSQL ``to_tsvector`` / ``to_tsquery`` for performant
        text matching. The GIN index on ``messages.content`` is used
        automatically by the planner.

        Parameters
        ----------
        room_id:
            Scope the search to this room.
        query:
            Natural-language search string.
        limit:
            Maximum results.

        Returns
        -------
        list[MessageModel]
            Matching messages ordered by relevance (``ts_rank``).
        """
        # Fallback for SQLite in-memory unit tests
        bind = self._session.bind
        if bind and bind.dialect.name == "sqlite":
            stmt = (
                select(MessageModel)
                .where(MessageModel.room_id == room_id)
                .where(MessageModel.is_deleted.is_(False))
                .where(MessageModel.content.ilike(f"%{query}%"))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())

        ts_vector = func.to_tsvector("english", MessageModel.content)
        ts_query = func.plainto_tsquery("english", query)

        stmt = (
            select(MessageModel)
            .where(MessageModel.room_id == room_id)
            .where(MessageModel.is_deleted.is_(False))
            .where(ts_vector.op("@@")(ts_query))
            .order_by(func.ts_rank(ts_vector, ts_query).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, message_id: int) -> bool:
        """Mark a message as deleted without removing the row.

        Returns
        -------
        bool
            ``True`` if the message was found and marked, ``False`` otherwise.
        """
        stmt = (
            update(MessageModel)
            .where(MessageModel.id == message_id)
            .where(MessageModel.is_deleted.is_(False))
            .values(is_deleted=True, deleted_at=func.now())
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (result.rowcount or 0) > 0

    async def mark_edited(
        self, message_id: int, new_content: str
    ) -> MessageModel | None:
        """Update message content and flag as edited.

        Returns
        -------
        MessageModel | None
            The updated message, or ``None`` if not found.
        """
        stmt = (
            update(MessageModel)
            .where(MessageModel.id == message_id)
            .where(MessageModel.is_deleted.is_(False))
            .values(
                content=new_content,
                is_edited=True,
                edited_at=func.now(),
            )
            .returning(MessageModel)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.flush()
        return row

    # ── Deliveries ─────────────────────────────────────────────

    async def create_delivery(
        self,
        message_id: int,
        user_id: uuid.UUID,
        status: str = DeliveryStatus.PENDING,
    ) -> MessageDeliveryModel:
        """Create a delivery record for a recipient.

        Parameters
        ----------
        message_id:
            The message being delivered.
        user_id:
            The target recipient.
        status:
            Initial delivery status (default ``'pending'``).

        Returns
        -------
        MessageDeliveryModel
            The flushed delivery record.
        """
        delivery = MessageDeliveryModel(
            message_id=message_id,
            user_id=user_id,
            status=status,
        )
        self._session.add(delivery)
        await self._session.flush()
        return delivery

    async def update_delivery_status(
        self,
        message_id: int,
        user_id: uuid.UUID,
        status: str,
        timestamp: datetime | None = None,
    ) -> None:
        """Transition a delivery to a new status.

        Automatically sets ``delivered_at`` / ``read_at`` if the new
        status is ``'delivered'`` or ``'read'``, respectively.

        Parameters
        ----------
        message_id:
            Target message.
        user_id:
            Target recipient.
        status:
            New delivery status value.
        timestamp:
            Optional explicit timestamp; defaults to ``now()``.
        """
        values: dict[str, Any] = {"status": status}
        ts = timestamp or datetime.utcnow()

        if status == DeliveryStatus.DELIVERED:
            values["delivered_at"] = ts
        elif status == DeliveryStatus.READ:
            values["read_at"] = ts

        stmt = (
            update(MessageDeliveryModel)
            .where(MessageDeliveryModel.message_id == message_id)
            .where(MessageDeliveryModel.user_id == user_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_pending_deliveries(
        self, user_id: uuid.UUID
    ) -> list[MessageDeliveryModel]:
        """Return all pending deliveries for a user.

        Useful when the user reconnects and needs to catch up on
        messages that were not yet acknowledged.
        """
        stmt = (
            select(MessageDeliveryModel)
            .where(MessageDeliveryModel.user_id == user_id)
            .where(MessageDeliveryModel.status == DeliveryStatus.PENDING)
            .order_by(MessageDeliveryModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Offline messages ───────────────────────────────────────

    async def create_offline_message(
        self, message_id: int, user_id: uuid.UUID
    ) -> OfflineMessageModel:
        """Enqueue a message for later delivery to an offline user.

        Parameters
        ----------
        message_id:
            The message to queue.
        user_id:
            The offline recipient.

        Returns
        -------
        OfflineMessageModel
            The flushed offline queue entry.
        """
        offline = OfflineMessageModel(
            message_id=message_id,
            user_id=user_id,
            status=OfflineMessageStatus.PENDING,
        )
        self._session.add(offline)
        await self._session.flush()
        return offline

    async def get_offline_messages(
        self, user_id: uuid.UUID
    ) -> list[OfflineMessageModel]:
        """Retrieve all pending offline messages for a user.

        Returned in chronological order so they can be delivered in
        the correct sequence.
        """
        stmt = (
            select(OfflineMessageModel)
            .where(OfflineMessageModel.user_id == user_id)
            .where(OfflineMessageModel.status == OfflineMessageStatus.PENDING)
            .order_by(OfflineMessageModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_offline_status(
        self,
        offline_id: uuid.UUID,
        status: str,
        next_retry: datetime | None = None,
    ) -> None:
        """Transition an offline-message entry to a new status.

        Parameters
        ----------
        offline_id:
            PK of the offline-message record.
        status:
            New status value (see :class:`OfflineMessageStatus`).
        next_retry:
            Scheduled next retry time (only relevant for retries).
        """
        values: dict[str, Any] = {"status": status}
        if next_retry is not None:
            values["next_retry_at"] = next_retry

        # Increment retry_count whenever we reschedule
        if status == OfflineMessageStatus.PROCESSING:
            values["retry_count"] = OfflineMessageModel.retry_count + 1

        stmt = (
            update(OfflineMessageModel)
            .where(OfflineMessageModel.id == offline_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()
