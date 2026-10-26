"""StatisticsService (Overview + daily digest) on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session))`` directly. The digest title comes
through the ``_app_title`` seam and the windows through ``_compute_windows``, both patched with
``patch.object`` — never through the lazy ``settings`` proxy, which would import ``app``.

The windows are pinned around "now": rows get ``created_at`` from the Postgres clock while the
service computes its window end from the Python clock, so a seeded row could otherwise fall just
outside the window. Currencies are unique per test file ("ZZQ") so revenue sums are exact.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.statistics import OverviewCard, OverviewStatisticsSchema
from core.services import admin_metrics
from core.services.admin_metrics import DigestRow, StatWindows, register_digest_row, register_overview_card
from core.services.requests import CoreRequestsService
from core.services.statistics import StatisticsService

CURRENCY = "ZZQ"


def _windows_covering_now() -> StatWindows:
    end = datetime.now(UTC) + timedelta(minutes=5)
    start = end - timedelta(hours=23, minutes=55)
    return StatWindows(
        now=end,
        today_start=start,
        week_ago_start=start - timedelta(days=7),
        month_ago_start=start - timedelta(days=30),
    )


@pytest.fixture(autouse=True)
def _isolated(monkeypatch) -> Iterator[None]:
    """Empty registries, a fixed title and windows that cover the seeded rows."""
    monkeypatch.setattr(admin_metrics, "_OVERVIEW_CARDS", {})
    monkeypatch.setattr(admin_metrics, "_DIGEST_ROWS", {})
    with (
        patch.object(StatisticsService, "_app_title", return_value="Demo"),
        patch.object(StatisticsService, "_compute_windows", staticmethod(_windows_covering_now)),
    ):
        yield


@pytest.fixture
def core_services(db_session: AsyncSession) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session))


async def _pay(
    services: CoreRequestsService,
    *,
    amount: float,
    recurring: bool = False,
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
    product_id: str = "P_MONTH",
) -> None:
    user = await services.repo.users.create({"username": f"st_{uuid4().hex[:8]}"})
    await services.repo.payments.create(
        {
            "user_id": user.id,
            "product_id": product_id,
            "provider_id": PaymentProvider.YOOKASSA,
            "amount": amount,
            "currency": CURRENCY,
            "status": status,
            "is_recurring": recurring,
            "provider_metadata": {},
        }
    )
    await services.repo.session.flush()


class TestOverview:
    @pytest.mark.business_logic
    async def test_blocks_are_populated(self, core_services: CoreRequestsService):
        await _pay(core_services, amount=300.0, product_id="P_STATS_A")

        overview = await core_services.statistics.get_overview_statistics()

        assert isinstance(overview, OverviewStatisticsSchema)
        assert overview.error is None
        assert overview.users.total >= 1
        assert overview.users.new_today >= 1
        assert overview.revenue.alltime[CURRENCY] == 300.0
        assert overview.revenue.today[CURRENCY] == 300.0
        assert overview.product_sales.alltime["P_STATS_A"] >= 1
        assert overview.cards == []

    @pytest.mark.business_logic
    async def test_registered_cards_get_the_session_and_windows(
        self, core_services: CoreRequestsService, db_session: AsyncSession
    ):
        seen: list[tuple[AsyncSession, StatWindows]] = []

        async def orders(session: AsyncSession, window: StatWindows) -> OverviewCard:
            seen.append((session, window))
            return OverviewCard(key="orders", section="shop", label="Orders", value=3, previous=2)

        async def rate(session: AsyncSession, window: StatWindows) -> OverviewCard:
            return OverviewCard(key="rate", section="shop", label="Rate", value=None, format="percent")

        register_overview_card("orders", orders)
        register_overview_card("rate", rate)

        overview = await core_services.statistics.get_overview_statistics()

        assert [card.key for card in overview.cards] == ["orders", "rate"]
        assert overview.cards[0].previous == 2
        assert overview.cards[1].value is None
        [(session, window)] = seen
        assert session is db_session
        assert window.today_str == overview.date

    @pytest.mark.business_logic
    async def test_a_failing_card_degrades_the_whole_overview(self, core_services: CoreRequestsService):
        async def broken(session: AsyncSession, window: StatWindows) -> OverviewCard:
            raise RuntimeError("card exploded")

        register_overview_card("broken", broken)

        overview = await core_services.statistics.get_overview_statistics()

        assert overview.error == "Failed to gather statistics: card exploded"
        assert overview.cards == []
        assert overview.users.total == 0
        assert overview.revenue.alltime == {}


class TestDailyDigest:
    @pytest.mark.business_logic
    async def test_purchases_and_renewals_split_and_canceled_payments_excluded(
        self, core_services: CoreRequestsService
    ):
        await _pay(core_services, amount=100.0)
        await _pay(core_services, amount=100.0, recurring=True)
        await _pay(core_services, amount=999.0, status=PaymentStatus.CANCELED)

        digest = await core_services.statistics.get_daily_digest()

        assert digest.error is None
        assert digest.app_title == "Demo"
        assert digest.day.revenue[CURRENCY] == 200.0
        assert digest.week.revenue[CURRENCY] == 200.0
        assert digest.day.purchases >= 1
        assert digest.day.renewals >= 1
        assert digest.day.new_users >= 3
        assert digest.partial is False

        text, rich = core_services.statistics.format_daily_digest(digest)
        assert rich is not None and rich.startswith("<h3>📊 Demo · ")
        assert text.startswith("<b>📊 Demo · ")

    @pytest.mark.business_logic
    async def test_registered_rows_are_collected_in_order_and_none_is_skipped(self, core_services: CoreRequestsService):
        async def orders(session: AsyncSession, window: StatWindows) -> DigestRow | None:
            return DigestRow("Orders", 1, 5, 4)

        async def nothing(session: AsyncSession, window: StatWindows) -> DigestRow | None:
            return None

        async def note(session: AsyncSession, window: StatWindows) -> DigestRow | None:
            return DigestRow("", line="📝 a note")

        register_digest_row("note", note, order=100)
        register_digest_row("orders", orders, order=30)
        register_digest_row("nothing", nothing, order=35)

        digest = await core_services.statistics.get_daily_digest()

        assert [(order, row.label) for order, row in digest.rows] == [(30, "Orders"), (100, "")]
        _, rich = core_services.statistics.format_daily_digest(digest)
        assert rich is not None
        assert rich.index("<td>New users</td>") < rich.index("<td>Orders</td>") < rich.index("<td>Purchases</td>")
        assert "<p>📝 a note</p>" in rich

    @pytest.mark.business_logic
    async def test_a_failing_row_degrades_to_an_error_digest(self, core_services: CoreRequestsService):
        async def broken(session: AsyncSession, window: StatWindows) -> DigestRow | None:
            raise RuntimeError("row <exploded>")

        register_digest_row("broken", broken)

        digest = await core_services.statistics.get_daily_digest()

        assert digest.error == "row <exploded>"
        text, rich = core_services.statistics.format_daily_digest(digest)
        assert rich is None
        assert "row &lt;exploded&gt;" in text
