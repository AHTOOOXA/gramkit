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
from core.testing.contracts.auth import BaseAuthTests

# Architecture/pattern contract tests
from core.testing.contracts.composition import BaseCompositionTests
from core.testing.contracts.health import BaseHealthTests
from core.testing.contracts.payments import BasePaymentTests
from core.testing.contracts.products import BaseProductProtocolTests
from core.testing.contracts.setup import BaseAppSetupTests
from core.testing.contracts.users import BaseUserTests

__all__ = [
    # Router contracts
    "BaseAuthTests",
    "BaseHealthTests",
    "BasePaymentTests",
    "BaseUserTests",
    # Architecture contracts
    "BaseAppSetupTests",
    "BaseCompositionTests",
    "BaseProductProtocolTests",
]
