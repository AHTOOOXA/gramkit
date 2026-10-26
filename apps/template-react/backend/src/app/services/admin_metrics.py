"""This app's numbers on the admin Overview and in the daily owner digest.

Core gathers the generic numbers (users, revenue, product sales, subscriptions, DAU/WAU/MAU —
``core.services.statistics``). Add your own through core's registries
(``core.services.admin_metrics``) inside ``register_admin_metrics()``, which
``setup_infrastructure()`` runs in the webhook (Overview), the bot (``/stats``) and the worker
(the daily digest). Nothing is registered yet.

A callback gets the request's (or job's) ``AsyncSession`` and the stat windows
(``StatWindows``: ``today_start`` = the last 02:00 UTC, ``week_ago_start``, ``month_ago_start``,
``prev_*_start``, ``partial``). Keep it read-only, and build your own repo from the session.
Callbacks run one after another on that session, so never ``asyncio.gather`` inside them.

Example — an Overview tile and a digest row::

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.infrastructure.database.repo.requests import RequestsRepo
    from core.schemas.statistics import OverviewCard
    from core.services.admin_metrics import DigestRow, StatWindows, register_digest_row, register_overview_card


    async def signups_card(session: AsyncSession, window: StatWindows) -> OverviewCard:
        users = RequestsRepo(session).users
        return OverviewCard(
            key="signupsThisWeek",  # frontend label: admin.overview.kpi.signupsThisWeek (else `label`)
            section="growth",  # frontend title: admin.overview.sections.growth
            label="Signups this week",
            value=await users.get_new_users_count(window.week_ago_start, window.now),
            previous=await users.get_new_users_count(window.prev_week_start, window.week_ago_start),
        )


    async def onboarded_row(session: AsyncSession, window: StatWindows) -> DigestRow | None:
        ...  # count something per window
        return DigestRow("Onboarded", day=3, week=20, prev_week=18)  # a table row; or line=... / warning=...


    def register_admin_metrics() -> None:
        register_overview_card("signupsThisWeek", signups_card)
        register_digest_row("onboarded", onboarded_row, order=30)  # 30 = between New users (20) and Purchases (40)
"""


def register_admin_metrics() -> None:
    """Register this app's Overview cards and digest rows in core (none yet; see the module docstring)."""
