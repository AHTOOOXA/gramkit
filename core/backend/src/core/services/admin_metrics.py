"""App extensions of the admin Overview and the daily owner digest.

Core computes the generic numbers (users, revenue, subscriptions). An app adds its own through two
module-level registries:

- ``register_overview_card(key, fn)`` — ``fn(session, window) -> OverviewCard``: one KPI tile on
  ``GET /admin/statistics/overview`` (in registration order).
- ``register_digest_row(key, fn, order=...)`` — ``fn(session, window) -> DigestRow | None``: a row
  of the digest table, a summary line under it, and/or a warning. ``None`` adds nothing.

Each app calls its registrations from one ``register_admin_metrics()`` in ``setup_infrastructure()``,
which the webhook, bot and worker entry points all run — there is no discovery. Registering a key
again replaces the earlier entry, so the call is idempotent.

Callbacks get the request's (or job's) ``AsyncSession`` and the stat windows. They must be read-only,
and they are awaited one after another: never ``gather`` on one session. A callback that raises
fails the whole read (the session's transaction is aborted), which then degrades to ``error``.

Core digest table rows use orders 10 (revenue), 20 (new users), 40 (purchases), 50 (renewals) and
60 (expired); pick an order between them to place an app row.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.statistics import OverviewCard

# The admin "day" starts at this hour (UTC); the digest cron fires just before it.
DAY_ANCHOR_HOUR_UTC = 2


@dataclass(frozen=True)
class StatWindows:
    """The day / 7-day / 30-day windows shared by the Overview and the digest.

    ``today_start`` is the most recent 02:00 UTC; the week and month start 7 and 30 days before it.
    """

    now: datetime
    today_start: datetime
    week_ago_start: datetime
    month_ago_start: datetime

    @classmethod
    def anchored(cls, now: datetime) -> StatWindows:
        """Windows for ``now``: the day starts at the closest past 02:00 UTC."""
        anchor = now.replace(hour=DAY_ANCHOR_HOUR_UTC, minute=0, second=0, microsecond=0)
        # Before 02:00 UTC the current day started yesterday.
        today_start = anchor - timedelta(days=1) if now.hour < DAY_ANCHOR_HOUR_UTC else anchor
        return cls(
            now=now,
            today_start=today_start,
            week_ago_start=today_start - timedelta(days=7),
            month_ago_start=today_start - timedelta(days=30),
        )

    @property
    def today_str(self) -> str:
        return self.today_start.strftime("%Y-%m-%d")

    @property
    def prev_day_start(self) -> datetime:
        """Start of the day before the current one (that day ends at ``today_start``)."""
        return self.today_start - timedelta(days=1)

    @property
    def prev_week_start(self) -> datetime:
        """Start of the 7 days before the current week (they end at ``week_ago_start``)."""
        return self.week_ago_start - timedelta(days=7)

    @property
    def prev_month_start(self) -> datetime:
        """Start of the 30 days before the current month (they end at ``month_ago_start``)."""
        return self.month_ago_start - timedelta(days=30)

    @property
    def partial(self) -> bool:
        """True mid-day (a manual /stats): the current window isn't a full day yet."""
        return (self.now - self.today_start).total_seconds() < 23 * 3600


@dataclass(frozen=True)
class DigestRow:
    """What an app adds to the daily digest.

    A table row (``label`` with ``day`` / ``week`` / ``prev_week`` counts) unless ``line`` is set:
    then ``line`` is printed under the table instead. ``line`` is Telegram HTML — escape any
    user-supplied text in it. ``label`` and ``warning`` are plain text (core escapes them);
    ``warning`` is added to the ⚠️ block (app warnings come before core's). A row with an empty
    ``label`` and no ``line`` adds only its warning.
    """

    label: str
    day: int = 0
    week: int = 0
    prev_week: int = 0
    line: str | None = None
    warning: str | None = None


OverviewCardFn = Callable[[AsyncSession, StatWindows], Awaitable[OverviewCard]]
DigestRowFn = Callable[[AsyncSession, StatWindows], Awaitable[DigestRow | None]]

# Insertion order = render order.
_OVERVIEW_CARDS: dict[str, OverviewCardFn] = {}
_DIGEST_ROWS: dict[str, tuple[int, DigestRowFn]] = {}


def register_overview_card(key: str, fn: OverviewCardFn) -> None:
    """Add (or replace) an Overview tile. ``fn(session, window) -> OverviewCard``."""
    _OVERVIEW_CARDS[key] = fn


def register_digest_row(key: str, fn: DigestRowFn, *, order: int = 100) -> None:
    """Add (or replace) a digest row. ``fn(session, window) -> DigestRow | None``.

    ``order`` places a table row among core's (10, 20, 40, 50, 60); lines and warnings keep it too.
    """
    _DIGEST_ROWS[key] = (order, fn)


def overview_card_fns() -> list[OverviewCardFn]:
    """Registered Overview card callbacks, in registration order."""
    return list(_OVERVIEW_CARDS.values())


def digest_row_fns() -> list[tuple[int, DigestRowFn]]:
    """Registered digest row callbacks with their order, sorted by order, then registration."""
    entries = list(_DIGEST_ROWS.values())
    return [entry for _, entry in sorted(enumerate(entries), key=lambda item: (item[1][0], item[0]))]
