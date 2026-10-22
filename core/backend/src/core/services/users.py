from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from core.exceptions import UserNotFoundException
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.base import BaseService

logger = get_logger(__name__)

MAX_REFERRAL_CODE_LENGTH = 40  # matches users.referral_code String(40)

DEFAULT_TIMEZONE = "Europe/Moscow"
STREAK_DAY_START_HOUR = 5  # a "day" starts at 05:00 local, so late-night use counts for the evening before


def user_zoneinfo(timezone: str | None) -> ZoneInfo:
    """The user's timezone; Moscow when unset or invalid."""
    try:
        return ZoneInfo(timezone or DEFAULT_TIMEZONE)
    except Exception:
        logger.warning(f"Invalid timezone '{timezone}', using {DEFAULT_TIMEZONE}")
        return ZoneInfo(DEFAULT_TIMEZONE)


def is_valid_timezone(timezone: str | None) -> bool:
    """An IANA zone name we can resolve. ``get_users_by_local_time`` feeds it to Postgres ``timezone()``,
    which raises on an unknown name — for the whole hourly query, i.e. for every user."""
    if not timezone:
        return False
    try:
        ZoneInfo(timezone)
    except Exception:
        return False
    return True


def get_streak_day(timezone: str | None, at: datetime) -> date:
    """The streak day ``at`` falls on in the user's timezone (days start at 05:00 local).

    The one definition of "a day" for ``users.last_activity_date``: anything compared with it
    (e.g. the notification lifecycle stages) must use this.
    """
    local = at.astimezone(user_zoneinfo(timezone))
    return (local - timedelta(hours=STREAK_DAY_START_HOUR)).date()


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
        """Notifiable users (Telegram, bot not blocked) whose local hour is ``hour``."""
        users = await self.repo.users.get_users_by_local_time(hour)
        return [UserSchema.model_validate(user) for user in users]

    async def get_notifiable_users(self) -> list[UserSchema]:
        """Every user a scheduled notification may reach, whatever their local hour."""
        users = await self.repo.users.get_notifiable_users()
        return [UserSchema.model_validate(user) for user in users]

    async def clear_bot_blocked(self, user_id: UUID) -> bool:
        """The user is back (/start or app open): scheduled notifications may reach them again."""
        return await self.repo.users.clear_bot_blocked(user_id)

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
        if "timezone" in update_data and not is_valid_timezone(update_data["timezone"]):
            logger.warning(f"User {user_id}: ignoring invalid timezone {update_data['timezone']!r}")
            del update_data["timezone"]
        if "is_onboarded" in update_data:
            posthog.capture(
                distinct_id=str(user_id),
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

    async def merge_seen_features(self, user_id: UUID, patch: dict) -> UserSchema:
        """Merge feature-seen flags into the user's `seen_features` map.

        Generic primitive for one-time reveals / coachmarks / "what's new" /
        capped nudges — gating state only, written via the dedicated endpoint.
        """
        updated = await self.repo.users.merge_seen_features(user_id, patch)
        return UserSchema.model_validate(updated)

    async def is_friend(self, user_id1: UUID, user_id2: UUID) -> bool:
        friendship = await self.repo.users.get_friendship(user_id1, user_id2)
        return friendship is not None and friendship.is_active

    async def process_referral(self, referral_id: str, user_id: UUID) -> None:
        """Save referral code for user acquisition tracking."""
        # Guard against empty/whitespace payloads (e.g. bare /start).
        referral_id = referral_id.strip() if referral_id else ""
        if not referral_id:
            return None
        # Guard against over-long payloads. The /start deep-link payload allows
        # up to 64 chars, but referral_code is String(40); storing a longer
        # value raises StringDataRightTruncationError and crashes the handler.
        # Legit codes are short (e.g. "r-123456"), so an over-long value is
        # garbage/abuse — skip storing it and let onboarding proceed normally.
        if len(referral_id) > MAX_REFERRAL_CODE_LENGTH:
            logger.warning(
                f"User {user_id}: referral code too long "
                f"({len(referral_id)} > {MAX_REFERRAL_CODE_LENGTH}), skipping: {referral_id[:64]!r}"
            )
            return None

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

        # Opening the app means the user is reachable again (see bot_blocked_at)
        if user.bot_blocked_at is not None:
            await self.repo.users.clear_bot_blocked(user_id)

        user_timezone = user.timezone or DEFAULT_TIMEZONE
        now_user_tz = datetime.now(UTC).astimezone(user_zoneinfo(user.timezone))
        streak_day = get_streak_day(user.timezone, now_user_tz)

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
                distinct_id=str(user_id),
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

        streak_day = get_streak_day(user.timezone, datetime.now(UTC))

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
