"""Schemas for the admin Tasks section (``/admin/tasks``)."""

from typing import Any

from pydantic import BaseModel


class AdminTaskInfo(BaseModel):
    """A runnable admin task, for the Tasks list."""

    name: str
    description: str
    destructive: bool


class RunAdminTaskRequest(BaseModel):
    """Run options. Defaults to a dry run so nothing mutates by accident."""

    dry_run: bool = True


class AdminTaskRunResult(BaseModel):
    """Outcome of running a task."""

    task: str
    dry_run: bool
    result: dict[str, Any]
