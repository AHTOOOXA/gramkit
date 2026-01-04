"""Core contract tests for template app.

Inherits all shared contract tests from core.testing.
App-specific tests should go in separate files.

Tests are organized by category:
- Router contracts: Auth, Health, User, Payments
- Architecture contracts: AppSetup, Composition, Products
"""

from core.testing.contracts import (
    # Architecture contracts
    BaseAppSetupTests,
    # Router contracts
    BaseAuthTests,
    BaseCompositionTests,
    BaseHealthTests,
    BasePaymentTests,
    BaseProductProtocolTests,
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


class TestPayments(BasePaymentTests):
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
