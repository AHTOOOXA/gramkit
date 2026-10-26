"""The app's admin tasks: ``users_overview`` (read-only demo) and its startup registration.

Gating, the 404, dry run vs apply and the audit row are covered by the inherited
``BaseAdminTests`` (``test_core_admin.py``); this file covers what the app adds.
"""

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_tasks import users_overview
from core.infrastructure.database.models.enums import UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.admin_tasks import get_admin_task

_BACKEND_DIR = Path(__file__).resolve().parents[4]

# Imports the webhook app in a FRESH interpreter and prints the registered task names.
_STARTUP_SCRIPT = """
import json
from unittest.mock import patch

with patch("core.infrastructure.redis.RedisClient.__init__", lambda self, config: None):
    import app.webhook.app  # noqa: F401

from core.services.admin_tasks import list_admin_tasks

print(json.dumps(sorted(task.name for task in list_admin_tasks())))
"""


async def _seed_user(db_session: AsyncSession) -> None:
    await CoreRequestsRepo(db_session).users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"overview_{uuid4().hex[:8]}",
            "role": UserRole.USER,
        }
    )
    await db_session.flush()


@pytest.mark.business_logic
def test_users_overview_is_registered_read_only():
    task = get_admin_task("users_overview")

    assert task is not None
    assert task.destructive is False


@pytest.mark.business_logic
async def test_users_overview_counts_users(db_session: AsyncSession):
    await _seed_user(db_session)

    result = await users_overview(db_session, dry_run=False)

    assert result["applied"] is False
    assert result["total_users"] >= 1
    assert result["by_role"]["user"] >= 1
    assert sum(result["by_type"].values()) == result["total_users"]
    assert result["new_last_7_days"] >= 1
    json.dumps(result)  # stored in the audit row (JSONB)


@pytest.mark.regression
def test_webhook_app_import_registers_tasks():
    """Importing the webhook app alone registers the tasks (the ``webhook/app.py`` import).

    In-process tests can't see a missing import: this file already imported the task
    module. So the check runs in a fresh interpreter.
    """
    # Pin `app` to THIS backend: the subprocess would otherwise resolve it through the
    # shared venv's editable install, i.e. whichever app backend was synced last.
    pythonpath = [str(_BACKEND_DIR / "src"), os.environ.get("PYTHONPATH")]
    env = {
        **os.environ,
        "ENV_FILE": os.environ.get("ENV_FILE", ".env.test"),
        "PYTHONPATH": os.pathsep.join(filter(None, pythonpath)),
    }
    result = subprocess.run(
        [sys.executable, "-c", _STARTUP_SCRIPT],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_BACKEND_DIR,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "users_overview" in json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.contract
async def test_tasks_endpoints_list_and_run_users_overview(owner_client: AsyncClient):
    listed = await owner_client.get("/admin/tasks")
    assert listed.status_code == 200
    assert "users_overview" in {task["name"] for task in listed.json()}

    response = await owner_client.post("/admin/tasks/users_overview", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "users_overview"
    assert data["result"]["applied"] is False
    assert data["result"]["by_role"]["owner"] >= 1
