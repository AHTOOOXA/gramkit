"""Core admin marketing-links API contract (``/admin/marketing-links*``) in template-react.

Every test is inherited from ``core.testing.contracts.BaseMarketingLinksTests``; the DB-backed
harness (``test_app``, ``admin_client``) is this directory's conftest.
"""

from core.testing.contracts import BaseMarketingLinksTests


class TestMarketingLinks(BaseMarketingLinksTests):
    pass
