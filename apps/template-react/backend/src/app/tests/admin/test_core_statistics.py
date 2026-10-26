"""Core admin Overview + money analytics contract in template-react.

Every test is inherited from ``core.testing.contracts.BaseAdminStatisticsTests``; the DB-backed
harness (``admin_client``, ``authenticated_client``, ``db_session``) comes from this directory's
``conftest.py``.
"""

from core.testing.contracts import BaseAdminStatisticsTests


class TestAdminStatistics(BaseAdminStatisticsTests):
    pass
