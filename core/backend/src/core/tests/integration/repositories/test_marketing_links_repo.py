"""MarketingLinkRepo against a real database (no app installed).

``stats_by_code`` takes the app's activity selectables as arguments, so these tests pass
``default_activity()`` or a custom core-only query (payments) — no global state, no app tables.
Codes are unique per test and results are looked up by code (parallel-safe).
"""

from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import Payment, User
from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus
from core.infrastructure.database.repo.marketing_links import MarketingLinkRepo, default_activity
from core.infrastructure.database.repo.requests import CoreRequestsRepo


def _code() -> str:
    return f"t_{uuid4().hex[:10]}"


async def _user(
    db_session: AsyncSession,
    code: str | None,
    *,
    created_at: datetime | None = None,
    last_activity_date: date | None = None,
) -> User:
    data: dict = {"username": f"u_{uuid4().hex[:8]}", "referral_code": code}
    if created_at:
        data["created_at"] = created_at
    if last_activity_date:
        data["last_activity_date"] = last_activity_date
    user = await CoreRequestsRepo(db_session).users.create(data)
    await db_session.flush()
    return user


async def _pay(
    db_session: AsyncSession,
    user: User,
    amount: float,
    *,
    provider: PaymentProvider = PaymentProvider.YOOKASSA,
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
    renewal: bool = False,
    at: datetime | None = None,
) -> None:
    payment = await CoreRequestsRepo(db_session).payments.create(
        {
            "user_id": user.id,
            "product_id": "TEST_PRODUCT",
            "provider_id": provider,
            "amount": amount,
            "currency": "RUB",
            "status": status,
            "is_recurring": renewal,
            "provider_metadata": {},
        }
    )
    if at:
        payment.created_at = at
    await db_session.flush()


async def _stats(repo: MarketingLinkRepo, code: str, activation=None, activity=None) -> dict:
    activation = activation if activation is not None else default_activity()
    activity = activity if activity is not None else activation
    return (await repo.stats_by_code(activation=activation, activity=activity))[code]


class TestDefaultActivity:
    @pytest.mark.business_logic
    async def test_users_who_opened_the_app_are_activated(self, db_session: AsyncSession):
        code = _code()
        await _user(db_session, code, last_activity_date=datetime.now(UTC).date())
        await _user(db_session, code)  # never opened the app (e.g. came through the bot only)

        stats = await _stats(MarketingLinkRepo(db_session), code)
        assert (stats["users"], stats["activated"]) == (2, 1)

    @pytest.mark.business_logic
    async def test_retention_counts_users_active_n_days_after_sign_up(self, db_session: AsyncSession):
        code = _code()
        signed_up = datetime.now(UTC) - timedelta(days=10)
        await _user(db_session, code, created_at=signed_up, last_activity_date=(signed_up + timedelta(days=8)).date())
        await _user(db_session, code, created_at=signed_up, last_activity_date=signed_up.date())  # first day only
        await _user(db_session, code)  # signed up now: not eligible yet

        stats = await _stats(MarketingLinkRepo(db_session), code)
        assert (stats["returned_d1"], stats["eligible_d1"]) == (1, 2)
        assert (stats["returned_d7"], stats["eligible_d7"]) == (1, 2)
        assert (stats["returned_d30"], stats["eligible_d30"]) == (0, 0)

    @pytest.mark.business_logic
    async def test_active_the_next_calendar_day_counts_as_returned_after_a_day(self, db_session: AsyncSession):
        """Sign-up at 15:00, back the next day (any hour): returned_d1. ``last_activity_date`` is a
        day, so its end is what counts — its midnight would be before sign-up + 24 h."""
        code = _code()
        day0 = datetime.now(UTC).date() - timedelta(days=3)
        signed_up = datetime.combine(day0, time(15, 0), tzinfo=UTC)
        await _user(db_session, code, created_at=signed_up, last_activity_date=day0 + timedelta(days=1))

        stats = await _stats(MarketingLinkRepo(db_session), code)
        assert (stats["returned_d1"], stats["eligible_d1"]) == (1, 1)
        assert stats["returned_d7"] == 0


