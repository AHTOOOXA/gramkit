"""Every enqueue_job("name", ...) in the app and core names a registered job and passes args it accepts."""

from pathlib import Path

import pytest

import app
import core
from core.testing.enqueue_calls import find_enqueue_calls, find_enqueue_mismatches

SOURCES = [Path(app.__file__).parent, Path(core.__file__).parent]


@pytest.mark.regression
def test_enqueued_jobs_match_the_worker():
    """2026-10: /demo/notify enqueued send_delayed_notification with
    ``user_id=`` after the job's parameter had been renamed to ``telegram_user_id`` (2025-11), so
    the job died with a TypeError in the worker. arq checks args only when the job runs."""
    from app.worker.worker import WorkerSettings

    assert find_enqueue_calls(SOURCES), "the scan found no enqueue_job calls; is the source path right?"
    assert find_enqueue_mismatches(SOURCES, WorkerSettings.functions) == []
