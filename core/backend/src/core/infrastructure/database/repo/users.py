from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, exists, extract, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from core.infrastructure.database.models import Friendship, User
from core.infrastructure.database.repo.base import BaseRepo
from core.infrastructure.utils import normalize_email


class UserRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = User

    async def get_or_create_user(self, user_data: dict) -> User:
        """
        Creates or updates a user in the database and returns the user object.
        Uses id as primary conflict key when available, telegram_id as fallback.
        Supports users with or without telegram_id.
        :param dict user_data: User data.
        :return: User object.
        """
        filtered_data = {k: v for k, v in user_data.items() if v is not None}
        user_id = filtered_data.get("id")
        telegram_id = filtered_data.get("telegram_id")

        # Determine conflict strategy based on available keys
        if user_id:
            # id is the real primary key - use it for conflicts
            insert_stmt = (
                insert(User)
                .values(**filtered_data, created_at=text("CURRENT_TIMESTAMP"), updated_at=text("CURRENT_TIMESTAMP"))
                .on_conflict_do_update(
                    index_elements=[User.id],
                    set_=dict(
                        **filtered_data,
                        updated_at=text("CURRENT_TIMESTAMP"),
                        created_at=User.created_at,  # Preserve original created_at
                    ),
                )
                .returning(User)
            )
        elif telegram_id:
            # No id provided - use telegram_id for conflicts
            insert_stmt = (
                insert(User)
                .values(**filtered_data, created_at=text("CURRENT_TIMESTAMP"), updated_at=text("CURRENT_TIMESTAMP"))
                .on_conflict_do_update(
                    index_elements=[User.telegram_id],
                    set_=dict(
                        **{k: v for k, v in filtered_data.items() if k not in ["telegram_id", "id"]},
                        updated_at=text("CURRENT_TIMESTAMP"),
                        created_at=User.created_at,  # Preserve original created_at
                        id=User.id,  # Preserve existing id
                    ),
                )
                .returning(User)
            )
        else:
            # No identifying keys - create new user (auto-generated id)
            insert_stmt = (
                insert(User)
                .values(**filtered_data, created_at=text("CURRENT_TIMESTAMP"), updated_at=text("CURRENT_TIMESTAMP"))
                .returning(User)
            )

        result = await self.session.execute(insert_stmt)
        user = result.scalar_one()
        # Add to session's identity map and refresh for consistent tracking
        self.session.add(user)
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: UUID, user_data: dict) -> User:
        """Update user and return updated user object.

        Transaction commits at dependency layer.
        """
        stmt = update(User).where(User.id == user_id).values(**user_data).returning(User)
        result = await self.session.execute(stmt)
        user = result.scalar_one()
        # Add to session's identity map and refresh for consistent tracking
        self.session.add(user)
        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by app username (primary username field, case-insensitive)."""
        stmt = select(User).where(func.lower(User.username) == username.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tg_username(self, tg_username: str) -> User | None:
        """Get user by Telegram username."""
        stmt = select(User).where(User.tg_username == tg_username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users_by_local_time(self, hour: int) -> list[User]:
        query = select(User).where(extract("hour", func.timezone(User.timezone, func.now())) == hour)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_users_count(self) -> int:
        stmt = select(func.count()).select_from(User)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_all_users_ids(self) -> list[UUID]:
        stmt = select(User.id).select_from(User)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_friendship(self, user_id1: UUID, user_id2: UUID) -> Friendship | None:
        stmt = select(Friendship).where(
            or_(
                and_(Friendship.user_id1 == user_id1, Friendship.user_id2 == user_id2),
                and_(Friendship.user_id1 == user_id2, Friendship.user_id2 == user_id1),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_friends(self, user_id: UUID):
        stmt = (
            select(User)
            .join(
                Friendship,
                or_(
                    and_(Friendship.user_id1 == user_id, User.id == Friendship.user_id2),
                    and_(Friendship.user_id2 == user_id, User.id == Friendship.user_id1),
                ),
            )
            .where(Friendship.is_active)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_friend(self, user_id: UUID, friend_id: UUID):
        """Add a friendship between two users.

        Transaction commits at dependency layer.
        """
        friendship = Friendship(user_id1=min(user_id, friend_id), user_id2=max(user_id, friend_id))
        self.session.add(friendship)
        await self.session.flush()
        return True

    # Statistics methods
    async def _get_count_between(self, column, from_dt, to_dt=None) -> int:
        """Generic helper to count rows where a timestamp column is within date range."""
        to_dt = to_dt if to_dt else datetime.now(UTC)

        stmt = select(func.count()).select_from(User).where(column >= from_dt, column <= to_dt)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_new_users_count(self, from_dt, to_dt=None) -> int:
        """Get count of users created between dates"""
        return await self._get_count_between(User.created_at, from_dt, to_dt)

    async def get_updated_users_count(self, from_dt, to_dt=None) -> int:
        """Get count of users updated between dates"""
        return await self._get_count_between(User.updated_at, from_dt, to_dt)

    async def get_by_verified_email(self, email: str) -> User | None:
        """
        Get user by verified email address.

        Only returns users who have verified their email.

        Args:
            email: Email address (will be normalized)

        Returns:
            User if found with verified email, None otherwise
        """
        normalized = normalize_email(email)
        stmt = select(User).where(
            func.lower(User.email) == normalized,
            User.email_verified == True,  # noqa: E712 (SQLAlchemy requires ==)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_email_verified_by_any_user(self, email: str) -> bool:
        """
        Check if email is verified by any user.

        Used to prevent duplicate verified emails.

        Args:
            email: Email address (will be normalized)

        Returns:
            True if email is verified by any user
        """
        normalized = normalize_email(email)
        stmt = select(
            exists().where(
                func.lower(User.email) == normalized,
                User.email_verified == True,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or False

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address (verified or unverified).

        Args:
            email: Email address (will be normalized)

        Returns:
            User if found, None otherwise
        """
        normalized = normalize_email(email)
        stmt = select(User).where(func.lower(User.email) == normalized)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
