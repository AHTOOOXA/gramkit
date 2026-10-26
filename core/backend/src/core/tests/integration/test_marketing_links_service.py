"""MarketingLinksService on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session), internal_referal_ids=...,
marketing_links_config=...)`` directly: the app's config is a constructor value, so there is no
global state to restore. Links come through the ``_link_bases`` seam, patched with
``patch.object`` — never through the lazy ``settings`` proxy, which would import ``app``.
"""

import random
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import MarketingCodeNotAllowedException, MarketingLinkNotFoundException
from core.infrastructure.database.models import AuditLog, Payment, User
from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus, UserRole
from core.infrastructure.database.repo.marketing_links import MarketingLinkRepo
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.marketing_links import MarketingLinkCreateRequest, MarketingLinkUpdateRequest
from core.schemas.users import UserSchema
from core.services.marketing_links import MarketingLinksConfig, MarketingLinksService
from core.services.requests import CoreRequestsService

APP_URL, BOT_URL = "https://t.me/test_bot/app", "https://t.me/test_bot"


@pytest.fixture(autouse=True)
def _link_bases() -> Iterator[None]:
    with patch.object(MarketingLinksService, "_link_bases", return_value=(APP_URL, BOT_URL)):
        yield


def _services(db_session: AsyncSession, config: MarketingLinksConfig | None = None) -> CoreRequestsService:
    return CoreRequestsService(
        CoreRequestsRepo(db_session), internal_referal_ids={"ownlink"}, marketing_links_config=config
    )


@pytest.fixture
def services(db_session: AsyncSession) -> CoreRequestsService:
    return _services(db_session)


def _code() -> str:
    return f"t_{uuid4().hex[:10]}"


async def _actor(services: CoreRequestsService) -> UserSchema:
    user = await services.repo.users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"a_{uuid4().hex[:8]}",
            "role": UserRole.ADMIN,
        }
    )
    await services.repo.session.flush()
    return UserSchema.model_validate(user)


async def _user_from(services: CoreRequestsService, code: str, **extra) -> User:
    user = await services.repo.users.create({"username": f"u_{uuid4().hex[:8]}", "referral_code": code, **extra})
    await services.repo.session.flush()
    return user


async def _pay(services: CoreRequestsService, user: User, amount: float, currency: str = "RUB") -> Payment:
    payment = await services.repo.payments.create(
        {
            "user_id": user.id,
            "product_id": "TEST_PRODUCT",
            "provider_id": PaymentProvider.YOOKASSA if currency == "RUB" else PaymentProvider.TELEGRAM_STARS,
            "amount": amount,
            "currency": currency,
            "status": PaymentStatus.SUCCEEDED,
            "provider_metadata": {},
        }
    )
    await services.repo.session.flush()
    return payment


async def _audit(services: CoreRequestsService, action: str, code: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.action == action, AuditLog.target_id == code)
    return list((await services.repo.session.execute(stmt)).scalars().all())


async def _alerts(services: CoreRequestsService, link_id: int) -> dict[str, str]:
    return {a.key: a.text for a in await services.marketing_links.pending_alerts() if a.link_id == link_id}


class TestCreateAndUpdate:
    @pytest.mark.business_logic
    async def test_create_builds_both_links_and_audits(self, services: CoreRequestsService):
        actor, code = await _actor(services), _code()
        item = await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code, channel=" Post 1 "))
        assert (item.registered, item.channel) == (True, "Post 1")
        assert item.app_link == f"{APP_URL}?startapp=r-{code}"
        assert item.bot_link == f"{BOT_URL}?start={code}"
        rows = await _audit(services, "marketing_link_create", code)
        assert len(rows) == 1
        assert (rows[0].target_type, rows[0].detail) == ("marketing_link", {"channel": "Post 1"})
        link = await services.repo.marketing_links.get_by_code(code)
        assert link.created_by == actor.username

    @pytest.mark.business_logic
    async def test_the_apps_own_codes_are_not_registrable(self, services: CoreRequestsService):
        with pytest.raises(MarketingCodeNotAllowedException, match="app's own notifications"):
            await services.marketing_links.create(await _actor(services), MarketingLinkCreateRequest(code="ownlink"))

    @pytest.mark.business_logic
    async def test_duplicate_code_raises(self, services: CoreRequestsService):
        actor, code = await _actor(services), _code()
        await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code))
        with pytest.raises(MarketingCodeNotAllowedException, match="already registered"):
            await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code))

    @pytest.mark.business_logic
    async def test_a_concurrent_duplicate_raises_the_same_error_and_keeps_the_transaction(
        self, services: CoreRequestsService
    ):
        """Two requests both pass the lookup; the second insert hits the unique constraint. The
        savepoint keeps the session usable and the error is the domain one (400, not 500)."""
        actor, code = await _actor(services), _code()
        await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code))
        with patch.object(MarketingLinkRepo, "get_by_code", AsyncMock(return_value=None)):
            with pytest.raises(MarketingCodeNotAllowedException, match="already registered"):
                await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code))
        assert len(await _audit(services, "marketing_link_create", code)) == 1  # session still works

    @pytest.mark.business_logic
    async def test_update_unknown_link_raises(self, services: CoreRequestsService):
        with pytest.raises(MarketingLinkNotFoundException, match="Marketing link not found"):
            await services.marketing_links.update(
                await _actor(services), 2_147_483_000, MarketingLinkUpdateRequest(channel="x")
            )

    @pytest.mark.business_logic
    async def test_update_trims_channel_and_audits_only_the_sent_fields(self, services: CoreRequestsService):
        actor, code = await _actor(services), _code()
        created = await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code, price_rub=10))
        item = await services.marketing_links.update(
            actor, created.id, MarketingLinkUpdateRequest(channel="  ", is_archived=True)
        )
        assert (item.channel, item.is_archived, item.price_rub) == (None, True, 10.0)
        rows = await _audit(services, "marketing_link_update", code)
        assert rows[0].detail == {"channel": None, "is_archived": True}


