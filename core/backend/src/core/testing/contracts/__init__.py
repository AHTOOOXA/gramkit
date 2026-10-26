"""Base test classes for core contract tests.

Apps inherit these classes and provide fixtures (client, authenticated_client, test_app).
This allows core tests to be written once and run in each app's context.

Usage in app:
    from core.testing.contracts import BaseAuthTests, BaseAppSetupTests

    class TestAuth(BaseAuthTests):
        pass  # Fixtures inherited from app's conftest.py

    class TestAppSetup(BaseAppSetupTests):
        pass
"""

# Router contract tests
from core.testing.contracts.admin import BaseAdminTests
from core.testing.contracts.admin_statistics import BaseAdminStatisticsTests
from core.testing.contracts.auth import BaseAuthTests
from core.testing.contracts.broadcasts import BaseBroadcastTests

# Architecture/pattern contract tests
from core.testing.contracts.composition import BaseCompositionTests
from core.testing.contracts.health import BaseHealthTests
from core.testing.contracts.marketing_links import BaseMarketingLinksTests
from core.testing.contracts.payments import BasePaymentTests
from core.testing.contracts.products import BaseProductProtocolTests
from core.testing.contracts.seen_features import BaseSeenFeaturesTests
from core.testing.contracts.setup import BaseAppSetupTests
from core.testing.contracts.users import BaseUserTests

__all__ = [
    # Router contracts
    "BaseAdminStatisticsTests",
    "BaseAdminTests",
    "BaseAuthTests",
    "BaseBroadcastTests",
    "BaseHealthTests",
    "BaseMarketingLinksTests",
    "BasePaymentTests",
    "BaseSeenFeaturesTests",
    "BaseUserTests",
    # Architecture contracts
    "BaseAppSetupTests",
    "BaseCompositionTests",
    "BaseProductProtocolTests",
]
