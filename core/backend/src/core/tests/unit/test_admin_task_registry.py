"""Unit tests for the ``@admin_task`` registry (no DB, no app)."""

import pytest

from core.services import admin_tasks
from core.services.admin_tasks import admin_task, get_admin_task, list_admin_tasks


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    """Each test starts from an empty registry; the real one is restored afterwards."""
    monkeypatch.setattr(admin_tasks, "_REGISTRY", {})


async def _noop(session, *, dry_run: bool) -> dict:
    return {"applied": False}


@pytest.mark.business_logic
def test_decorator_registers_and_returns_fn_unchanged():
    decorated = admin_task("alpha", "First task.", destructive=True)(_noop)

    assert decorated is _noop
    task = get_admin_task("alpha")
    assert task is not None
    assert task.name == "alpha"
    assert task.description == "First task."
    assert task.destructive is True
    assert task.run is _noop


@pytest.mark.business_logic
def test_destructive_defaults_to_false():
    admin_task("read_only", "Reads only.")(_noop)

    task = get_admin_task("read_only")
    assert task is not None
    assert task.destructive is False


@pytest.mark.business_logic
def test_list_is_sorted_by_name():
    admin_task("zeta", "Z.")(_noop)
    admin_task("alpha", "A.")(_noop)
    admin_task("mu", "M.")(_noop)

    assert [task.name for task in list_admin_tasks()] == ["alpha", "mu", "zeta"]


@pytest.mark.business_logic
def test_unknown_name_returns_none():
    assert get_admin_task("does_not_exist") is None


@pytest.mark.business_logic
def test_duplicate_name_raises():
    admin_task("twice", "First.")(_noop)

    with pytest.raises(ValueError, match="'twice' is already registered"):
        admin_task("twice", "Second.")(_noop)

    # The first registration is kept.
    task = get_admin_task("twice")
    assert task is not None
    assert task.description == "First."
