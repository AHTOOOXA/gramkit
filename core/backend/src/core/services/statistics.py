"""Admin statistics: the Overview KPI snapshot and the daily owner digest.

Both read the same 02:00-UTC-anchored windows (``StatWindows``). Core gathers the generic numbers
(users, revenue, product sales, subscriptions); the app's registered Overview cards and digest rows
(``core.services.admin_metrics``) are awaited after them, sequentially, on the same session.

Both reads degrade instead of raising: on any error they log it and return zeroed data carrying
``error``, so the endpoint never 500s and the digest still reaches the owners.
"""

from datetime import UTC, datetime

from core.infrastructure.database.models.enums import SubscriptionStatus
from core.infrastructure.logging import get_logger
from core.schemas.statistics import (
    OverviewCard,
    OverviewStatisticsSchema,
    ProductSalesStatsSchema,
    RevenueStatsSchema,
    SubscriptionsStatsSchema,
    UsersStatsSchema,
)
from core.services.admin_digest import DailyDigest, DigestPeriod, render_error, render_rich, render_text
from core.services.admin_metrics import DigestRow, StatWindows, digest_row_fns, overview_card_fns
from core.services.base import BaseService

logger = get_logger(__name__)


class StatisticsService(BaseService):
    """Overview snapshot (``GET /admin/statistics/overview``) and the daily digest (job + ``/stats``)."""

    @staticmethod
    def _compute_windows() -> StatWindows:
        """The current windows. A seam: tests patch it to pin the windows around their seeded rows."""
        return StatWindows.anchored(datetime.now(UTC))

    @staticmethod
    def _app_title() -> str:
        """The digest title's app name (``APP_NAME``, title-cased). A seam: core tests patch it."""
        # Imported here (not at module level): the settings proxy resolves the app's config.
        from core.infrastructure.config import settings

        return str(getattr(settings, "app_name", "app")).title()

    async def _digest_period(self, from_dt: datetime, to_dt: datetime) -> DigestPeriod:
        kinds = await self.repo.payments.get_succeeded_counts_by_kind(from_dt, to_dt)
        return DigestPeriod(
            revenue=await self.repo.payments.get_revenue_by_all_currencies_and_date(from_dt, to_dt),
            new_users=await self.repo.users.get_new_users_count(from_dt, to_dt),
            purchases=kinds["first"],
            renewals=kinds["recurring"],
            expired=await self.repo.subscriptions.count_ended_between(SubscriptionStatus.EXPIRED, from_dt, to_dt),
        )

    async def get_daily_digest(self) -> DailyDigest:
        """Data for the daily admin digest: the current 2AM-UTC day plus 7d / previous-7d context.

        The cron fires at 01:55 UTC, i.e. at the very end of the window, so "day" is a full day.
        Degrades gracefully: on a read error it logs and returns a digest carrying ``error``.
        """
        windows = self._compute_windows()
        now = windows.now
        app_title = self._app_title()
        empty = DigestPeriod()

        try:
            digest = DailyDigest(
                window_start=windows.today_start,
                window_end=now,
                day=await self._digest_period(windows.today_start, now),
                week=await self._digest_period(windows.week_ago_start, now),
                prev_week=await self._digest_period(windows.prev_week_start, windows.week_ago_start),
                dau=await self.repo.users.get_updated_users_count(windows.today_start, now),
                wau=await self.repo.users.get_updated_users_count(windows.week_ago_start, now),
                mau=await self.repo.users.get_updated_users_count(windows.month_ago_start, now),
                active_subs=await self.repo.subscriptions.get_active_subscribers_count(),
                past_due=await self.repo.subscriptions.count_by_status(SubscriptionStatus.PAST_DUE),
                canceled_day=await self.repo.subscriptions.count_ended_between(
                    SubscriptionStatus.CANCELED, windows.today_start, now
                ),
                app_title=app_title,
            )
            # App rows: sequentially, on this session (never gathered).
            rows: list[tuple[int, DigestRow]] = []
            for order, fn in digest_row_fns():
                row = await fn(self.repo.session, windows)
                if row is not None:
                    rows.append((order, row))
            digest.rows = rows
            return digest
        except Exception as e:
            logger.error(f"Error gathering daily digest: {e}", exc_info=True)
            return DailyDigest(
                window_start=windows.today_start,
                window_end=now,
                day=empty,
                week=empty,
                prev_week=empty,
                app_title=app_title,
                error=str(e),
            )

    def format_daily_digest(self, digest: DailyDigest, locale: str = "en") -> tuple[str, str | None]:
        """(classic HTML text, rich HTML body) for send_admin_message; no rich body on error."""
        if digest.error:
            return render_error(digest, locale), None
        return render_text(digest, locale), render_rich(digest, locale)

    async def get_overview_statistics(self) -> OverviewStatisticsSchema:
        """KPI snapshot for the admin Overview dashboard.

        Reuses the 2AM-UTC windows, ALSO computes the immediately-preceding window for
        each range (prev day / prev week / prev month) so the frontend can render deltas.
        Revenue and product sales stay per-currency / per-product (never summed). The app's
        registered cards follow, in registration order.

        Degrades gracefully: on any read error it logs and returns zeroed blocks (no cards)
        with a populated ``error`` so the endpoint never 500s.
        """
        windows = self._compute_windows()
        now = windows.now
        today_start = windows.today_start
        week_ago_start = windows.week_ago_start
        month_ago_start = windows.month_ago_start

        try:
            users_repo = self.repo.users
            users = UsersStatsSchema(
                total=await users_repo.get_users_count(),
                new_today=await users_repo.get_new_users_count(today_start, now),
                new_this_week=await users_repo.get_new_users_count(week_ago_start, now),
                new_this_month=await users_repo.get_new_users_count(month_ago_start, now),
                new_prev_day=await users_repo.get_new_users_count(windows.prev_day_start, today_start),
                new_prev_week=await users_repo.get_new_users_count(windows.prev_week_start, week_ago_start),
                new_prev_month=await users_repo.get_new_users_count(windows.prev_month_start, month_ago_start),
                dau=await users_repo.get_updated_users_count(today_start, now),
                wau=await users_repo.get_updated_users_count(week_ago_start, now),
                mau=await users_repo.get_updated_users_count(month_ago_start, now),
            )

            # Revenue (per-currency, never summed)
            payments = self.repo.payments
            revenue = RevenueStatsSchema(
                alltime=await payments.get_total_revenue_by_currency(),
                today=await payments.get_revenue_by_all_currencies_and_date(today_start, now),
                this_week=await payments.get_revenue_by_all_currencies_and_date(week_ago_start, now),
                this_month=await payments.get_revenue_by_all_currencies_and_date(month_ago_start, now),
            )

            product_sales = ProductSalesStatsSchema(
                alltime=await payments.get_product_sales_stats(),
                today=await payments.get_product_sales_stats_by_date(today_start, now),
            )

            subscriptions = SubscriptionsStatsSchema(
                active_subscribers=await self.repo.subscriptions.get_active_subscribers_count()
            )

            # App cards: sequentially, on this session (never gathered).
            cards: list[OverviewCard] = []
            for fn in overview_card_fns():
                cards.append(await fn(self.repo.session, windows))

            return OverviewStatisticsSchema(
                date=windows.today_str,
                users=users,
                revenue=revenue,
                product_sales=product_sales,
                subscriptions=subscriptions,
                cards=cards,
            )
        except Exception as e:
            logger.error(f"Error gathering overview statistics: {str(e)}", exc_info=True)
            return OverviewStatisticsSchema(
                date=windows.today_str,
                error=f"Failed to gather statistics: {str(e)}",
                users=UsersStatsSchema(
                    total=0,
                    new_today=0,
                    new_this_week=0,
                    new_this_month=0,
                    new_prev_day=0,
                    new_prev_week=0,
                    new_prev_month=0,
                    dau=0,
                    wau=0,
                    mau=0,
                ),
                revenue=RevenueStatsSchema(alltime={}, today={}, this_week={}, this_month={}),
                product_sales=ProductSalesStatsSchema(alltime={}, today={}),
                subscriptions=SubscriptionsStatsSchema(active_subscribers=0),
                cards=[],
            )
