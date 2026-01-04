from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from core.exceptions import UserNotFoundException
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.base import BaseService

logger = get_logger(__name__)


class UserService(BaseService):
    # Telegram fields that can be updated from TG API
    _TG_UPDATABLE_FIELDS = {
        "tg_first_name",
        "tg_last_name",
        "tg_username",
        "tg_language_code",
        "tg_is_premium",
        "tg_is_bot",
        "tg_added_to_attachment_menu",
        "tg_allows_write_to_pm",
    }

    async def get_or_create_user(self, user_data: UserSchema) -> UserSchema:
        """
        Optimized user get/create with minimal DB writes.

        Strategy:
        1. SELECT existing user (fast, read-only)
        2. If exists and no TG fields changed → return immediately (no write!)
        3. If exists and TG fields changed → UPDATE only changed fields
        4. If not exists → upsert (handles race conditions atomically)
        """
        data = user_data.model_dump(exclude_unset=True)
        telegram_id = data.get("telegram_id")

        # Fast path: check if user exists
        if telegram_id:
            existing = await self.repo.users.get_by_telegram_id(telegram_id)
            if existing:
                # Check if any TG fields need updating
                updates = self._get_telegram_field_updates(existing, data)
                if not updates:
                    # No changes needed - return without any write!
                    return UserSchema.model_validate(existing)

                # Update only changed TG fields
                updated = await self.repo.users.update_user(existing.id, updates)
                return UserSchema.model_validate(updated)

        # Slow path: new user - use upsert for atomicity (handles race conditions)
        user = await self.repo.users.get_or_create_user(data)
        return UserSchema.model_validate(user)

    def _get_telegram_field_updates(self, existing, new_data: dict) -> dict:
        """Compare TG fields and return only changed ones."""
        updates = {}
        for field in self._TG_UPDATABLE_FIELDS:
            if field in new_data:
                old_value = getattr(existing, field, None)
                new_value = new_data[field]
                if old_value != new_value:
                    updates[field] = new_value
        return updates

    async def get_all(self) -> list[UserSchema]:
        users = await self.repo.users.get_all()
        return [UserSchema.model_validate(user) for user in users]

    async def get_user_by_id(self, user_id: UUID):
        return UserSchema.model_validate(await self.repo.users.get_user_by_id(user_id))

    async def get_by_username(self, username: str):
        return UserSchema.model_validate(await self.repo.users.get_by_username(username))

    async def get_by_tg_username(self, tg_username: str):
        """Get user by Telegram username."""
        user = await self.repo.users.get_by_tg_username(tg_username)
        return UserSchema.model_validate(user) if user else None

    async def get_users_by_local_time(self, hour: int) -> list[UserSchema]:
        users = await self.repo.users.get_users_by_local_time(hour)
        return [UserSchema.model_validate(user) for user in users]

    async def get_users_count(self):
        return await self.repo.users.get_users_count()

    async def get_all_users_ids(self):
        return await self.repo.users.get_all_users_ids()

    async def get_friends(self, user_id: UUID):
        return await self.repo.users.get_friends(user_id)

    async def add_friend(self, user_id: UUID, friend_id: UUID):
        friend = await self.repo.users.get_user_by_id(friend_id)
        if friend is None:
            raise UserNotFoundException(f"User with id {friend_id} not found")
        if await self.is_friend(user_id, friend_id):
            logger.info(f"User {user_id} is already friends with {friend_id}")
            return
        await self.repo.users.add_friend(user_id, friend.id)

    async def update_user(self, user_id: UUID, user_data: UpdateUserRequest) -> UserSchema:
        update_data = user_data.model_dump(exclude_unset=True)
        if "is_onboarded" in update_data:
            posthog.capture(
                distinct_id=user_id,
                event="user_onboarded",
            )
        # Get current user to verify existence
        current_user = await self.repo.users.get_user_by_id(user_id)
        if not current_user:
            raise UserNotFoundException(f"User {user_id} not found")

        # Update user and return updated schema
        updated_user = await self.repo.users.update_user(user_id, update_data)
        return UserSchema.model_validate(updated_user)

    async def get_by_telegram_id(self, telegram_id: int) -> UserSchema | None:
        """Get user by Telegram ID for admin operations."""
        user = await self.repo.users.get_by_telegram_id(telegram_id)
        return UserSchema.model_validate(user) if user else None

    async def is_friend(self, user_id1: UUID, user_id2: UUID) -> bool:
        friendship = await self.repo.users.get_friendship(user_id1, user_id2)
        return friendship is not None and friendship.is_active

    async def process_referral(self, referral_id: str, user_id: UUID) -> None:
        """Save referral code for user acquisition tracking."""
        user = await self.repo.users.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return None
        if user.referral_code:
            logger.info(f"User {user_id} already registered with referral code: {user.referral_code}")
            return None

        await self.repo.users.update_user(user_id, {"referral_code": referral_id})
        logger.info(f"User {user_id}: Referral code saved: {referral_id}")

    async def process_referal(self, referal_id: str, user_id: UUID) -> None:
        """Deprecated: Use process_referral instead."""
        return await self.process_referral(referal_id, user_id)

    async def update_user_streak(self, user_id: UUID):
        """Update user streak when they use the app. Call this in process_start.

        New day starts at 5 AM local time (or Moscow time as fallback).
        This prevents late-night usage from breaking streaks.
        """
        user = await self.repo.users.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found for streak update")
            return None

        # Get user's timezone, default to Moscow time if not set
        user_timezone = user.timezone or "Europe/Moscow"
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            # Fallback to Moscow time if timezone is invalid
            tz = ZoneInfo("Europe/Moscow")
            logger.warning(f"Invalid timezone '{user_timezone}' for user {user_id}, using Europe/Moscow")

        # Calculate the "streak day" (day starts at 5 AM)
        now_utc = datetime.now(ZoneInfo("UTC"))
        now_user_tz = now_utc.astimezone(tz)

        # If it's before 5 AM, consider it as the previous day
        if now_user_tz.hour < 5:
            streak_day = (now_user_tz - timedelta(hours=5)).date()
        else:
            streak_day = now_user_tz.date()

        # Fix legacy users with streak 0
        if user.current_streak == 0:
            logger.warning(f"User {user_id} has streak 0, fixing to 1")
            user_current_streak = 1
        else:
            user_current_streak = user.current_streak

        # Skip if already processed this streak day
        if user.last_activity_date == streak_day:
            # But fix streak 0 users
            if user.current_streak == 0:
                fixed_user = await self.repo.users.update_user(
                    user_id,
                    {
                        "current_streak": max(user_current_streak, 1),
                        "best_streak": max(user.best_streak, 1),
                        "total_active_days": max(user.total_active_days, 1),
                    },
                )
                return UserSchema.model_validate(fixed_user)
            return UserSchema.model_validate(user)

        # Calculate new streak values
        if not user.last_activity_date:
            new_current_streak = 1
            new_total_active_days = max(user.total_active_days, 1)

        elif user.last_activity_date == streak_day - timedelta(days=1):
            new_current_streak = user_current_streak + 1
            new_total_active_days = user.total_active_days + 1

        else:
            new_current_streak = 1
            new_total_active_days = user.total_active_days + 1
            days_gap = (streak_day - user.last_activity_date).days if user.last_activity_date else 0
            if days_gap > 1:
                logger.info(f"User {user_id}: Streak reset after {days_gap} day gap")

        # Update best streak if current is better
        new_best_streak = max(user.best_streak, new_current_streak)

        # Ensure values are never 0
        new_current_streak = max(new_current_streak, 1)
        new_best_streak = max(new_best_streak, 1)
        new_total_active_days = max(new_total_active_days, 1)

        # Update user with new streak data
        try:
            updated_user = await self.repo.users.update_user(
                user_id,
                {
                    "current_streak": new_current_streak,
                    "best_streak": new_best_streak,
                    "last_activity_date": streak_day,
                    "total_active_days": new_total_active_days,
                },
            )
        except Exception as e:
            logger.error(f"User {user_id}: Streak update failed - {str(e)}")
            # Return user with at least streak 1 to prevent showing 0
            if user.current_streak == 0:
                user.current_streak = 1
                user.best_streak = max(user.best_streak, 1)
                user.total_active_days = max(user.total_active_days, 1)
            return UserSchema.model_validate(user)

        # Log streak milestones for analytics
        if new_current_streak in [3, 7, 14, 30, 100]:
            posthog.capture(
                distinct_id=user_id,
                event="streak_milestone_reached",
                properties={
                    "streak_days": new_current_streak,
                    "is_new_best": new_current_streak == new_best_streak,
                    "user_timezone": user_timezone,
                    "streak_day": streak_day.isoformat(),
                    "local_time": now_user_tz.isoformat(),
                },
            )

        return UserSchema.model_validate(updated_user)

    async def reset_user_streak(self, user_id: UUID, force: bool = False):
        """Reset user streak to 1 (for fixing broken streaks).

        Args:
            user_id: User ID to reset
            force: If True, resets even if user has a streak > 0
        """
        user = await self.repo.users.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for streak reset")
            return None

        if not force and user.current_streak > 0:
            logger.info(f"User {user_id} already has streak {user.current_streak}, skipping reset")
            return UserSchema.model_validate(user)

        # Get user's timezone for proper date calculation
        user_timezone = user.timezone or "Europe/Moscow"
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("Europe/Moscow")

        # Calculate current streak day

        now_utc = datetime.now(ZoneInfo("UTC"))
        now_user_tz = now_utc.astimezone(tz)

        if now_user_tz.hour < 5:
            streak_day = (now_user_tz - timedelta(hours=5)).date()
        else:
            streak_day = now_user_tz.date()

        # Reset streak to 1
        updated_user = await self.repo.users.update_user(
            user_id,
            {
                "current_streak": 1,
                "best_streak": max(user.best_streak, 1),
                "last_activity_date": streak_day,
                "total_active_days": max(user.total_active_days, 1),
            },
        )

        logger.info(f"User {user_id}: Streak manually reset to 1 (was {user.current_streak})")
        return UserSchema.model_validate(updated_user)
