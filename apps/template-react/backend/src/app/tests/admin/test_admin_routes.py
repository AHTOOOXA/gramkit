"""Route-table guards for the admin API (template-react).

The admin API is core's router plus the app's (empty) ``webhook/routers/admin.py``, both under
``/admin``. These tests read the module-level FastAPI app (no database needed).
"""

from unittest.mock import patch

import pytest
from fastapi.routing import APIRoute

with patch("core.infrastructure.redis.RedisClient.__init__", lambda self, config: None):
    from app.webhook.app import app as api

LEGACY_ADMIN_STUBS = {"/admin/stats", "/admin/me", "/admin/demo-action"}


@pytest.mark.contract
class TestAdminRoutes:
    def test_legacy_admin_stubs_removed(self):
        """The pre-core demo endpoints are gone; core's admin API replaces them."""
        paths = set(api.openapi()["paths"])
        assert LEGACY_ADMIN_STUBS.isdisjoint(paths), LEGACY_ADMIN_STUBS & paths

    def test_no_duplicate_method_path(self):
        """No two routes share a method + path: the later one would be shadowed silently (D2)."""
        seen: dict[tuple[str, str], str] = {}
        duplicates: list[str] = []
        for route in api.routes:
            if not isinstance(route, APIRoute):
                continue
            for method in route.methods or ():
                key = (method, route.path)
                if key in seen:
                    duplicates.append(f"{method} {route.path}: {seen[key]} and {route.name}")
                else:
                    seen[key] = route.name
        assert not duplicates, duplicates

    def test_core_admin_api_is_mounted(self):
        """Sanity check for the two tests above: the core admin routes are in the table."""
        paths = set(api.openapi()["paths"])
        assert {"/admin/users", "/admin/audit-log", "/admin/meta/rbac"} <= paths
