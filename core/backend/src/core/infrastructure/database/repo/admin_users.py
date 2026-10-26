"""Read-only repository for the admin Users section.

Search/filter/paginate over the ``User`` table plus the per-user payment and
subscription sub-lists and the detail rollups. ``sort_by`` is whitelisted via the
``_SORTABLE`` dict (never interpolated raw).

App-specific per-user data (an app's own tables) lives in an app repo next to its
own admin endpoints, not here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select

from core.infrastructure.database.models import Payment, Subscription, User
from core.infrastructure.database.models.enums import SubscriptionStatus
from core.infrastructure.database.repo.admin_list import admin_list_count, apply_admin_list
from core.infrastructure.database.repo.base import BaseRepo
from core.schemas.admin_common import AdminListParams


class AdminUsersRepo(BaseRepo[User]):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = User

    # Whitelisted sortable columns for the user list (first entry = default sort).
    _SORTABLE = {
        "created_at": User.created_at,
        "updated_at": User.updated_at,
        "current_streak": User.current_streak,
        "best_streak": User.best_streak,
        "total_active_days": User.total_active_days,
        "username": User.username,
        "role": User.role,
    }
    _SEARCHABLE = [User.username, User.tg_username, User.display_name, User.email]

    def _apply_user_filters(
        self,
        stmt: Select,
        *,
        role: str | None,
        user_type: str | None,
    ) -> Select:
        if role is not None:
            stmt = stmt.where(User.role == role)
        if user_type is not None:
            stmt = stmt.where(User.user_type == user_type)
        return stmt

    async def search_users(
        self,
        params: AdminListParams,
        *,
        role: str | None = None,
        user_type: str | None = None,
    ) -> tuple[list[User], int]:
        """Filtered + paginated user rows plus the unpaginated total.

        Free-text search comes from ``params.search`` (ILIKE across ``_SEARCHABLE``);
        ``role`` / ``user_type`` are exact filters applied before the generic
        search/sort/paginate.
        """
        base = self._apply_user_filters(select(User), role=role, user_type=user_type)

        list_stmt = apply_admin_list(
            base,
            params,
            sortable=self._SORTABLE,
            searchable=self._SEARCHABLE,
            date_column=User.created_at,
        )
        count_stmt = admin_list_count(
            base,
            params,
            searchable=self._SEARCHABLE,
            date_column=User.created_at,
        )

        rows = (await self.session.execute(list_stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    # ── Per-user sub-lists ────────────────────────────────────────────────────

    async def list_payments(self, user_id: UUID, params: AdminListParams) -> tuple[list[Payment], int]:
        base = select(Payment).where(Payment.user_id == user_id)
        sortable = {"created_at": Payment.created_at, "amount": Payment.amount, "status": Payment.status}
        list_stmt = apply_admin_list(base, params, sortable=sortable, searchable=[], date_column=Payment.created_at)
        count_stmt = admin_list_count(base, params, searchable=[], date_column=Payment.created_at)
        rows = (await self.session.execute(list_stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def list_subscriptions(self, user_id: UUID) -> list[Subscription]:
        stmt = select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.start_date.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    # ── Detail aggregation helpers ────────────────────────────────────────────

    async def get_active_subscription(self, user_id: UUID) -> Subscription | None:
        """The user's current entitled subscription, if any.

        Entitled = ACTIVE, PAST_DUE or CANCELED (a canceled sub runs to its end date)
        with ``end_date`` still in the future. Latest-ending first.
        """
        stmt = (
            select(Subscription)
            .where(
                (Subscription.user_id == user_id)
                & (
                    Subscription.status.in_(
                        (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELED)
                    )
                )
                & (Subscription.end_date > datetime.now(UTC))
            )
            .order_by(Subscription.end_date.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_payments(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Payment).where(Payment.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one()
