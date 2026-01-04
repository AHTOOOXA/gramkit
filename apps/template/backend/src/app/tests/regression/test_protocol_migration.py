"""
Regression tests for Protocol-based dependency injection.

Date: December 2025
Severity: High
Root cause: Core services hardcoded `from app.domain.products`, causing code duplication.
Fix: Protocol-based dependency injection.

These tests ensure the architectural boundary between core and app is maintained.
Core services must NOT import from app.domain - they receive products via dependency injection.
"""

import inspect

import pytest

from app.domain import products
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService


@pytest.mark.regression
class TestProtocolMigrationRegression:
    """Regression tests for Protocol-based dependency injection pattern."""

    async def test_requests_service_injects_app_products(self, db_session):
        """
        RequestsService injects app-specific products to core services.

        Verifies that the composition pattern correctly passes products
        from app.domain to core services via dependency injection.
        """
        repo = RequestsRepo(db_session)
        services = RequestsService(repo=repo)

        # Core services should have products injected
        assert services.payments.products is products, (
            "PaymentsService should have app-specific products injected. "
            "This indicates the Protocol-based DI is broken."
        )
        assert services.subscriptions.products is products, (
            "SubscriptionsService should have app-specific products injected. "
            "This indicates the Protocol-based DI is broken."
        )

    def test_core_payments_service_does_not_import_app_domain(self):
        """
        Core PaymentsService must NOT import from app.domain (architectural boundary).

        This is a critical architectural constraint. If violated:
        - Core becomes coupled to app-specific code
        - Multiple apps cannot share core services
        - 360-line product definitions get duplicated
        """
        from core.services.payments.service import PaymentsService

        source = inspect.getsource(PaymentsService)

        # Core should NOT import from app.domain
        assert "from app.domain" not in source, (
            "CRITICAL: PaymentsService imports from app.domain! "
            "This breaks the core/app architectural boundary. "
            "Products should be injected via Protocol, not imported."
        )

        # Core should use injected products
        assert "self.products" in source, (
            "PaymentsService should use self.products (injected via Protocol). "
            "This indicates the Protocol-based DI was removed or broken."
        )

    def test_core_subscriptions_service_does_not_import_app_domain(self):
        """
        Core SubscriptionsService must NOT import from app.domain (architectural boundary).
        """
        from core.services.subscriptions import SubscriptionsService

        source = inspect.getsource(SubscriptionsService)

        # Core should NOT import from app.domain
        assert "from app.domain" not in source, (
            "CRITICAL: SubscriptionsService imports from app.domain! This breaks the core/app architectural boundary."
        )

        # Core should use injected products
        assert "self.products" in source, "SubscriptionsService should use self.products (injected via Protocol)."

    async def test_products_api_endpoint_works_with_protocol(self, authenticated_client):
        """
        GET /payments/products works with Protocol-injected products.

        Integration test verifying the full stack works with Protocol-based DI.
        """
        response = await authenticated_client.get("/payments/products")

        assert response.status_code == 200, (
            f"Products endpoint failed with status {response.status_code}. "
            "This may indicate Protocol-based DI is broken."
        )

        products_list = response.json()
        assert isinstance(products_list, list), "Products endpoint should return a list"

        # At least one product should be available
        assert len(products_list) > 0, "No products returned. Protocol injection may have failed."

        # Verify product structure
        for product in products_list:
            assert "id" in product, "Product missing 'id' field"
            assert "name" in product, "Product missing 'name' field"
            assert "price" in product, "Product missing 'price' field"
            assert "duration_days" in product, "Product missing 'duration_days' field"

    async def test_subscription_service_uses_injected_products(self, authenticated_client):
        """
        Subscription endpoint works with Protocol-injected products.

        Verifies subscriptions service correctly uses injected products
        for price lookups and product validation.
        """
        response = await authenticated_client.get("/subscriptions/")

        assert response.status_code == 200, (
            f"Subscriptions endpoint failed with status {response.status_code}. "
            "This may indicate Protocol-based DI is broken in subscriptions."
        )

        subscription = response.json()
        assert "user_id" in subscription, "Subscription missing 'user_id' field"
        assert "status" in subscription, "Subscription missing 'status' field"
