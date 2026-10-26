"""Core contract tests for template app.

Inherits all shared contract tests from core.testing.
App-specific tests should go in separate files.

Tests are organized by category:
- Router contracts: Auth, Health, User, SeenFeatures, Payments, Admin, AdminStatistics, Broadcasts,
  MarketingLinks
- Architecture contracts: AppSetup, Composition, Products
"""

from core.testing.contracts import (
    # Architecture contracts
    BaseAdminStatisticsTests,
    BaseAdminTests,
    BaseAppSetupTests,
    # Router contracts
    BaseAuthTests,
    BaseBroadcastTests,
    BaseCompositionTests,
    BaseHealthTests,
    BaseMarketingLinksTests,
    BasePaymentTests,
    BaseProductProtocolTests,
    BaseSeenFeaturesTests,
    BaseUserTests,
)

# =============================================================================
# Router Contract Tests
# =============================================================================


class TestAuth(BaseAuthTests):
    pass


class TestHealth(BaseHealthTests):
    pass


class TestUser(BaseUserTests):
    pass


class TestSeenFeatures(BaseSeenFeaturesTests):
    pass


class TestPayments(BasePaymentTests):
    pass


class TestAdmin(BaseAdminTests):
    pass


class TestAdminStatistics(BaseAdminStatisticsTests):
    pass


class TestBroadcasts(BaseBroadcastTests):
    pass


class TestMarketingLinks(BaseMarketingLinksTests):
    pass


# =============================================================================
# Architecture Contract Tests
# =============================================================================


class TestAppSetup(BaseAppSetupTests):
    """Template-specific app setup tests."""

    def test_app_is_configured(self, test_app):
        """App is properly configured with correct title."""
        assert test_app.title == "Template API"


class TestComposition(BaseCompositionTests):
    pass


class TestProducts(BaseProductProtocolTests):
    pass
