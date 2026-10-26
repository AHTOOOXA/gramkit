"""Base test class for the core admin API contract tests.

Covers every endpoint of ``core.infrastructure.fastapi.routers.admin``: RBAC meta,
audit log, admin tasks, users list/detail/sub-lists, gift, revoke, role change, reset
and refund. The task tests register a uniquely named probe task (``probe_task``), so
they need no app task and stay parallel-safe.

Rule: every Owner-gated endpoint (role, reset, refund) has an ``admin_client`` -> 403
test, and every Admin-gated endpoint has an ``authenticated_client`` -> 403 test.

Apps inherit this class and provide the fixtures:
- ``authenticated_client``: regular (non-admin) Telegram-authenticated client
- ``admin_client`` / ``owner_client``: from ``core.testing.fixtures`` (need ``test_app``)
- ``db_session``: the session the app's ``test_app`` is wired to

Types and relations are asserted (never hardcoded ids) so the suite stays parallel-safe.
"""

import random
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus, UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services import admin_tasks
from core.services.admin_tasks import AdminTask


async def _seed_user(db_session: AsyncSession, username: str | None = None) -> str:
    """Insert a throwaway target user; return its id (str)."""
    repo = CoreRequestsRepo(db_session)
    user = await repo.users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": username or f"target_{uuid4().hex[:8]}",
            "role": UserRole.USER,
        }
    )
    await db_session.flush()
    return str(user.id)


async def _seed_card_payment(db_session: AsyncSession, user_id: str) -> str:
    """A SUCCEEDED YooKassa payment: refunds for it are made in YooKassa's dashboard, not here."""
    repo = CoreRequestsRepo(db_session)
    payment = await repo.payments.create(
        {
            "user_id": user_id,
            "product_id": "TEST_PRODUCT",
            "provider_id": PaymentProvider.YOOKASSA,
            "amount": 555.0,
            "currency": "RUB",
            "status": PaymentStatus.SUCCEEDED,
            "provider_metadata": {},
        }
    )
    await db_session.flush()
    return str(payment.id)


async def _audit_rows(client: AsyncClient, action: str, user_id: str) -> list[dict]:
    response = await client.get(f"/admin/audit-log?action={action}&target_user_id={user_id}")
    assert response.status_code == 200
    return response.json()["items"]


