"""Import-cycle guards: modules that must import cleanly in a FRESH interpreter.

``core.auth.rbac`` imports ``core.infrastructure.fastapi.dependencies``, which runs
``core/infrastructure/fastapi/__init__.py`` -> ``factory``. If ``factory`` imported the
routers package at module level, ``routers/__init__`` -> ``routers.admin`` ->
``core.auth.rbac`` would hit the partially initialized module
(``ImportError: cannot import name 'AdminUser'``). In-process tests can't see this
(the modules are already cached), so each check runs in a subprocess.
"""

import re
import subprocess
import sys

import pytest

_MISSING_MODULE = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")


def _import_in_fresh_interpreter(module: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "module",
    [
        "core.auth.rbac",
        "core.infrastructure.fastapi.routers",
        "core.infrastructure.fastapi.routers.admin",
        "core.infrastructure.fastapi.routers.admin_broadcasts",
        "core.services.admin_tasks",
        "core.infrastructure.fastapi.routers.admin_statistics",
        "core.services.statistics",
        "core.services.admin_metrics",
        "core.infrastructure.telegram.handlers.admin",
    ],
)
def test_module_imports_in_fresh_interpreter(module: str):
    """The module imports on its own (no circular-import error)."""
    result = _import_in_fresh_interpreter(module)

    if result.returncode != 0:
        # Core-only environments (core CI) lack some web-stack packages the apps install
        # (e.g. sentry_sdk, slowapi). That isn't a cycle, so skip rather than fail; the
        # check runs for real in every app's suite, which includes core's tests.
        missing = _MISSING_MODULE.search(result.stderr)
        if missing and missing.group(1).split(".")[0] not in {"core", "app"}:
            pytest.skip(f"third-party module {missing.group(1)!r} not installed in this environment")

    assert result.returncode == 0, result.stderr
