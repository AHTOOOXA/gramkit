"""Integration tests for AdminService on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session))`` directly (core has no
``services`` fixture). Config owners come through the ``_owner_ids`` seam, patched
with ``patch.object`` — never through the lazy ``settings`` proxy, which would import
``app`` and fail core CI.
"""

import random
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PaymentNotFoundException, RefundNotAllowedException, UserNotFoundException
from core.infrastructure.database.models import AuditLog, User
from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus, UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.users import UserSchema
from core.services.admin import AdminService
from core.services.payments.types import ProviderRefundError
from core.services.requests import CoreRequestsService


@pytest.fixture
def core_services(db_session: AsyncSession) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session))


async def _seed_user(services: CoreRequestsService, role: UserRole = UserRole.USER) -> User:
    user = await services.repo.users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"svc_{uuid4().hex[:8]}",
            "role": role,
        }
    )
    await services.repo.session.flush()
    return user


async def _actor(services: CoreRequestsService) -> UserSchema:
    return UserSchema.model_validate(await _seed_user(services, role=UserRole.OWNER))


async def _audit_rows(services: CoreRequestsService, action: str, target_id: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.action == action, AuditLog.target_id == target_id)
    return list((await services.repo.session.execute(stmt)).scalars().all())


class TestBuildDetail:
    @pytest.mark.business_logic
    async def test_is_config_owner_true_for_configured_telegram_id(self, core_services: CoreRequestsService):
        user = await _seed_user(core_services)

        with patch.object(AdminService, "_owner_ids", return_value={user.telegram_id}):
            detail = await core_services.admin.get_user_detail(user.id)

        assert detail is not None
        assert detail.is_config_owner is True
        assert detail.has_active_subscription is False
        assert detail.payments_count == 0

    @pytest.mark.business_logic
    async def test_is_config_owner_false_otherwise(self, core_services: CoreRequestsService):
        user = await _seed_user(core_services)

        with patch.object(AdminService, "_owner_ids", return_value=set()):
            detail = await core_services.admin.build_detail(user)

        assert detail.is_config_owner is False

    @pytest.mark.business_logic
    async def test_get_user_detail_unknown_user_returns_none(self, core_services: CoreRequestsService):
        assert await core_services.admin.get_user_detail(uuid4()) is None


class TestRequireUser:
    @pytest.mark.business_logic
    async def test_require_user_raises_for_unknown_id(self, core_services: CoreRequestsService):
        with pytest.raises(UserNotFoundException, match="User not found"):
            await core_services.admin.require_user(uuid4())

    @pytest.mark.business_logic
    async def test_require_user_returns_row(self, core_services: CoreRequestsService):
        user = await _seed_user(core_services)
        assert (await core_services.admin.require_user(user.id)).id == user.id


class TestChangeRole:
    @pytest.mark.business_logic
    async def test_change_role_applies_and_audits_config_owner(self, core_services: CoreRequestsService):
        actor = await _actor(core_services)
        target = await _seed_user(core_services)

        with patch.object(AdminService, "_owner_ids", return_value={target.telegram_id}):
            detail = await core_services.admin.change_role(actor, target.id, "admin")

        assert detail.role == "admin"
        rows = await _audit_rows(core_services, "change_role", str(target.id))
        assert len(rows) == 1
        assert rows[0].actor_user_id == actor.id
        assert rows[0].actor_role == actor.role
        assert rows[0].target_type == "user"
        assert rows[0].detail == {"previous_role": "user", "new_role": "admin", "config_owner": True}

    @pytest.mark.business_logic
    async def test_change_role_unknown_user_raises_and_writes_nothing(self, core_services: CoreRequestsService):
        actor = await _actor(core_services)
        missing = uuid4()

        with pytest.raises(UserNotFoundException):
            await core_services.admin.change_role(actor, missing, "admin")

        assert await _audit_rows(core_services, "change_role", str(missing)) == []


class TestResetUser:
    @pytest.mark.business_logic
    async def test_reset_deletes_user_and_audit_row_survives(self, core_services: CoreRequestsService):
        actor = await _actor(core_services)
        target = await _seed_user(core_services)
        target_id = target.id

        await core_services.admin.reset_user(actor, target_id)

        assert await core_services.repo.users.get_user_by_id(target_id) is None
        rows = await _audit_rows(core_services, "reset_user", str(target_id))
        assert len(rows) == 1
        assert rows[0].detail is not None
        assert rows[0].detail["role"] == "user"


class TestRefundPayment:
    """Error mapping of the refund path (the provider call itself is mocked)."""

    async def _seed_payment(self, services: CoreRequestsService) -> str:
        user = await _seed_user(services)
        payment = await services.repo.payments.create(
            {
                "user_id": user.id,
                "product_id": "TEST_PRODUCT",
                "provider_id": PaymentProvider.TELEGRAM_STARS,
                "amount": 100.0,
                "currency": "XTR",
                "status": PaymentStatus.SUCCEEDED,
                "provider_metadata": {},
            }
        )
        await services.repo.session.flush()
        return payment.id

    @pytest.mark.business_logic
    async def test_unknown_payment_raises_not_found(self, core_services: CoreRequestsService):
        actor = await _actor(core_services)
        with pytest.raises(PaymentNotFoundException, match="Payment not found"):
            await core_services.admin.refund_payment(actor, uuid4())

    @pytest.mark.business_logic
    async def test_value_error_becomes_refund_not_allowed(self, core_services: CoreRequestsService):
        actor = await _actor(core_services)
        payment_id = await self._seed_payment(core_services)
        core_services.__dict__["payments"] = MagicMock(
            refund_payment=AsyncMock(side_effect=ValueError("can't be refunded from here"))
        )

        with pytest.raises(RefundNotAllowedException, match="can't be refunded from here"):
            await core_services.admin.refund_payment(actor, payment_id)

    @pytest.mark.business_logic
    async def test_provider_error_propagates_after_audit_row(self, core_services: CoreRequestsService):
        """The audit row is written BEFORE the provider call; the provider error propagates
        unchanged so the router can raise (and the request transaction rolls both back)."""
        actor = await _actor(core_services)
        payment_id = await self._seed_payment(core_services)
        core_services.__dict__["payments"] = MagicMock(
            refund_payment=AsyncMock(side_effect=ProviderRefundError("telegram said no"))
        )

        with pytest.raises(ProviderRefundError):
            await core_services.admin.refund_payment(actor, payment_id)

        stmt = select(AuditLog).where(AuditLog.action == "refund_payment", AuditLog.actor_user_id == actor.id)
        rows = list((await core_services.repo.session.execute(stmt)).scalars().all())
        assert len(rows) == 1
        assert rows[0].detail is not None
        assert rows[0].detail["payment_id"] == str(payment_id)
