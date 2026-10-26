"""Schemas for the admin Overview dashboard (``GET /admin/statistics/overview``).

Each block carries current-window scalars plus prior-window counts so the frontend
can render deltas. Revenue/product-sales are PER-CURRENCY / per-product dicts and are
NEVER summed across currencies (no base currency exists). ``error`` surfaces a degraded
read gracefully instead of 500-ing — statistics gathering swallows exceptions.

App-specific numbers arrive as ``cards``: KPI tiles the app registers with
``core.services.admin_metrics.register_overview_card``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UsersStatsSchema(BaseModel):
    total: int
    new_today: int
    new_this_week: int
    new_this_month: int
    new_prev_day: int
    new_prev_week: int
    new_prev_month: int
    dau: int
    wau: int
    mau: int


class RevenueStatsSchema(BaseModel):
    # Per-currency maps, never summed across currencies.
    alltime: dict[str, float]
    today: dict[str, float]
    this_week: dict[str, float]
    this_month: dict[str, float]


class ProductSalesStatsSchema(BaseModel):
    alltime: dict[str, int]
    today: dict[str, int]


class SubscriptionsStatsSchema(BaseModel):
    active_subscribers: int


class OverviewCard(BaseModel):
    """An app-registered KPI tile on the admin Overview (core.services.admin_metrics)."""

    # Stable id. The UI label is the i18n key admin.overview.kpi.<key>, else ``label``.
    key: str
    # Grouping. The UI section title is admin.overview.sections.<section>.
    section: str
    # English fallback label.
    label: str
    # None = undefined (e.g. a rate with no votes) — never a misleading 0.
    value: float | None
    # The same metric over the preceding window, for a delta chip (None = no delta).
    previous: float | None = None
    format: Literal["number", "percent", "currency"] = "number"
    # Only for format="currency": the currency code of ``value``.
    currency: str | None = None
    # i18n key suffix under admin.overview.caveats (e.g. "partialDay").
    caveat: str | None = None
    # Oldest -> newest points for a small trend line.
    sparkline: list[float] = []


class OverviewStatisticsSchema(BaseModel):
    date: str
    users: UsersStatsSchema
    revenue: RevenueStatsSchema
    product_sales: ProductSalesStatsSchema
    subscriptions: SubscriptionsStatsSchema
    # App-registered tiles, in registration order (empty when degraded).
    cards: list[OverviewCard] = []
    # Set when statistics gathering degraded; the blocks above are then zeroed.
    error: str | None = None
