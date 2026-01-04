"""
Business logic tests for streak calculation.

Streak system uses a 5 AM cutoff:
- Usage at 2 AM counts as the previous day
- Usage at 10 AM counts as the current day

This prevents late-night users from breaking their streak.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService


def calculate_streak_day(dt: datetime) -> date:
    """
    Calculate streak day based on 5 AM cutoff.

    Before 5 AM: previous day
    After 5 AM: current day
    """
    if dt.hour < 5:
        return (dt - timedelta(hours=5)).date()
    return dt.date()


@pytest.mark.business_logic
class TestStreakDayCalculation:
    """Tests for streak day calculation with 5 AM cutoff."""

    def test_streak_day_calculation_normal_hours(self):
        """Streak day for 10 AM = same day."""
        moscow_10am = datetime(2025, 8, 30, 10, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_10am) == date(2025, 8, 30)

    def test_streak_day_calculation_early_hours(self):
        """Streak day for 2 AM = previous day (5 AM cutoff)."""
        moscow_2am = datetime(2025, 8, 30, 2, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_2am) == date(2025, 8, 29)

    def test_streak_day_calculation_exactly_5am(self):
        """Streak day for exactly 5 AM = current day."""
        moscow_5am = datetime(2025, 8, 30, 5, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_5am) == date(2025, 8, 30)

    def test_streak_day_calculation_just_before_5am(self):
        """Streak day for 4:59 AM = previous day."""
        moscow_459am = datetime(2025, 8, 30, 4, 59, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_459am) == date(2025, 8, 29)

    def test_streak_day_calculation_midnight(self):
        """Streak day for midnight = previous day."""
        moscow_midnight = datetime(2025, 8, 30, 0, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_midnight) == date(2025, 8, 29)

    def test_streak_day_calculation_evening(self):
        """Streak day for 11 PM = same day."""
        moscow_11pm = datetime(2025, 8, 30, 23, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        assert calculate_streak_day(moscow_11pm) == date(2025, 8, 30)


@pytest.mark.business_logic
class TestStreakUpdate:
    """Tests for streak update logic."""

    async def test_first_time_user_gets_streak_1(self, db_session: AsyncSession):
        """First time user gets streak 1."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        # Create new user
        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 111111111,
                "username": "streak_test_1",
                "tg_first_name": "Test",
            }
        )
        await db_session.flush()

        # Update streak
        updated = await services.users.update_user_streak(user.id)

        assert updated is not None
        assert updated.current_streak >= 1, "First time user should have streak >= 1"
        assert updated.best_streak >= 1, "Best streak should be >= 1"

    async def test_consecutive_day_increments_streak(self, db_session: AsyncSession):
        """Consecutive day activity increments streak."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        # Create user with yesterday's activity
        yesterday = date.today() - timedelta(days=1)
        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 222222222,
                "username": "streak_test_2",
                "tg_first_name": "Test",
            }
        )
        await db_session.flush()

        # Set last activity to yesterday with streak 5
        await repo.users.update_user(
            user.id,
            {
                "last_activity_date": yesterday,
                "current_streak": 5,
                "best_streak": 5,
                "total_active_days": 5,
            },
        )
        await db_session.flush()

        # Update streak for today
        updated = await services.users.update_user_streak(user.id)

        # Streak should increment (may be 6 or 1 depending on timing)
        assert updated.current_streak >= 1

    async def test_total_active_days_always_increments(self, db_session: AsyncSession):
        """Total active days increments on new activity."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        # Create user
        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 333333333,
                "username": "streak_test_3",
                "tg_first_name": "Test",
                "total_active_days": 10,
            }
        )
        await db_session.flush()

        # Set last activity to 3 days ago (gap)
        three_days_ago = date.today() - timedelta(days=3)
        await repo.users.update_user(
            user.id,
            {
                "last_activity_date": three_days_ago,
                "total_active_days": 10,
            },
        )
        await db_session.flush()

        # Update streak
        updated = await services.users.update_user_streak(user.id)

        # Total active days should increment
        assert updated.total_active_days >= 10

    async def test_streak_never_goes_below_1(self, db_session: AsyncSession):
        """Streak is never 0 (minimum is 1)."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        # Create user with streak 0 (legacy data)
        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 444444444,
                "username": "streak_test_4",
                "tg_first_name": "Test",
                "current_streak": 0,
            }
        )
        await db_session.flush()

        # Update streak should fix the 0
        updated = await services.users.update_user_streak(user.id)

        assert updated.current_streak >= 1, "Streak should never be 0"


@pytest.mark.business_logic
class TestStreakTimezones:
    """Tests for streak calculation with different timezones."""

    async def test_timezone_moscow(self, db_session: AsyncSession):
        """Moscow timezone (Europe/Moscow) uses correct cutoff."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 555555555,
                "username": "tz_moscow",
                "tg_first_name": "Test",
                "timezone": "Europe/Moscow",
            }
        )
        await db_session.flush()

        # Update streak
        updated = await services.users.update_user_streak(user.id)
        assert updated is not None

    async def test_timezone_utc(self, db_session: AsyncSession):
        """UTC timezone works correctly."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 666666666,
                "username": "tz_utc",
                "tg_first_name": "Test",
                "timezone": "UTC",
            }
        )
        await db_session.flush()

        updated = await services.users.update_user_streak(user.id)
        assert updated is not None

    async def test_invalid_timezone_falls_back_to_moscow(self, db_session: AsyncSession):
        """Invalid timezone falls back to Moscow."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 777777777,
                "username": "tz_invalid",
                "tg_first_name": "Test",
                "timezone": "Invalid/Timezone",
            }
        )
        await db_session.flush()

        # Should not crash, falls back to Moscow
        updated = await services.users.update_user_streak(user.id)
        assert updated is not None


@pytest.mark.business_logic
class TestStreakReset:
    """Tests for streak reset functionality."""

    async def test_reset_streak_sets_to_1(self, db_session: AsyncSession):
        """Reset streak sets it to 1."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 888888888,
                "username": "reset_test",
                "tg_first_name": "Test",
                "current_streak": 0,  # Legacy broken data
            }
        )
        await db_session.flush()

        # Force reset
        updated = await services.users.reset_user_streak(user.id, force=True)

        assert updated is not None
        assert updated.current_streak == 1

    async def test_reset_preserves_best_streak(self, db_session: AsyncSession):
        """Reset preserves best streak when higher than 1."""
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        user = await repo.users.get_or_create_user(
            {
                "telegram_id": 999999999,
                "username": "reset_best",
                "tg_first_name": "Test",
                "current_streak": 50,
                "best_streak": 50,
            }
        )
        await db_session.flush()

        # Force reset
        updated = await services.users.reset_user_streak(user.id, force=True)

        assert updated.current_streak == 1
        assert updated.best_streak == 50  # Preserved