class TestListing:
    @pytest.mark.business_logic
    async def test_the_apps_own_codes_are_not_listed(self, services: CoreRequestsService):
        external = _code()
        await _user_from(services, external)
        await _user_from(services, "ownlink")
        codes = {item.code for item in (await services.marketing_links.list_links()).items}
        assert external in codes
        assert "ownlink" not in codes

    @pytest.mark.business_logic
    async def test_rates_come_from_the_config(self, db_session: AsyncSession):
        services = _services(db_session, MarketingLinksConfig(rub_per_unit={"RUB": 1.0, "XTR": 2.0}))
        code = _code()
        await _pay(services, await _user_from(services, code), 100, currency="XTR")
        await _pay(services, await _user_from(services, code), 50, currency="USD")  # no rate: 0
        item = next(i for i in (await services.marketing_links.list_links()).items if i.code == code)
        assert item.stats.revenue_rub == 200.0

    @pytest.mark.business_logic
    async def test_default_rates(self, services: CoreRequestsService):
        code = _code()
        await _pay(services, await _user_from(services, code), 100, currency="XTR")
        item = next(i for i in (await services.marketing_links.list_links()).items if i.code == code)
        assert item.stats.revenue_rub == 110.0

    @pytest.mark.business_logic
    async def test_activation_comes_from_the_config(self, db_session: AsyncSession):
        code = _code()
        services = _services(db_session)
        payer = await _user_from(services, code, last_activity_date=datetime.now(UTC).date())
        await _pay(services, payer, 100)
        await _user_from(services, code, last_activity_date=datetime.now(UTC).date())

        default = next(i for i in (await services.marketing_links.list_links()).items if i.code == code)
        assert default.stats.activated == 2  # both opened the app

        paid = MarketingLinksConfig(
            activation=lambda: select(Payment.user_id.label("user_id"), Payment.created_at.label("at"))
        )
        custom = next(
            i for i in (await _services(db_session, paid).marketing_links.list_links()).items if i.code == code
        )
        assert custom.stats.activated == 1


class TestAlerts:
    @pytest.mark.business_logic
    async def test_first_user_and_first_payment_alert_once(self, services: CoreRequestsService):
        code = _code()
        link = await services.marketing_links.create(await _actor(services), MarketingLinkCreateRequest(code=code))
        await _pay(services, await _user_from(services, code), 100)

        alerts = await _alerts(services, link.id)
        assert set(alerts) == {"first_user", "first_payment"}
        assert code in alerts["first_user"] and "#code_" in alerts["first_user"]

        await services.marketing_links.mark_alerts_sent(await services.marketing_links.pending_alerts())
        assert await _alerts(services, link.id) == {}

    @pytest.mark.business_logic
    async def test_registering_an_old_code_does_not_replay_its_history(self, services: CoreRequestsService):
        code = _code()
        await _user_from(services, code, created_at=datetime.now(UTC) - timedelta(days=90))
        link = await services.marketing_links.create(await _actor(services), MarketingLinkCreateRequest(code=code))
        assert await _alerts(services, link.id) == {}

    @pytest.mark.business_logic
    async def test_archived_links_get_no_alerts(self, services: CoreRequestsService):
        actor, code = await _actor(services), _code()
        link = await services.marketing_links.create(actor, MarketingLinkCreateRequest(code=code))
        await services.marketing_links.update(actor, link.id, MarketingLinkUpdateRequest(is_archived=True))
        await _user_from(services, code)
        assert await _alerts(services, link.id) == {}

    @pytest.mark.business_logic
    async def test_digests_on_days_after_the_post(self, services: CoreRequestsService):
        actor, today = await _actor(services), datetime.now(UTC).date()
        week_old = await services.marketing_links.create(
            actor, MarketingLinkCreateRequest(code=_code(), price_rub=1000, published_on=today - timedelta(days=7))
        )
        day_old = await services.marketing_links.create(
            actor, MarketingLinkCreateRequest(code=_code(), published_on=today - timedelta(days=1))
        )

        week_alerts = await _alerts(services, week_old.id)
        assert set(week_alerts) == {"day_7"}  # day 1 has passed unsent: no late digests
        assert "Day 7" in week_alerts["day_7"] and "not yet" in week_alerts["day_7"]
        day_alerts = await _alerts(services, day_old.id)
        assert set(day_alerts) == {"day_1"}
        assert "Nobody came" in day_alerts["day_1"]
        assert "opened the app" in day_alerts["day_1"]  # the default activation label

    @pytest.mark.business_logic
    async def test_digest_uses_the_apps_activation_label(self, db_session: AsyncSession):
        services = _services(db_session, MarketingLinksConfig(activation_label="did <X>"))
        code = _code()
        link = await services.marketing_links.create(
            await _actor(services),
            MarketingLinkCreateRequest(code=code, published_on=datetime.now(UTC).date() - timedelta(days=1)),
        )
        await _user_from(services, code, last_activity_date=datetime.now(UTC).date())
        digest = (await _alerts(services, link.id))["day_1"]
        assert "1 users · 100% did &lt;X&gt; · 0 paid (0%)" in digest
