"""Marketing links: the registry of acquisition codes and the per-code results.

Results come from ``users.referral_code`` (first touch) and ``payments``. What counts as
*activity* is the app's call: ``stats_by_code`` takes two selectables (rows labelled
``user_id``, ``at``) that the service resolves from the app's ``MarketingLinksConfig``;
``default_activity()`` is the fallback (the user opened the app on that day).
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy import TIMESTAMP, CompoundSelect, Select, cast, exists, func, select, text, true
from sqlalchemy.orm import aliased

from core.infrastructure.database.models import MarketingLink, Payment, PaymentProvider, PaymentStatus, User
from core.infrastructure.database.repo.base import BaseRepo

RETENTION_DAYS = (1, 7, 30)


def default_activity() -> Select:
    """Activity when the app defines none: the days the user opened the app.

    ``users.last_activity_date`` is a calendar ``Date`` (set at every app session), so the row's
    ``at`` is the END of that day: "active on calendar day >= sign-up day + N" counts as returned
    after N days. (Midnight would undercount every ``returned_dN`` by about a day.)
    """
    return select(
        User.id.label("user_id"),
        cast(User.last_activity_date + timedelta(days=1), TIMESTAMP(timezone=True)).label("at"),
    ).where(User.last_activity_date.isnot(None))


class MarketingLinkRepo(BaseRepo[MarketingLink]):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = MarketingLink

    async def get_by_code(self, code: str) -> MarketingLink | None:
        return (
            await self.session.execute(select(MarketingLink).where(MarketingLink.code == code))
        ).scalar_one_or_none()

    async def list_all(self) -> Sequence[MarketingLink]:
        return (
            (await self.session.execute(select(MarketingLink).order_by(MarketingLink.created_at.desc())))
            .scalars()
            .all()
        )

    async def stats_by_code(
        self, *, activation: Select | CompoundSelect, activity: Select | CompoundSelect
    ) -> dict[str, dict[str, Any]]:
        """Per acquisition code (users.referral_code, first touch): users, activated, payers,
        first/last sign-up, and retention: of the users signed up at least N days ago
        (eligible_dN), how many were active N or more days after signing up (returned_dN).

        ``activation`` rows make a user `activated`; ``activity`` rows (their latest ``at``) decide
        retention. Both are joined per user (correlated EXISTS / LATERAL), so Postgres pushes the
        user filter into them and uses their ``user_id`` indexes. Gifts (provider GIFT) aren't payments.
        """
        u = aliased(User, name="u")
        act = activation.subquery("act")
        acts = activity.subquery("acts")
        activated = exists(select(act.c.user_id).where(act.c.user_id == u.id))
        last = select(func.max(acts.c.at).label("last_active_at")).where(acts.c.user_id == u.id).lateral("a")
        paid = exists(
            select(Payment.id).where(
                Payment.user_id == u.id,
                Payment.status == PaymentStatus.SUCCEEDED,
                Payment.provider_id != PaymentProvider.GIFT,
            )
        )
        cols: list[Any] = [
            u.referral_code.label("code"),
            func.count().label("users"),
            func.count().filter(activated).label("activated"),
            func.count().filter(paid).label("payers"),
            func.min(u.created_at).label("first_user_at"),
            func.max(u.created_at).label("last_user_at"),
        ]
        for n in RETENTION_DAYS:
            old_enough = u.created_at <= func.now() - timedelta(days=n)
            came_back = last.c.last_active_at >= u.created_at + timedelta(days=n)
            cols += [
                func.count().filter(old_enough).label(f"eligible_d{n}"),
                func.count().filter(old_enough & came_back).label(f"returned_d{n}"),
            ]
        stmt = (
            select(*cols).select_from(u).join(last, true()).where(u.referral_code.isnot(None)).group_by(u.referral_code)
        )
        rows = await self.session.execute(stmt)
        return {row.code: row._asdict() for row in rows}

    async def payments_by_code(self) -> Sequence[Any]:
        """Every SUCCEEDED non-gift payment of a user with an acquisition code, oldest first: code,
        currency, amount, created_at, is_purchase (made by the user, not an automatic renewal
        charge). REFUNDED payments drop out by status."""
        rows = await self.session.execute(
            text(
                """
                SELECT u.referral_code AS code, p.currency, p.amount, p.created_at, NOT p.is_recurring AS is_purchase
                FROM payments p JOIN users u ON u.id = p.user_id
                WHERE p.status = 'SUCCEEDED' AND p.provider_id <> 'GIFT' AND u.referral_code IS NOT NULL
                ORDER BY p.created_at
                """
            )
        )
        return rows.all()
