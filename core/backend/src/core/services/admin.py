"""Admin Users service: aggregation reads + audited mutations.

Reads shape user rows + per-user sub-lists into the API schemas. Mutations delegate
to the existing domain services (SubscriptionsService gift/cancel, PaymentsService
refund, CASCADE reset) and then record an audit row via
``services.audit_log.record(...)``. The actor's EFFECTIVE role is whatever the
injected ``UserSchema`` carries (resolved server-side by RBAC), never client-supplied.

Gating lives in the router (AdminUser vs OwnerUser); this service assumes the caller
is already authorized and focuses on doing the work + writing the trail. Failures are
raised as domain exceptions (``UserNotFoundException``, ``PaymentNotFoundException``,
``RefundNotAllowedException``, ``ProviderRefundError``); the router maps them to HTTP.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete

from core.exceptions import PaymentNotFoundException, RefundNotAllowedException, UserNotFoundException
from core.infrastructure.config import settings
from core.infrastructure.database.models import User
from core.schemas.admin_common import AdminListParams, AdminListResponse
from core.schemas.admin_users import (
    AdminPaymentListItem,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserSubscription,
    GiftDuration,
)
from core.schemas.users import UserSchema
from core.services.base import BaseService

# Gift duration name -> days (mirrors the Telegram /giftsub command's mapping).
_GIFT_DURATION_DAYS: dict[str, int] = {
    "week": 7,
    "month": 30,
    "year": 365,
    "max": 365 * 5,
}


class AdminService(BaseService):
    # ── Config seam ───────────────────────────────────────────────────────────

    def _owner_ids(self) -> set[int]:
        """Telegram ids forced to OWNER by config (``RBAC__OWNER_IDS``).

        One small seam so tests can ``patch.object(AdminService, "_owner_ids", ...)``
        instead of touching the lazy settings proxy.
        """
        return set(settings.rbac.owner_ids)

    def _is_config_owner(self, user) -> bool:
        return bool(user.telegram_id and user.telegram_id in self._owner_ids())

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def list_users(
        self,
        params: AdminListParams,
        *,
        role: str | None = None,
        user_type: str | None = None,
    ) -> AdminListResponse[AdminUserListItem]:
        rows, total = await self.repo.admin_users.search_users(
            params,
            role=role,
            user_type=user_type,
        )
        items = [AdminUserListItem.model_validate(row) for row in rows]
        return AdminListResponse.build(items, total, params)

    async def get_user_detail(self, user_id: UUID) -> AdminUserDetail | None:
        user = await self.repo.users.get_user_by_id(user_id)
        if user is None:
            return None
        return await self.build_detail(user)

    async def build_detail(self, user) -> AdminUserDetail:
        """Shape a ``User`` row into the admin detail payload (public: apps reuse it)."""
        active_sub = await self.repo.admin_users.get_active_subscription(user.id)
        payments_count = await self.repo.admin_users.count_payments(user.id)

        return AdminUserDetail(
            id=user.id,
            user_type=str(user.user_type),
            role=user.role,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            language_code=user.language_code,
            timezone=user.timezone,
            birth_date=user.birth_date,
            male=user.male,
            telegram_id=user.telegram_id,
            tg_username=user.tg_username,
            tg_first_name=user.tg_first_name,
            tg_is_premium=user.tg_is_premium,
            email=user.email,
            email_verified=user.email_verified,
            current_streak=user.current_streak,
            best_streak=user.best_streak,
            total_active_days=user.total_active_days,
            last_activity_date=user.last_activity_date,
            is_onboarded=user.is_onboarded,
            created_at=user.created_at,
            updated_at=user.updated_at,
            active_subscription=AdminUserSubscription.model_validate(active_sub) if active_sub else None,
            has_active_subscription=active_sub is not None,
            payments_count=payments_count,
            is_config_owner=self._is_config_owner(user),
        )

    async def list_payments(self, user_id: UUID, params: AdminListParams) -> AdminListResponse[AdminPaymentListItem]:
        rows, total = await self.repo.admin_users.list_payments(user_id, params)
        return AdminListResponse.build([_payment_item(p) for p in rows], total, params)

    async def list_subscriptions(self, user_id: UUID) -> list[AdminUserSubscription]:
        rows = await self.repo.admin_users.list_subscriptions(user_id)
        return [AdminUserSubscription.model_validate(s) for s in rows]

    # ── Mutations (each writes an audit row) ───────────────────────────────────

    async def require_user(self, user_id: UUID):
        """Load the user or raise ``UserNotFoundException`` (public: apps reuse it)."""
        user = await self.repo.users.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundException("User not found")
        return user

    async def gift_subscription(self, actor: UserSchema, user_id: UUID, duration: GiftDuration) -> AdminUserDetail:
        """Gift (or extend) a subscription via the SHARED core method, then audit."""
        await self.require_user(user_id)
        duration_days = _GIFT_DURATION_DAYS[duration]

        subscription = await self.services.subscriptions.gift_subscription(
            user_id,
            duration_days,
            gifted_by=actor.id,
        )

        await self.services.audit_log.record(
            actor=actor,
            action="gift_subscription",
            target_type="user",
            target_id=str(user_id),
            detail={
                "duration": duration,
                "duration_days": duration_days,
                "subscription_id": str(subscription.id),
                "end_date": subscription.end_date.isoformat(),
            },
        )
        user = await self.require_user(user_id)
        return await self.build_detail(user)

    async def revoke_subscription(self, actor: UserSchema, user_id: UUID) -> AdminUserDetail:
        """Cancel the user's active subscription (existing cancel flow), then audit."""
        await self.require_user(user_id)

        await self.services.subscriptions.cancel_subscription(user_id, reason="admin_revoked")

        await self.services.audit_log.record(
            actor=actor,
            action="revoke_subscription",
            target_type="user",
            target_id=str(user_id),
            detail={"reason": "admin_revoked"},
        )
        user = await self.require_user(user_id)
        return await self.build_detail(user)

    async def refund_payment(self, actor: UserSchema, payment_id: UUID) -> AdminPaymentListItem:
        """Refund a Stars payment at Telegram and take back what it paid for; audited.

        The audit row is written first: the refund call at Telegram can't be undone, so nothing that
        can fail may run after it. A payment that isn't refundable here raises
        ``RefundNotAllowedException``; the provider refusing raises ``ProviderRefundError``. The
        router turns both into an HTTP error that leaves the request, so the request's transaction
        rolls back and nothing is half-done.
        """
        payment = await self.repo.payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundException("Payment not found")
        await self.services.audit_log.record(
            actor=actor,
            action="refund_payment",
            target_type="user",
            target_id=str(payment.user_id),
            detail={
                "payment_id": str(payment.id),
                "product_id": payment.product_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "provider_id": str(payment.provider_id),
            },
        )
        try:
            payment = await self.services.payments.refund_payment(payment_id)
        except ValueError as e:
            raise RefundNotAllowedException(str(e)) from e
        # ProviderRefundError propagates: nothing changed here. If the provider did refund (the call
        # timed out after it), its refund notice finishes the job (marks the payment and takes back
        # what it gave).
        return _payment_item(payment)

    async def change_role(self, actor: UserSchema, user_id: UUID, new_role: str) -> AdminUserDetail:
        """Change a user's RBAC role (OWNER-gated in the router), then audit.

        NOTE: if the target's telegram_id is in RBAC__OWNER_IDS the change won't stick
        (startup sync forces OWNER) — the detail carries ``is_config_owner`` so the UI
        can warn. We still apply + audit the attempt.
        """
        user = await self.require_user(user_id)
        previous_role = user.role
        config_owner = self._is_config_owner(user)

        await self.repo.users.update_user(user_id, {"role": new_role})

        await self.services.audit_log.record(
            actor=actor,
            action="change_role",
            target_type="user",
            target_id=str(user_id),
            detail={
                "previous_role": previous_role,
                "new_role": new_role,
                "config_owner": config_owner,
            },
        )
        user = await self.require_user(user_id)
        return await self.build_detail(user)

    async def reset_user(self, actor: UserSchema, user_id: UUID) -> None:
        """DEBUG-only hard delete (CASCADE) of a user, then audit.

        Router enforces DEBUG-only + OwnerUser; this is the data-access + audit body.
        Snapshots a little target identity into the audit detail BEFORE the row is gone.
        """
        user = await self.require_user(user_id)
        snapshot = {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "role": user.role,
        }

        await self.repo.session.execute(delete(User).where(User.id == user_id))
        await self.repo.session.flush()

        await self.services.audit_log.record(
            actor=actor,
            action="reset_user",
            target_type="user",
            target_id=str(user_id),
            detail=snapshot,
        )


def _payment_item(p) -> AdminPaymentListItem:
    return AdminPaymentListItem(
        id=p.id,
        product_id=p.product_id,
        provider_id=str(p.provider_id),
        amount=p.amount,
        currency=p.currency,
        status=str(p.status),
        is_recurring=p.is_recurring,
        created_at=p.created_at,
    )
