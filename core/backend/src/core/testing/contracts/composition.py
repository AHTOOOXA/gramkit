"""Base test class for Core/App composition pattern contract tests.

Tests verify that the composition pattern between core and app
services is working correctly. The pattern allows:
- Core services to be shared across multiple apps
- App-specific configuration to be injected at composition time
- Clean architectural boundaries between core and app code

Apps inherit this class and provide `services` and `products_module` fixtures.
"""

import pytest

from core.infrastructure.database.repo.analytics import AnalyticsRepo
from core.services.analytics import AnalyticsService
from core.services.statistics import StatisticsService


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
        # Admin API (core router): without these delegators the admin endpoints 500.
        assert hasattr(services, "audit_log"), "Missing audit_log service"
        assert hasattr(services, "admin"), "Missing admin service"
        assert hasattr(services, "admin_tasks"), "Missing admin_tasks service"
        # Broadcasts (core admin router + send path): service and repo delegators.
        assert hasattr(services, "broadcasts"), "Missing broadcasts service"
        assert hasattr(services.repo, "promotional_broadcasts"), "Missing promotional_broadcasts repo"
        # Marketing links (core admin router + alerts job): service and repo delegators.
        assert hasattr(services, "marketing_links"), "Missing marketing_links service"
        assert hasattr(services.repo, "marketing_links"), "Missing marketing_links repo"
        # Overview + analytics (core admin router, digest job, /stats): they call core methods, so
        # an app's own class under the same name 500s the endpoints — check the type, not the name.
        assert isinstance(services.statistics, StatisticsService), "statistics must delegate to core"
        assert isinstance(services.analytics, AnalyticsService), "analytics must delegate to core"
        assert isinstance(services.repo.analytics, AnalyticsRepo), "repo.analytics must delegate to core"

    @pytest.mark.contract
    def test_services_has_app_services(self, services):
        """App-specific services are available alongside core services."""
        assert hasattr(services, "balance"), "Missing balance service"
        assert hasattr(services, "notifications"), "Missing notifications service"

    @pytest.mark.contract
    def test_core_services_use_injected_products(self, services, products_module):
        """Core services receive app-specific products via composition."""
        assert services.payments.products is products_module, "PaymentsService should use app-specific products"
        assert services.subscriptions.products is products_module, (
            "SubscriptionsService should use app-specific products"
        )
        assert services.analytics.services.products is products_module, (
            "AnalyticsService (MRR) should use app-specific products"
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
