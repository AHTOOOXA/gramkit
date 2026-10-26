"""Core ``seen_features`` endpoint contract (``PATCH /users/me/seen-features``) in template-react.

Every test is inherited from ``core.testing.contracts.BaseSeenFeaturesTests``; the DB-backed
harness (``test_app``, ``client``, ``authenticated_client``) is this directory's conftest.
"""

from core.testing.contracts import BaseSeenFeaturesTests


class TestSeenFeatures(BaseSeenFeaturesTests):
    pass
