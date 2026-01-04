"""Base test class for Core/App composition pattern contract tests.

Tests verify that the composition pattern between core and app
services is working correctly. The pattern allows:
- Core services to be shared across multiple apps
- App-specific configuration to be injected at composition time
- Clean architectural boundaries between core and app code

Apps inherit this class and provide `services` and `products_module` fixtures.
"""

import pytest


class BaseCompositionTests:
    """Base class for core/app service composition tests.

    Apps must provide:
    - `services` fixture: An instance of app's RequestsService
    - `products_module` fixture: The app's products module
    """

    # =========================================================================
    # Core Services Composition Tests
    # =========================================================================

    @pytest.mark.contract
    def test_services_has_core_services(self, services):
        """Services correctly composes core services."""
        assert hasattr(services, "users"), "Missing users service"
        assert hasattr(services, "payments"), "Missing payments service"
        assert hasattr(services, "subscriptions"), "Missing subscriptions service"
        assert hasattr(services, "worker"), "Missing worker service"
        assert hasattr(services, "auth"), "Missing auth service"
        assert hasattr(services, "start"), "Missing start service"

    @pytest.mark.contract
    def test_services_has_app_services(self, services):
        """App-specific services are available alongside core services."""
        assert hasattr(services, "balance"), "Missing balance service"
        assert hasattr(services, "statistics"), "Missing statistics service"
        assert hasattr(services, "notifications"), "Missing notifications service"

    @pytest.mark.contract
    def test_core_services_use_injected_products(self, services, products_module):
        """Core services receive app-specific products via composition."""
        assert services.payments.products is products_module, "PaymentsService should use app-specific products"
        assert services.subscriptions.products is products_module, (
            "SubscriptionsService should use app-specific products"
        )

    @pytest.mark.contract
    def test_lazy_loading_pattern(self, services):
        """Services use lazy loading (@cached_property) pattern."""
        # Access services to trigger lazy loading
        _ = services.users
        _ = services.payments

        # Second access should return cached instance
        users1 = services.users
        users2 = services.users
        assert users1 is users2, "Users service should be cached"