class TestCustomActivity:
    @pytest.mark.business_logic
    async def test_an_app_query_decides_activation_and_return(self, db_session: AsyncSession):
        """Any (user_id, at) query composes: here "activated" = paid, "returned" = paid later."""
        code = _code()
        signed_up = datetime.now(UTC) - timedelta(days=20)
        late_payer = await _user(db_session, code, created_at=signed_up, last_activity_date=datetime.now(UTC).date())
        await _pay(db_session, late_payer, 100, at=signed_up + timedelta(days=9))
        early_payer = await _user(db_session, code, created_at=signed_up)
        await _pay(db_session, early_payer, 100, at=signed_up + timedelta(hours=2))
        await _user(db_session, code, created_at=signed_up, last_activity_date=datetime.now(UTC).date())

        paid = select(Payment.user_id.label("user_id"), Payment.created_at.label("at"))
        stats = await _stats(MarketingLinkRepo(db_session), code, activation=paid)
        assert (stats["users"], stats["activated"], stats["payers"]) == (3, 2, 2)
        assert (stats["returned_d1"], stats["returned_d7"], stats["eligible_d7"]) == (1, 1, 3)

    @pytest.mark.business_logic
    async def test_activation_and_return_can_differ(self, db_session: AsyncSession):
        code = _code()
        signed_up = datetime.now(UTC) - timedelta(days=10)
        await _user(db_session, code, created_at=signed_up, last_activity_date=(signed_up + timedelta(days=8)).date())

        nobody = select(User.id.label("user_id"), User.created_at.label("at")).where(User.id.is_(None))
        stats = await _stats(MarketingLinkRepo(db_session), code, activation=nobody, activity=default_activity())
        assert (stats["activated"], stats["returned_d7"]) == (0, 1)


class TestPayers:
    @pytest.mark.business_logic
    async def test_gifts_and_refunds_are_not_payers(self, db_session: AsyncSession):
        code = _code()
        payer = await _user(db_session, code)
        await _pay(db_session, payer, 100)
        gifted = await _user(db_session, code)
        await _pay(db_session, gifted, 100, provider=PaymentProvider.GIFT)
        refunded = await _user(db_session, code)
        await _pay(db_session, refunded, 100, status=PaymentStatus.REFUNDED)

        stats = await _stats(MarketingLinkRepo(db_session), code)
        assert (stats["users"], stats["payers"]) == (3, 1)


class TestPaymentsByCode:
    @pytest.mark.business_logic
    async def test_only_succeeded_non_gift_payments_of_coded_users(self, db_session: AsyncSession):
        code = _code()
        user = await _user(db_session, code)
        now = datetime.now(UTC)
        await _pay(db_session, user, 100, at=now - timedelta(days=2))
        await _pay(db_session, user, 200, renewal=True, at=now - timedelta(days=1))
        await _pay(db_session, user, 999, provider=PaymentProvider.GIFT)
        await _pay(db_session, user, 300, status=PaymentStatus.REFUNDED)
        await _pay(db_session, await _user(db_session, None), 400)  # no code: not attributed

        rows = [r for r in await MarketingLinkRepo(db_session).payments_by_code() if r.code == code]
        assert [(r.amount, r.is_purchase) for r in rows] == [(100.0, True), (200.0, False)]  # oldest first
        assert all(r.currency == "RUB" for r in rows)


class TestRegistry:
    @pytest.mark.business_logic
    async def test_get_by_code_and_newest_first(self, db_session: AsyncSession):
        repo = MarketingLinkRepo(db_session)
        older = await repo.create({"code": _code()})
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        newer = await repo.create({"code": _code(), "channel": "post"})
        await db_session.flush()

        assert (await repo.get_by_code(newer.code)).id == newer.id
        assert await repo.get_by_code(_code()) is None
        ids = [link.id for link in await repo.list_all()]
        assert ids.index(newer.id) < ids.index(older.id)
        assert (newer.is_archived, newer.alerts_sent) == (False, [])
        assert (await repo.get_by_id(older.id)).code == older.code  # model_type is set
