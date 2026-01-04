from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, inspect, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepo(Generic[ModelType]):  # noqa: UP046
    def __init__(self, session):
        self.session: AsyncSession = session
        self.model_type: type[ModelType] = None  # Set in child classes

    @property
    def primary_key_field(self) -> str:
        """Get primary key field name from model"""
        mapper = inspect(self.model_type)
        # Get the first primary key column name
        return mapper.primary_key[0].name

    async def get_by_id(self, id: Any) -> ModelType | None:
        stmt = select(self.model_type).where(getattr(self.model_type, self.primary_key_field) == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(
        self,
        id: Any,
        read: bool = False,
        nowait: bool = False,
        skip_locked: bool = False,
    ) -> ModelType | None:
        """Get entity by ID with pessimistic lock.

        Prevents race conditions in read-modify-write operations by locking
        the row until the transaction commits or rolls back.

        Args:
            id: Primary key value
            read: If False (default), acquire exclusive lock (FOR UPDATE).
                  If True, acquire shared lock (FOR SHARE).
            nowait: If True, raise OperationalError immediately if row is locked (don't wait)
            skip_locked: If True, return None if row is locked (skip it)

        Returns:
            Model instance with lock, or None if not found (or locked with skip_locked=True)

        Lock types:
            read=False (default): Exclusive lock (SELECT FOR UPDATE)
                - Prevents all other access (reads and writes)
                - Use for: Balance deductions, updates, any modification
                - Blocks: All other locks

            read=True: Shared lock (SELECT FOR SHARE)
                - Allows other shared locks but prevents writes
                - Use for: Reading data that shouldn't change during processing
                - Blocks: Only exclusive locks (other shared reads allowed)

        Example race condition prevented:
            Without lock:
                Request A: Read balance (count=1) → decides to allow
                Request B: Read balance (count=1) → decides to allow
                Request A: Deduct 1 → balance = 0
                Request B: Deduct 1 → balance = -1 (WRONG!)

            With exclusive lock (read=False):
                Request A: Lock and read balance (count=1)
                Request B: Waits for lock...
                Request A: Deduct 1 → balance = 0 → commit & release lock
                Request B: Gets lock, reads balance (count=0) → rejects request

        Example usage:
            # Exclusive lock for modifications (default)
            balance = await repo.balance.get_by_id_with_lock(user_id)
            balance.credits -= 1
            await repo.balance.update(balance.id, {...})

            # Shared lock for consistent reads
            balance = await repo.balance.get_by_id_with_lock(user_id, read=True)
            # Can read, others can read, but no writes until commit

            # NOWAIT (fail fast if locked)
            try:
                balance = await repo.balance.get_by_id_with_lock(user_id, nowait=True)
            except OperationalError:
                # Row is locked by another transaction, retry later
                pass

            # SKIP LOCKED (skip busy rows)
            balance = await repo.balance.get_by_id_with_lock(user_id, skip_locked=True)
            if balance is None:
                # Row is locked or doesn't exist, skip this operation
                pass
        """
        stmt = select(self.model_type).where(getattr(self.model_type, self.primary_key_field) == id)
        stmt = stmt.with_for_update(read=read, nowait=nowait, skip_locked=skip_locked)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[Any]) -> Sequence[ModelType]:
        stmt = select(self.model_type).where(getattr(self.model_type, self.primary_key_field).in_(ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_ids_with_lock(
        self, ids: list[Any], read: bool = False, nowait: bool = False
    ) -> Sequence[ModelType]:
        """Get multiple entities by IDs with pessimistic lock.

        Useful for batch operations that need locking on multiple rows.

        Args:
            ids: List of primary key values
            read: If False (default), acquire exclusive lock. If True, acquire shared lock.
            nowait: If True, raise OperationalError immediately if any row is locked

        Returns:
            List of model instances with locks

        Example usage:
            # Exclusive lock for batch modifications
            balances = await repo.balance.get_by_ids_with_lock([1, 2, 3])
            for balance in balances:
                balance.credits += 10
            # All locks released on commit

            # Shared lock for consistent batch read
            balances = await repo.balance.get_by_ids_with_lock([1, 2, 3], read=True)
        """
        stmt = select(self.model_type).where(getattr(self.model_type, self.primary_key_field).in_(ids))
        stmt = stmt.with_for_update(read=read, nowait=nowait)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all(self) -> Sequence[ModelType]:
        stmt = select(self.model_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: dict) -> ModelType:
        """Create a new entity.

        Uses flush() instead of commit() - transaction is managed at
        the dependency injection layer (see webhook/dependencies/database.py).

        flush() writes to database and assigns IDs, but doesn't commit.
        refresh() reloads the object to get DB-assigned values.
        """
        obj = self.model_type(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def upsert(self, data: dict, index_elements: list[str]) -> ModelType:
        """Insert or update entity on conflict.

        Uses flush() instead of commit() - transaction is managed at
        the dependency injection layer.
        """
        stmt = (
            insert(self.model_type)
            .values(**data)
            .on_conflict_do_update(
                index_elements=index_elements,
                set_=data,
            )
            .returning(self.model_type)
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one()
        # Add to session's identity map and refresh for consistent tracking
        self.session.add(obj)
        await self.session.refresh(obj)
        return obj

    async def update(self, id: Any, data: dict) -> ModelType | None:
        """Update an existing entity.

        Uses flush() instead of commit() - transaction is managed at
        the dependency injection layer.
        """
        stmt = (
            update(self.model_type)
            .where(getattr(self.model_type, self.primary_key_field) == id)
            .values(**data)
            .returning(self.model_type)
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj:
            # Add to session's identity map and refresh for consistent tracking
            self.session.add(obj)
            await self.session.refresh(obj)
        return obj

    async def delete(self, id: Any) -> bool:
        """Delete an entity.

        Uses flush() instead of commit() - transaction is managed at
        the dependency injection layer.
        """
        stmt = delete(self.model_type).where(getattr(self.model_type, self.primary_key_field) == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