class BaseAdminTests:
    """Base class for core admin API contract tests."""

    # =========================================================================
    # RBAC meta
    # =========================================================================

    @pytest.mark.contract
    async def test_rbac_meta_returns_admin_capabilities(self, admin_client: AsyncClient):
        """GET /admin/meta/rbac returns the admin's effective capabilities."""
        response = await admin_client.get("/admin/meta/rbac")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["role"], str)
        assert data["is_admin"] is True
        assert isinstance(data["is_owner"], bool)
        # Admin (not owner) cannot perform destructive actions.
        assert data["can_perform_destructive"] == data["is_owner"]

    @pytest.mark.contract
    async def test_rbac_meta_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/meta/rbac")
        assert response.status_code == 403

    # =========================================================================
    # Audit log
    # =========================================================================

    @pytest.mark.contract
    async def test_audit_log_returns_paginated_envelope(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/audit-log")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1
        assert isinstance(data["page_size"], int)
        assert isinstance(data["total_pages"], int)

    @pytest.mark.contract
    async def test_audit_log_echoes_pagination_params(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/audit-log?page=2&page_size=5")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    @pytest.mark.contract
    async def test_audit_log_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/audit-log")
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_audit_actions_lists_recorded_actions(self, admin_client: AsyncClient, db_session: AsyncSession):
        """GET /admin/audit-log/actions returns the distinct recorded actions as strings."""
        user_id = await _seed_user(db_session)
        await admin_client.post(f"/admin/users/{user_id}/gift-subscription", json={"duration": "week"})

        response = await admin_client.get("/admin/audit-log/actions")

        assert response.status_code == 200
        actions = response.json()
        assert isinstance(actions, list)
        assert all(isinstance(a, str) for a in actions)
        assert "gift_subscription" in actions

    @pytest.mark.contract
    async def test_audit_actions_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/audit-log/actions")
        assert response.status_code == 403

    # =========================================================================
    # Tasks (list: AdminUser, run: OwnerUser)
    # =========================================================================

    @pytest.fixture
    def probe_task(self, monkeypatch) -> tuple[str, list[bool]]:
        """Register a uniquely named destructive probe task; return (name, recorded dry_run flags)."""
        name = f"contract_probe_{uuid4().hex[:8]}"
        calls: list[bool] = []

        async def _run(session: AsyncSession, *, dry_run: bool) -> dict:
            calls.append(dry_run)
            return {"applied": not dry_run, "probe": True}

        monkeypatch.setitem(
            admin_tasks._REGISTRY,
            name,
            AdminTask(name=name, description="Contract probe.", destructive=True, run=_run),
        )
        return name, calls

    @pytest.mark.contract
    async def test_tasks_list_includes_registered_task(
        self, admin_client: AsyncClient, probe_task: tuple[str, list[bool]]
    ):
        name, _ = probe_task

        response = await admin_client.get("/admin/tasks")

        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        assert all(set(task) == {"name", "description", "destructive"} for task in tasks)
        probe = next(task for task in tasks if task["name"] == name)
        assert probe["destructive"] is True
        assert probe["description"] == "Contract probe."

    @pytest.mark.contract
    async def test_tasks_list_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/tasks")
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_run_task_forbidden_for_admin(self, admin_client: AsyncClient, probe_task: tuple[str, list[bool]]):
        name, calls = probe_task

        response = await admin_client.post(f"/admin/tasks/{name}", json={})

        assert response.status_code == 403
        assert calls == []

    @pytest.mark.contract
    async def test_run_task_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, probe_task: tuple[str, list[bool]]
    ):
        name, calls = probe_task

        response = await authenticated_client.post(f"/admin/tasks/{name}", json={})

        assert response.status_code == 403
        assert calls == []

    @pytest.mark.contract
    async def test_run_unknown_task_404(self, owner_client: AsyncClient):
        name = f"no_such_task_{uuid4().hex[:8]}"

        response = await owner_client.post(f"/admin/tasks/{name}", json={})

        assert response.status_code == 404
        assert response.json()["detail"] == f"Unknown task: {name}"

    @pytest.mark.contract
    async def test_run_task_defaults_to_dry_run(self, owner_client: AsyncClient, probe_task: tuple[str, list[bool]]):
        name, calls = probe_task

        response = await owner_client.post(f"/admin/tasks/{name}", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["task"] == name
        assert data["dry_run"] is True
        assert data["result"] == {"applied": False, "probe": True}
        assert calls == [True]

    @pytest.mark.contract
    async def test_run_task_apply(self, owner_client: AsyncClient, probe_task: tuple[str, list[bool]]):
        name, calls = probe_task

        response = await owner_client.post(f"/admin/tasks/{name}", json={"dry_run": False})

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is False
        assert data["result"] == {"applied": True, "probe": True}
        assert calls == [False]

    @pytest.mark.contract
    async def test_run_task_writes_audit_row(self, owner_client: AsyncClient, probe_task: tuple[str, list[bool]]):
        """Every run is audit-logged as ``admin_task:<name>`` with ``{"dry_run", "result"}``."""
        name, _ = probe_task
        await owner_client.post(f"/admin/tasks/{name}", json={})

        response = await owner_client.get(f"/admin/audit-log?action=admin_task:{name}")

        assert response.status_code == 200
        rows = response.json()["items"]
        assert len(rows) == 1
        assert rows[0]["actor_role"] == "owner"
        assert rows[0]["target_type"] == "admin_task"
        assert rows[0]["target_id"] == name
        assert rows[0]["detail"] == {"dry_run": True, "result": {"applied": False, "probe": True}}

    # =========================================================================
    # Users list
    # =========================================================================

    @pytest.mark.contract
    async def test_users_list_returns_paginated_envelope(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1

    @pytest.mark.contract
    async def test_users_list_role_filter_narrows_rows(self, admin_client: AsyncClient, db_session: AsyncSession):
        await _seed_user(db_session)

        response = await admin_client.get("/admin/users?role=admin")

        assert response.status_code == 200
        items = response.json()["items"]
        assert items  # the admin client's own user
        assert all(item["role"] == "admin" for item in items)

    @pytest.mark.contract
    async def test_users_list_search_finds_seeded_username(self, admin_client: AsyncClient, db_session: AsyncSession):
        username = f"needle_{uuid4().hex[:8]}"
        user_id = await _seed_user(db_session, username=username)

        response = await admin_client.get(f"/admin/users?search={username}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == user_id
        assert data["items"][0]["username"] == username

    @pytest.mark.contract
    async def test_users_list_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/users")
        assert response.status_code == 403

    # =========================================================================
    # User detail
    # =========================================================================

    @pytest.mark.contract
    async def test_user_detail_returns_core_fields(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)

        response = await admin_client.get(f"/admin/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["role"] == "user"
        assert isinstance(data["user_type"], str)
        assert isinstance(data["payments_count"], int)
        assert data["active_subscription"] is None
        assert data["has_active_subscription"] is False
        assert isinstance(data["is_config_owner"], bool)
        # App-specific data is served by app endpoints, never on the core detail.
        assert "balance" not in data

    @pytest.mark.contract
    async def test_user_detail_unknown_user_404(self, admin_client: AsyncClient):
        response = await admin_client.get(f"/admin/users/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    @pytest.mark.contract
    async def test_user_detail_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.get(f"/admin/users/{user_id}")
        assert response.status_code == 403

    # =========================================================================
    # Per-user sub-lists
    # =========================================================================

    @pytest.mark.contract
    async def test_user_payments_returns_envelope(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)
        await _seed_card_payment(db_session, user_id)

        response = await admin_client.get(f"/admin/users/{user_id}/payments")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert isinstance(data["items"][0]["status"], str)
        assert data["items"][0]["amount"] == 555.0

    @pytest.mark.contract
    async def test_user_subscriptions_returns_list(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)
        response = await admin_client.get(f"/admin/users/{user_id}/subscriptions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.contract
    async def test_user_payments_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.get(f"/admin/users/{user_id}/payments")
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_user_subscriptions_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.get(f"/admin/users/{user_id}/subscriptions")
        assert response.status_code == 403

    # =========================================================================
    # Gift / revoke (AdminUser)
    # =========================================================================

    @pytest.mark.contract
    async def test_gift_subscription_activates_and_audits(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)

        response = await admin_client.post(f"/admin/users/{user_id}/gift-subscription", json={"duration": "week"})

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_subscription"] is True
        assert isinstance(data["active_subscription"]["status"], str)

        rows = await _audit_rows(admin_client, "gift_subscription", user_id)
        assert len(rows) == 1
        assert rows[0]["actor_role"] == "admin"
        assert rows[0]["detail"]["duration"] == "week"

    @pytest.mark.contract
    async def test_gift_subscription_unknown_user_404(self, admin_client: AsyncClient):
        response = await admin_client.post(f"/admin/users/{uuid4()}/gift-subscription", json={"duration": "week"})
        assert response.status_code == 404

    @pytest.mark.contract
    async def test_gift_subscription_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.post(
            f"/admin/users/{user_id}/gift-subscription", json={"duration": "week"}
        )
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_revoke_subscription_audits(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)
        # Gift first so there is something to revoke.
        await admin_client.post(f"/admin/users/{user_id}/gift-subscription", json={"duration": "week"})

        response = await admin_client.post(f"/admin/users/{user_id}/revoke-subscription")

        assert response.status_code == 200
        rows = await _audit_rows(admin_client, "revoke_subscription", user_id)
        assert len(rows) == 1
        assert rows[0]["detail"] == {"reason": "admin_revoked"}

    @pytest.mark.contract
    async def test_revoke_subscription_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.post(f"/admin/users/{user_id}/revoke-subscription")
        assert response.status_code == 403

    # =========================================================================
    # Role change (OwnerUser)
    # =========================================================================

    @pytest.mark.contract
    async def test_owner_changes_role_and_audits(self, owner_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)

        response = await owner_client.post(f"/admin/users/{user_id}/role", json={"new_role": "admin"})

        assert response.status_code == 200
        assert response.json()["role"] == "admin"
        rows = await _audit_rows(owner_client, "change_role", user_id)
        assert len(rows) == 1
        assert rows[0]["actor_role"] == "owner"
        assert rows[0]["detail"]["previous_role"] == "user"
        assert rows[0]["detail"]["new_role"] == "admin"

    @pytest.mark.contract
    async def test_role_change_forbidden_for_admin(self, admin_client: AsyncClient, db_session: AsyncSession):
        user_id = await _seed_user(db_session)
        response = await admin_client.post(f"/admin/users/{user_id}/role", json={"new_role": "admin"})
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_role_change_forbidden_for_non_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _seed_user(db_session)
        response = await authenticated_client.post(f"/admin/users/{user_id}/role", json={"new_role": "admin"})
        assert response.status_code == 403

    # =========================================================================
    # Reset (OwnerUser, DEBUG-only)
    # =========================================================================

    @pytest.mark.contract
    async def test_reset_404_when_not_debug(self, owner_client: AsyncClient, db_session: AsyncSession, monkeypatch):
        """With DEBUG off the endpoint is invisible (404) even for an owner."""
        monkeypatch.setattr(settings, "debug", False)
        user_id = await _seed_user(db_session)

        response = await owner_client.post(f"/admin/users/{user_id}/reset")

        assert response.status_code == 404

    @pytest.mark.contract
    async def test_reset_forbidden_for_admin_when_debug(
        self, admin_client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        """DEBUG on, so a 404 can't mask the gate: an admin (not owner) gets 403."""
        monkeypatch.setattr(settings, "debug", True)
        user_id = await _seed_user(db_session)

        response = await admin_client.post(f"/admin/users/{user_id}/reset")

        assert response.status_code == 403

    @pytest.mark.contract
    async def test_owner_resets_user_when_debug_and_audit_survives(
        self, owner_client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        """With DEBUG on, an owner hard-deletes the user (204); the audit row outlives it."""
        monkeypatch.setattr(settings, "debug", True)
        user_id = await _seed_user(db_session)

        response = await owner_client.post(f"/admin/users/{user_id}/reset")

        assert response.status_code == 204
        assert (await owner_client.get(f"/admin/users/{user_id}")).status_code == 404
        rows = await _audit_rows(owner_client, "reset_user", user_id)
        assert len(rows) == 1
        assert rows[0]["target_id"] == user_id
        assert rows[0]["detail"]["role"] == "user"

    @pytest.mark.contract
    async def test_owner_cannot_reset_self_when_debug(self, owner_client: AsyncClient, monkeypatch):
        """Self-reset is refused (400) and the owner's account survives."""
        monkeypatch.setattr(settings, "debug", True)
        owner_id = (await owner_client.get("/users/me")).json()["id"]

        response = await owner_client.post(f"/admin/users/{owner_id}/reset")

        assert response.status_code == 400
        assert response.json()["detail"] == "Can't reset your own account"
        assert (await owner_client.get(f"/admin/users/{owner_id}")).status_code == 200

    @pytest.mark.contract
    async def test_reset_unknown_user_404_when_debug(self, owner_client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "debug", True)
        response = await owner_client.post(f"/admin/users/{uuid4()}/reset")
        assert response.status_code == 404

    # =========================================================================
    # Refund (OwnerUser)
    # =========================================================================

    @pytest.mark.contract
    async def test_refund_forbidden_for_admin(self, admin_client: AsyncClient, db_session: AsyncSession):
        payment_id = await _seed_card_payment(db_session, await _seed_user(db_session))
        response = await admin_client.post(f"/admin/payments/{payment_id}/refund")
        assert response.status_code == 403

    @pytest.mark.contract
    async def test_refund_unknown_payment_404(self, owner_client: AsyncClient):
        response = await owner_client.post(f"/admin/payments/{uuid4()}/refund")
        assert response.status_code == 404
        assert response.json()["detail"] == "Payment not found"

    @pytest.mark.contract
    async def test_refund_of_card_payment_is_refused(self, owner_client: AsyncClient, db_session: AsyncSession):
        """A provider without a refund API here -> 400 with the service's reason."""
        payment_id = await _seed_card_payment(db_session, await _seed_user(db_session))

        response = await owner_client.post(f"/admin/payments/{payment_id}/refund")

        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)
