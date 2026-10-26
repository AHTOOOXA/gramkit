"""The request session's scope per route (route table only, no database).

Every endpoint opens ``get_repo`` at ``scope="function"`` (commit before the response is sent);
only the streaming endpoints listed here keep request scope, because their body generator still
writes through the services after the endpoint returned. No route may reach it at both scopes:
FastAPI caches them apart, so it would open two sessions. See ``app.webhook.dependencies.database``.
"""

from unittest.mock import patch

import pytest

from app.webhook.dependencies.database import get_repo
from core.testing.dependency_scopes import dependency_scopes_by_route

with patch("core.infrastructure.redis.RedisClient.__init__", lambda self, config: None):
    from app.webhook.app import app as api


@pytest.mark.contract
def test_request_session_scope_per_route():
    streaming: set = set()  # none of the template's endpoints streams from the database
    scopes = dependency_scopes_by_route(api, get_repo)

    assert len(scopes) > 10, "the walk found almost no routes using the session"
    wrong = [
        f"{sorted(route.methods or ())} {route.path} ({route.name}): {sorted(found)}"
        for route, found in scopes
        if found != ({"request"} if route.endpoint in streaming else {"function"})
    ]
    assert not wrong, wrong
    assert streaming <= {route.endpoint for route, _ in scopes}, "a streaming endpoint no longer uses the session"
