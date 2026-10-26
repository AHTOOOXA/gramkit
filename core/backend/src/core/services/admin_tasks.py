"""Admin tasks: owner-run maintenance that runs inside the live webhook process.

Register ``async def fn(session: AsyncSession, *, dry_run: bool) -> dict`` with
``@admin_task(name, description, destructive=...)``. The registry is module-level; each app
imports its task module once at startup (``app/webhook/app.py``) — there is no discovery.

A run reuses the request's session and transaction: the task's writes and its audit row
commit together, and an exception rolls both back. The returned dict is stored in the
audit row (JSONB), so it must be JSON-serialisable (dates as ISO strings).

Convention: a task that changes data is ``destructive=True``, changes nothing when
``dry_run`` is true, and returns ``{"applied": bool, ...}``.

Every run is audit-logged as ``action="admin_task:<name>"``, ``target_type="admin_task"``,
``target_id=<name>``, ``detail={"dry_run": ..., "result": <task dict>}``. Tasks may read that
shape back (e.g. a once-only guard querying ``detail->'result'->>'applied'``), so keep it.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from core.exceptions import AdminTaskNotFoundException
from core.schemas.admin_tasks import AdminTaskInfo, AdminTaskRunResult
from core.schemas.users import UserSchema
from core.services.base import BaseService

TaskFn = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class AdminTask:
    name: str
    description: str
    destructive: bool
    run: TaskFn


_REGISTRY: dict[str, AdminTask] = {}


def admin_task(name: str, description: str, *, destructive: bool = False) -> Callable[[TaskFn], TaskFn]:
    """Register an admin task. The decorated fn is ``async (session, *, dry_run) -> dict``.

    Raises ``ValueError`` if a task with the same name is already registered, so a name
    clash fails at startup instead of silently replacing a task.
    """

    def decorator(fn: TaskFn) -> TaskFn:
        if name in _REGISTRY:
            raise ValueError(f"Admin task {name!r} is already registered")
        _REGISTRY[name] = AdminTask(name=name, description=description, destructive=destructive, run=fn)
        return fn

    return decorator


def list_admin_tasks() -> list[AdminTask]:
    """All registered tasks, sorted by name."""
    return sorted(_REGISTRY.values(), key=lambda task: task.name)


def get_admin_task(name: str) -> AdminTask | None:
    """The task registered under ``name``, or ``None``."""
    return _REGISTRY.get(name)


class AdminTasksService(BaseService):
    """Lists registered tasks and runs one inside the request transaction, with an audit row.

    Gating lives in the router (list: AdminUser, run: OwnerUser).
    """

    def list_tasks(self) -> list[AdminTaskInfo]:
        """Registered tasks for the admin Tasks list, sorted by name."""
        return [
            AdminTaskInfo(name=task.name, description=task.description, destructive=task.destructive)
            for task in list_admin_tasks()
        ]

    async def run(self, actor: UserSchema, name: str, *, dry_run: bool) -> AdminTaskRunResult:
        """Run task ``name`` on the request session, then record the audit row.

        The task runs first: a task that raises writes no audit row, and the exception
        propagates so the request transaction rolls its partial writes back.
        """
        task = get_admin_task(name)
        if task is None:
            raise AdminTaskNotFoundException(f"Unknown task: {name}")

        result = await task.run(self.repo.session, dry_run=dry_run)

        await self.services.audit_log.record(
            actor=actor,
            action=f"admin_task:{name}",
            target_type="admin_task",
            target_id=name,
            detail={"dry_run": dry_run, "result": result},
        )
        return AdminTaskRunResult(task=name, dry_run=dry_run, result=result)
