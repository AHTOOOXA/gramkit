"""Core admin routes: the Overview snapshot and the money analytics.

  GET /admin/statistics/overview                  KPI snapshot (+ app-registered cards)
  GET /admin/analytics/revenue-timeseries         bucketed revenue per (currency, provider)
  GET /admin/analytics/revenue-kpis               per-currency cash KPIs + growth
  GET /admin/analytics/subscription-trend         new / ended / active per ISO week
  GET /admin/analytics/subscription-breakdown     status counts, gifted/paid split, churn
  GET /admin/analytics/mrr                        per-currency MRR + MoM growth

All AdminUser, thin (one service call each). Money is per-currency and NEVER summed across
currencies; the non-cash providers surface as separate series. The service clamps bounds
(days<=365, weeks<=26) and Redis-caches the two heavy reads (revenue-timeseries,
subscription-trend). Apps add Overview cards with
``core.services.admin_metrics.register_overview_card``; app-only analytics (e.g. a funnel over app
tables) live on the app's admin router under other ``/admin/analytics/*`` paths.

NOT mounted on its own: ``routers/admin.py`` includes this router, so the routes get the
``/admin`` prefix and the ``admin`` tag from there and every app keeps exactly one
``core_admin.router`` mount. That's why it declares no prefix and no tags.

Handler names, paths, query params and docstrings are frozen: the generated frontend
clients and hooks are named after them (default operationIds, no explicit ``operation_id``).

No error mapping: the services degrade instead of raising (``error`` on the overview), and
out-of-range params are FastAPI 422s.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from core.auth.rbac import AdminUser
from core.infrastructure.fastapi.dependencies import get_services
from core.schemas.analytics import (
    MrrSchema,
    RevenueKpisSchema,
    RevenueTimeseriesSchema,
    SubscriptionBreakdownSchema,
    SubscriptionTrendSchema,
)
from core.schemas.statistics import OverviewStatisticsSchema
from core.services.requests import CoreRequestsService

router = APIRouter()


@router.get("/statistics/overview", response_model=OverviewStatisticsSchema)
async def get_statistics_overview(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> OverviewStatisticsSchema:
    """KPI snapshot for the admin Overview dashboard (current + prior windows)."""
    return await services.statistics.get_overview_statistics()


@router.get("/analytics/revenue-timeseries", response_model=RevenueTimeseriesSchema)
async def get_revenue_timeseries(
    user: AdminUser,
    granularity: Literal["day", "week"] = Query("day", description="Bucket size."),
    days: int = Query(90, ge=1, le=365, description="Lookback window (clamped to 365)."),
    services: CoreRequestsService = Depends(get_services),
) -> RevenueTimeseriesSchema:
    """Bucketed revenue per (currency, provider); cash vs XTR/GIFT kept separate."""
    return await services.analytics.revenue_timeseries(granularity=granularity, days=days)


@router.get("/analytics/revenue-kpis", response_model=RevenueKpisSchema)
async def get_revenue_kpis(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> RevenueKpisSchema:
    """Per-currency cash KPIs: paying users, ARPPU, avg payment + month/week growth %."""
    return await services.analytics.revenue_kpis()


@router.get("/analytics/subscription-trend", response_model=SubscriptionTrendSchema)
async def get_subscription_trend(
    user: AdminUser,
    weeks: int = Query(12, ge=1, le=26, description="Weeks of history (clamped to 26)."),
    services: CoreRequestsService = Depends(get_services),
) -> SubscriptionTrendSchema:
    """New / ended / active subscriptions per ISO week."""
    return await services.analytics.subscription_trend(weeks=weeks)


@router.get("/analytics/subscription-breakdown", response_model=SubscriptionBreakdownSchema)
async def get_subscription_breakdown(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> SubscriptionBreakdownSchema:
    """Status counts + gifted/paid active split + churn rate + net-new (trailing 30d)."""
    return await services.analytics.subscription_breakdown()


@router.get("/analytics/mrr", response_model=MrrSchema)
async def get_mrr(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> MrrSchema:
    """Per-currency MRR (from active paid subs' product pricing) + MoM growth %."""
    return await services.analytics.mrr()
