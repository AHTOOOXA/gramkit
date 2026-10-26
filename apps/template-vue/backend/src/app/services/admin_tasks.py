"""This app's admin tasks: owner-run maintenance, executed inside the live webhook process.

The framework is core (``core/services/admin_tasks.py``): the ``@admin_task`` registry, the
``GET /admin/tasks`` / ``POST /admin/tasks/{name}`` endpoints (list: admin, run: owner), and
an audit row for every run (``admin_task:<name>``). This module is imported once at startup
by ``webhook/app.py``; that import is what registers the tasks below.

Use a task, not a script, for data fixes on a running server (``.claude/rules/prod-scripts.md``):
it reuses the request's DB session and transaction, so there is no second app to boot (no OOM
risk in a small container), and its writes commit together with the audit row — an exception
rolls both back.

Writing a task:
- Signature: ``async def fn(session: AsyncSession, *, dry_run: bool) -> dict[str, Any]``.
- Return a JSON-serialisable dict (it is stored in the audit row): ISO strings for dates,
  ``.value`` for enums, ``str()`` for UUIDs.
- A task that changes data is ``destructive=True``: it must change nothing when ``dry_run``
  is true and return ``{"applied": bool, ...}``. (template-vue's admin Tasks tab enables
  "Apply" only after a successful dry run; the endpoint itself defaults to a dry run.)
- Names are unique: registering the same name twice raises at startup.

Destructive skeleton::

    @admin_task("purge_stale_guests", "Deletes guest users older than 30 days.", destructive=True)
    async def purge_stale_guests(session: AsyncSession, *, dry_run: bool) -> dict[str, Any]:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        where = (User.user_type == UserType.GUEST, User.created_at < cutoff)
        count = await session.scalar(select(func.count()).select_from(User).where(*where)) or 0
        if not dry_run:
            await session.execute(delete(User).where(*where))
        return {"applied": not dry_run, "matched": count}
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import User
from core.services.admin_tasks import admin_task


@admin_task(
    "users_overview",
    "Read-only. Counts users by role and by type, and sign-ups in the last 7 days. Changes nothing.",
)
async def users_overview(session: AsyncSession, *, dry_run: bool) -> dict[str, Any]:
    by_role_rows = (await session.execute(select(User.role, func.count()).group_by(User.role))).all()
    by_type_rows = (await session.execute(select(User.user_type, func.count()).group_by(User.user_type))).all()
    week_ago = datetime.now(UTC) - timedelta(days=7)
    new_last_7_days = await session.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago))

    by_role = {str(role): count for role, count in by_role_rows}
    by_type = {user_type.value: count for user_type, count in by_type_rows}
    return {
        "applied": False,
        "total_users": sum(by_role.values()),
        "by_role": by_role,
        "by_type": by_type,
        "new_last_7_days": new_last_7_days or 0,
    }
