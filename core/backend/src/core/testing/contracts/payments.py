"""Base test class for payment and subscription contract tests.

Tests cover:
- Product listing
- Subscription status
- Payment initiation (YooKassa, Telegram Stars)
- Subscription cancellation

Apps inherit this class - fixtures are provided by app's conftest.py.
"""

import pytest
from httpx import AsyncClient


class BasePaymentTests:
    """Base class for payment/subscription contract tests."""

    # =========================================================================
    # Product Listing
    # =========================================================================

    @pytest.mark.contract
    async def test_products_list_returns_products(self, authenticated_client: AsyncClient):
        """GET /payments/products returns available products."""
        response = await authenticated_client.get("/payments/products")

        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) > 0

    @pytest.mark.contract
    async def test_products_have_required_fields(self, authenticated_client: AsyncClient):
        """Products have all required fields."""
        response = await authenticated_client.get("/payments/products")
        products = response.json()

        for product in products:
            assert "id" in product
            assert "name" in product
            assert "price" in product
            assert "duration_days" in product
            assert "currency" in product

    @pytest.mark.contract
    async def test_products_have_valid_prices(self, authenticated_client: AsyncClient):
        """All products have positive prices."""
        response = await authenticated_client.get("/payments/products")

        for product in response.json():
            assert product["price"] > 0

    # =========================================================================
    # Subscription Status
    # =========================================================================

    @pytest.mark.contract
    async def test_get_subscription_returns_status(self, authenticated_client: AsyncClient):
        """GET /subscriptions/ returns subscription status."""
        response = await authenticated_client.get("/subscriptions/")

        assert response.status_code == 200
        subscription = response.json()
        assert "user_id" in subscription
        assert "status" in subscription
        assert "product_id" in subscription

    @pytest.mark.contract
    async def test_subscription_includes_pricing(self, authenticated_client: AsyncClient):
        """Subscription response includes pricing details."""
        response = await authenticated_client.get("/subscriptions/")
        subscription = response.json()

        assert "product_price" in subscription
        assert "currency" in subscription

    # =========================================================================
    # YooKassa Payment
    # =========================================================================

    @pytest.mark.contract
    async def test_yookassa_purchase_initiation(self, authenticated_client: AsyncClient, mock_yookassa):
        """POST /payments/start_purchase initiates YooKassa payment."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "MONTH_SUB_V3",
                "currency": "RUB",
                "provider_id": "YOOKASSA",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "confirmation_url" in data
        assert data["confirmation_url"].startswith("http")

    @pytest.mark.contract
    async def test_yookassa_returns_payment_id(self, authenticated_client: AsyncClient, mock_yookassa):
        """YooKassa payment returns payment_id for tracking."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "WEEK_SUB_V3",
                "currency": "RUB",
                "provider_id": "YOOKASSA",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 200
        assert "payment_id" in response.json()

    @pytest.mark.contract
    async def test_invalid_product_fails(self, authenticated_client: AsyncClient, mock_yookassa):
        """Purchase with invalid product ID returns 400."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "INVALID_PRODUCT_12345",
                "currency": "RUB",
                "provider_id": "YOOKASSA",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 400

    # =========================================================================
    # Telegram Stars Payment
    # =========================================================================

    @pytest.mark.contract
    async def test_telegram_stars_invoice_creation(self, authenticated_client: AsyncClient):
        """Create invoice for Telegram Stars payment."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "TEST_ONETIME",
                "currency": "XTR",
                "provider_id": "TELEGRAM_STARS",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 200
        assert "confirmation_url" in response.json()

    @pytest.mark.contract
    async def test_telegram_stars_returns_payment_id(self, authenticated_client: AsyncClient):
        """Telegram Stars payment returns payment_id."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "TEST_ONETIME",
                "currency": "XTR",
                "provider_id": "TELEGRAM_STARS",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 200
        assert "payment_id" in response.json()

    @pytest.mark.contract
    async def test_telegram_stars_subscription_product(self, authenticated_client: AsyncClient):
        """Subscription products work with Telegram Stars."""
        response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": "TEST_SUBSCRIPTION",
                "currency": "XTR",
                "provider_id": "TELEGRAM_STARS",
                "return_url": "https://example.com/return",
            },
        )

        assert response.status_code == 200

    # =========================================================================
    # Subscription Cancellation
    # =========================================================================

    @pytest.mark.contract
    async def test_cancel_subscription_endpoint(self, authenticated_client: AsyncClient):
        """POST /subscriptions/cancel endpoint works."""
        response = await authenticated_client.post(
            "/subscriptions/cancel",
            json={"reason": "notUsing"},
        )

        assert response.status_code == 200

    @pytest.mark.contract
    async def test_cancel_with_feedback(self, authenticated_client: AsyncClient):
        """Cancellation with feedback is accepted."""
        response = await authenticated_client.post(
            "/subscriptions/cancel",
            json={
                "reason": "tooExpensive",
                "feedback": "Price too high.",
            },
        )

        assert response.status_code == 200
        assert "status" in response.json()

    # =========================================================================
    # Authorization
    # =========================================================================

    @pytest.mark.contract
    async def test_guest_payment_handling(self, client: AsyncClient):
        """Guest payment is handled gracefully (no crash)."""
        response = await client.post(
            "/payments/start_purchase",
            json={
                "product_id": "TEST_ONETIME",
                "currency": "XTR",
                "provider_id": "TELEGRAM_STARS",
                "return_url": "https://example.com/return",
            },
        )

        # Should not crash
        assert response.status_code in [200, 400, 401, 403]

    # =========================================================================
    # Complete Flows
    # =========================================================================

    @pytest.mark.contract
    async def test_view_products_then_purchase(self, authenticated_client: AsyncClient, mock_yookassa):
        """User can view products then initiate purchase."""
        # View products
        products_response = await authenticated_client.get("/payments/products")
        assert products_response.status_code == 200
        products = products_response.json()

        # Purchase first product
        product = products[0]
        purchase_response = await authenticated_client.post(
            "/payments/start_purchase",
            json={
                "product_id": product["id"],
                "currency": product["currency"],
                "provider_id": "YOOKASSA",
                "return_url": "https://example.com/return",
            },
        )

        assert purchase_response.status_code == 200
        assert "confirmation_url" in purchase_response.json()
