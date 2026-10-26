"""Base test class for the core admin marketing-links API contract tests.

Covers every endpoint of ``core.infrastructure.fastapi.routers.admin_marketing_links``
(served under ``/admin`` through ``routers.admin``):

  GET   /admin/marketing-links              (A)
  POST  /admin/marketing-links              (A)  (400: already registered)
  PATCH /admin/marketing-links/{link_id}    (A)  (404: unknown id)

plus the per-code results (users, payers, revenue, economics) and the audit rows of the
mutating endpoints. What counts as *activated* / *returned* is app-defined, so those are
asserted by shape only.

Rule: every endpoint has an ``authenticated_client`` -> 403 test.

Apps inherit this class and provide the fixtures:
- ``authenticated_client``: regular (non-admin) Telegram-authenticated client
- ``admin_client``: from ``core.testing.fixtures`` (needs ``test_app``)
- ``db_session``: the session the app's ``test_app`` is wired to (rolled back after each test)

Codes are unique per test (``t_<hex>``) and rows are found by code, so the suite stays
parallel-safe on a shared database.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus
from core.infrastructure.database.repo.requests import CoreRequestsRepo

URL = "/admin/marketing-links"


def _code() -> str:
    return f"t_{uuid4().hex[:10]}"


async def _user_from(db_session: AsyncSession, code: str, *, created_at: datetime | None = None):
    """A user whose first touch was ``code``."""
    data: dict = {"username": f"u_{uuid4().hex[:8]}", "referral_code": code}
    if created_at:
        data["created_at"] = created_at
    user = await CoreRequestsRepo(db_session).users.create(data)
    await db_session.flush()
    return user


async def _pay(
    db_session: AsyncSession,
    user,
    *,
    amount: float,
    currency: str = "RUB",
    provider: PaymentProvider = PaymentProvider.YOOKASSA,
    at: datetime | None = None,
    renewal: bool = False,
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
) -> None:
    payment = await CoreRequestsRepo(db_session).payments.create(
        {
            "user_id": user.id,
            "product_id": "TEST_PRODUCT",
            "provider_id": provider,
            "amount": amount,
            "currency": currency,
            "status": status,
            "is_recurring": renewal,
            "provider_metadata": {},
        }
    )
    if at:
        payment.created_at = at
    await db_session.flush()


def _by_code(listing: dict, code: str) -> dict:
    return next(item for item in listing["items"] if item["code"] == code)


async def _listing(client: AsyncClient) -> dict:
    response = await client.get(URL)
    assert response.status_code == 200, response.text
    return response.json()


async def _audit_rows(client: AsyncClient, action: str, code: str) -> list[dict]:
    """Audit rows of ``action`` for one code. (The audit log's ``target_user_id`` filter only
    matches ``target_type == "user"``, so filter by action and match ``target_id`` here; the
    rows of other tests aren't visible because ``db_session`` rolls back after each test.)"""
    response = await client.get(f"/admin/audit-log?action={action}&page_size=100")
    assert response.status_code == 200, response.text
    return [row for row in response.json()["items"] if row["target_id"] == code]


class BaseMarketingLinksTests:
    """Base class for core admin marketing-links API contract tests."""

    # =========================================================================
    # Create
    # =========================================================================

    @pytest.mark.contract
    async def test_create_returns_both_links(self, admin_client: AsyncClient):
        code = _code()
        response = await admin_client.post(URL, json={"code": code, "channel": "Test channel"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["registered"] is True
        assert isinstance(body["id"], int)
        assert body["code"] == code
        assert body["channel"] == "Test channel"
        assert body["app_link"].endswith(f"?startapp=r-{code}")
        assert body["bot_link"].endswith(f"?start={code}")

    @pytest.mark.contract
    async def test_only_the_code_is_required(self, admin_client: AsyncClient):
        response = await admin_client.post(URL, json={"code": _code()})
        assert response.status_code == 200, response.text
        assert response.json()["channel"] is None
        assert response.json()["price_rub"] is None

    @pytest.mark.contract
    async def test_create_normalises_the_code(self, admin_client: AsyncClient):
        code = _code()
        response = await admin_client.post(URL, json={"code": f"  {code.upper()} "})
        assert response.status_code == 200, response.text
        assert response.json()["code"] == code

    @pytest.mark.contract
    async def test_create_writes_audit_row(self, admin_client: AsyncClient):
        code = _code()
        await admin_client.post(URL, json={"code": code, "channel": "x"})
        rows = await _audit_rows(admin_client, "marketing_link_create", code)
        assert len(rows) == 1
        assert rows[0]["target_type"] == "marketing_link"
        assert rows[0]["actor_role"] == "admin"

    # =========================================================================
    # Code rules
    # =========================================================================

    @pytest.mark.contract
    @pytest.mark.parametrize("bad", ["Bad-Code", "a", "a-b", "x" * 41, "кот_1"])
    async def test_malformed_codes_are_422(self, admin_client: AsyncClient, bad: str):
        assert (await admin_client.post(URL, json={"code": bad})).status_code == 422

    @pytest.mark.contract
    async def test_duplicate_code_is_400(self, admin_client: AsyncClient):
        code = _code()
        assert (await admin_client.post(URL, json={"code": code})).status_code == 200
        response = await admin_client.post(URL, json={"code": code, "channel": "again"})
        assert response.status_code == 400
        assert response.json()["detail"] == "This code is already registered"

    # =========================================================================
    # Update
    # =========================================================================

    @pytest.mark.contract
    async def test_archive_and_edit_channel(self, admin_client: AsyncClient):
        created = (await admin_client.post(URL, json={"code": _code(), "channel": "x"})).json()
        updated = await admin_client.patch(f"{URL}/{created['id']}", json={"is_archived": True, "channel": " post 2 "})
        assert updated.status_code == 200, updated.text
        assert updated.json()["is_archived"] is True
        assert updated.json()["channel"] == "post 2"
        cleared = await admin_client.patch(f"{URL}/{created['id']}", json={"channel": "  "})
        assert cleared.status_code == 200
        assert cleared.json()["channel"] is None
        assert cleared.json()["is_archived"] is True  # untouched fields stay

    @pytest.mark.contract
    async def test_null_archived_flag_leaves_it_unchanged(self, admin_client: AsyncClient):
        created = (await admin_client.post(URL, json={"code": _code()})).json()
        response = await admin_client.patch(f"{URL}/{created['id']}", json={"is_archived": None, "channel": "c"})
        assert response.status_code == 200, response.text  # not a NOT NULL violation (500)
        assert response.json()["is_archived"] is False
        assert response.json()["channel"] == "c"

    @pytest.mark.contract
    async def test_price_and_date_can_be_set_and_cleared(self, admin_client: AsyncClient):
        created = (await admin_client.post(URL, json={"code": _code()})).json()
        set_ = await admin_client.patch(
            f"{URL}/{created['id']}", json={"price_rub": 5000, "published_on": "2026-09-01"}
        )
        assert set_.status_code == 200, set_.text
        assert (set_.json()["price_rub"], set_.json()["published_on"]) == (5000.0, "2026-09-01")
        assert set_.json()["start_date"] == "2026-09-01"
        cleared = (await admin_client.patch(f"{URL}/{created['id']}", json={"price_rub": None})).json()
        assert cleared["price_rub"] is None
        assert cleared["published_on"] == "2026-09-01"
        assert (await admin_client.patch(f"{URL}/{created['id']}", json={"price_rub": -1})).status_code == 422

    @pytest.mark.contract
    async def test_update_unknown_link_404(self, admin_client: AsyncClient):
        response = await admin_client.patch(f"{URL}/2147483000", json={"channel": "x"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Marketing link not found"

    @pytest.mark.contract
    async def test_update_writes_audit_row(self, admin_client: AsyncClient):
        code = _code()
        created = (await admin_client.post(URL, json={"code": code})).json()
        await admin_client.patch(f"{URL}/{created['id']}", json={"price_rub": 100, "published_on": "2026-09-01"})
        rows = await _audit_rows(admin_client, "marketing_link_update", code)
        assert len(rows) == 1
        assert rows[0]["target_type"] == "marketing_link"
        assert rows[0]["detail"] == {"price_rub": 100.0, "published_on": "2026-09-01"}

    # =========================================================================
    # Results
    # =========================================================================

    @pytest.mark.contract
    async def test_results_count_users_payers_and_revenue(self, admin_client: AsyncClient, db_session: AsyncSession):
        code = _code()
        await admin_client.post(URL, json={"code": code})
        await _user_from(db_session, code)
        payer = await _user_from(db_session, code)
        await _pay(db_session, payer, amount=100)
        await _pay(db_session, payer, amount=999, provider=PaymentProvider.GIFT)  # a gift, not money
        await _pay(db_session, payer, amount=500, status=PaymentStatus.REFUNDED)  # refunded: not revenue
        refunded_only = await _user_from(db_session, code)
        await _pay(db_session, refunded_only, amount=300, status=PaymentStatus.REFUNDED)

        item = _by_code(await _listing(admin_client), code)
        assert item["stats"]["users"] == 3
        assert item["stats"]["payers"] == 1
        assert item["stats"]["revenue_rub"] == 100.0
        assert item["ltv_rub"] == 33.33
        assert item["stats"]["first_payment_at"] is not None
        assert item["payback"] is None  # no price, no verdict
        assert item["cac_rub"] is None

    @pytest.mark.contract
    async def test_stats_shape(self, admin_client: AsyncClient, db_session: AsyncSession):
        code = _code()
        await _user_from(db_session, code)
        stats = _by_code(await _listing(admin_client), code)["stats"]
        counts = {"users", "activated", "payers", *(f"{k}_d{n}" for k in ("eligible", "returned") for n in (1, 7, 30))}
        money = {"revenue_rub", "revenue_purchases_rub", "revenue_d14_rub"}
        dates = {"first_user_at", "last_user_at", "first_payment_at"}
        assert set(stats) == counts | money | dates  # the generic names only
        for key in counts:
            assert isinstance(stats[key], int), key
        assert 0 <= stats["activated"] <= stats["users"] == 1
        assert stats["first_user_at"] is not None

    # =========================================================================
    # Economics
    # =========================================================================

    @pytest.mark.contract
    async def test_price_gives_cac_ltv_roas_and_the_payback_day(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        code = _code()
        published = datetime.now(UTC).date() - timedelta(days=30)
        start = datetime.combine(published, datetime.min.time(), tzinfo=UTC)
        await admin_client.post(URL, json={"code": code, "price_rub": 1000, "published_on": str(published)})

        first = await _user_from(db_session, code)
        await _user_from(db_session, code)
        await _pay(db_session, first, amount=600, at=start + timedelta(days=3))
        await _pay(db_session, first, amount=550, at=start + timedelta(days=10))  # RUB: no app-specific rate
        await _pay(db_session, first, amount=400, at=start + timedelta(days=20), renewal=True)  # after D14
        await _pay(db_session, first, amount=999, provider=PaymentProvider.GIFT)

        item = _by_code(await _listing(admin_client), code)
        assert item["stats"]["payers"] == 1
        assert item["stats"]["revenue_d14_rub"] == 1150.0
        assert item["stats"]["revenue_rub"] == 1550.0
        assert item["stats"]["revenue_purchases_rub"] == 1150.0  # the renewal isn't a purchase
        assert item["cac_rub"] == 500.0
        assert item["ltv_rub"] == 775.0
        assert item["roas"] == 1.55
        assert item["payback"] == "paid_back"
        assert item["payback_days"] == 11  # 600 on day 4 + 550 on day 11 cover the 1000
        assert item["start_date"] == str(published)

    @pytest.mark.contract
    async def test_not_paid_back_only_after_14_days(self, admin_client: AsyncClient, db_session: AsyncSession):
        fresh, old = _code(), _code()
        today = datetime.now(UTC).date()
        for code, days_ago in ((fresh, 3), (old, 20)):
            await admin_client.post(
                URL, json={"code": code, "price_rub": 1000, "published_on": str(today - timedelta(days=days_ago))}
            )
            await _pay(db_session, await _user_from(db_session, code), amount=100)

        listing = await _listing(admin_client)
        assert _by_code(listing, fresh)["payback"] == "in_progress"
        assert _by_code(listing, old)["roas"] == 0.1
        assert _by_code(listing, old)["payback"] == "not_paid_back"
        assert _by_code(listing, old)["stats"]["revenue_d14_rub"] == 0.0  # paid today, after its first 14 days

    # =========================================================================
    # Codes seen before the registry
    # =========================================================================

    @pytest.mark.contract
    async def test_codes_used_before_the_registry_are_listed(self, admin_client: AsyncClient, db_session: AsyncSession):
        legacy = _code()
        await _user_from(db_session, legacy, created_at=datetime.now(UTC) - timedelta(days=40))

        item = _by_code(await _listing(admin_client), legacy)
        assert item["registered"] is False
        assert item["id"] is None
        assert item["stats"]["users"] == 1
        assert item["start_date"] == str((datetime.now(UTC) - timedelta(days=40)).date())  # its first sign-up

        # Registering it later keeps its history.
        assert (await admin_client.post(URL, json={"code": legacy, "channel": "Old post"})).status_code == 200
        item = _by_code(await _listing(admin_client), legacy)
        assert item["registered"] is True
        assert item["channel"] == "Old post"
        assert item["stats"]["users"] == 1

    @pytest.mark.contract
    async def test_registered_codes_come_first(self, admin_client: AsyncClient, db_session: AsyncSession):
        unregistered, registered = _code(), _code()
        await _user_from(db_session, unregistered)
        await admin_client.post(URL, json={"code": registered})
        codes = [item["code"] for item in (await _listing(admin_client))["items"]]
        assert codes.index(registered) < codes.index(unregistered)

    # =========================================================================
    # RBAC
    # =========================================================================

    @pytest.mark.contract
    async def test_list_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        assert (await authenticated_client.get(URL)).status_code == 403

    @pytest.mark.contract
    async def test_create_forbidden_for_non_admin(self, authenticated_client: AsyncClient):
        assert (await authenticated_client.post(URL, json={"code": _code()})).status_code == 403

    @pytest.mark.contract
    async def test_update_forbidden_for_non_admin(self, authenticated_client: AsyncClient, admin_client: AsyncClient):
        created = (await admin_client.post(URL, json={"code": _code()})).json()
        response = await authenticated_client.patch(f"{URL}/{created['id']}", json={"is_archived": True})
        assert response.status_code == 403


__all__ = ["BaseMarketingLinksTests"]
