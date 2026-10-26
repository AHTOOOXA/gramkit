"""Core admin broadcasts API contract (``/admin/broadcasts*``) in template-react.

Every test is inherited from ``core.testing.contracts.BaseBroadcastTests``; the DB-backed
harness (``test_app`` with ``api_bot_mock``, ``admin_client`` / ``owner_client``) is this
directory's conftest.
"""

from core.testing.contracts import BaseBroadcastTests


class TestBroadcasts(BaseBroadcastTests):
    pass
