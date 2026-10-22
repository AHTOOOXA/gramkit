"""Base test class for app setup contract tests.

Tests cover:
- App initialization and configuration
- Router registration
- Dependency injection setup
- Required routes presence

Apps inherit this class - fixtures are provided by app's conftest.py.
"""

import pytest


def _collect_route_paths(routes) -> list[str]:
    """Flatten an app/router's routes into a list of path strings.

    Starlette 1.0 changed ``include_router()``: instead of eagerly copying a
    sub-router's routes onto the parent, ``app.routes`` now holds an
    ``_IncludedRouter`` wrapper whose ``path`` is ``None`` and whose children
    live on ``.original_router.routes``. Starlette 0.x — and ``Mount`` /
    sub-apps on both — expose children directly via ``.routes``. Walk
    recursively so this contract holds across versions instead of assuming every
    entry is a flat ``APIRoute`` with a ``.path``.
    """
    paths: list[str] = []
    for route in routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.append(path)
        # Descend into included routers (Starlette 1.x) / mounts / sub-apps.
        nested = getattr(route, "routes", None)
        if nested is None:
            original = getattr(route, "original_router", None)
            nested = getattr(original, "routes", None) if original is not None else None
        if nested:
            paths.extend(_collect_route_paths(nested))
    return paths


class BaseAppSetupTests:
    """Base class for app setup contract tests."""

    # =========================================================================
    # App Configuration Tests
    # =========================================================================

    @pytest.mark.contract
    def test_app_has_routers(self, test_app):
        """App has routers registered."""
        routes = _collect_route_paths(test_app.routes)
        assert len(routes) > 0, "App should have routes registered"

    @pytest.mark.contract
    def test_app_has_required_routes(self, test_app):
        """App has required core routes."""
        route_paths = _collect_route_paths(test_app.routes)

        assert any("/users" in p for p in route_paths), "Missing /users routes"
        assert any("/payments" in p for p in route_paths), "Missing /payments routes"
        assert any("/subscriptions" in p for p in route_paths), "Missing /subscriptions routes"
        assert any("/health" in p for p in route_paths), "Missing /health route"

    # =========================================================================
    # Dependency Injection Tests
    # =========================================================================

    @pytest.mark.contract
    def test_user_dependency_is_overridden(self, test_app):
        """User dependency is overridden for app."""
        from core.infrastructure.fastapi import dependencies as core_deps

        assert core_deps.get_user in test_app.dependency_overrides, "App must override core get_user dependency"

    @pytest.mark.contract
    def test_services_dependency_is_overridden(self, test_app):
        """Services dependency is overridden for app."""
        from core.infrastructure.fastapi import dependencies as core_deps

        assert core_deps.get_services in test_app.dependency_overrides, "App must override core get_services dependency"

    # =========================================================================
    # App State Tests
    # =========================================================================

    @pytest.mark.contract
    def test_telegram_auth_in_app_state(self, test_app):
        """Telegram auth is stored in app state."""
        assert hasattr(test_app.state, "telegram_auth"), "App state must have telegram_auth"
        assert test_app.state.telegram_auth is not None

    @pytest.mark.contract
    def test_settings_in_app_state(self, test_app):
        """Settings are stored in app state."""
        assert hasattr(test_app.state, "settings"), "App state must have settings"
        assert test_app.state.settings is not None
