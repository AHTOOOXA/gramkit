"""setup_logging(): records go through a queue, a listener thread writes them to stdout.

The line must look exactly as before (request id and user from the caller's contextvars, full tracebacks), a second
setup must not double the lines, and shutdown_logging() must write out whatever is still queued.
"""

import io
import logging
import re
import threading
import time
from collections.abc import Iterator
from logging.handlers import QueueHandler
from types import SimpleNamespace

import pytest

from core.infrastructure import logging as core_logging
from core.infrastructure.logging import PLAIN_FORMAT, setup_logging, shutdown_logging
from core.infrastructure.request_context import RequestContext, clear_request_context, set_request_context

pytestmark = pytest.mark.contract

LOGGER = "core.tests.logging"


class _Stream(io.StringIO):
    """stdout stand-in: remembers which threads wrote to it; ``delay`` makes every write slow."""

    def __init__(self, delay: float = 0.0):
        super().__init__()
        self.delay = delay
        self.writer_threads: set[int] = set()

    def write(self, s: str) -> int:
        self.writer_threads.add(threading.get_ident())
        if self.delay:
            time.sleep(self.delay)
        return super().write(s)

    def lines(self) -> list[str]:
        return self.getvalue().splitlines()


@pytest.fixture
def stream(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Stream]:
    """Plain format on a fake stdout; the root logger is put back as it was afterwards."""
    root = logging.getLogger()
    # An app imported during collection may already run a listener: stop it (it falls back to direct writes) so
    # the root logger saved here is a plain one we can restore.
    shutdown_logging()
    saved_handlers, saved_level = root.handlers[:], root.level

    fake = _Stream()
    # Not sys.stdout itself: pytest's capture puts its own stream back there at the start of the test call.
    monkeypatch.setattr(core_logging, "sys", SimpleNamespace(stdout=fake))
    monkeypatch.setattr(core_logging, "_colored", lambda: False)
    try:
        yield fake
    finally:
        shutdown_logging()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)
        clear_request_context()


def _wait_for_lines(stream: _Stream, count: int, timeout: float = 2.0) -> list[str]:
    deadline = time.monotonic() + timeout
    while len(stream.lines()) < count and time.monotonic() < deadline:
        time.sleep(0.005)
    return stream.lines()


def test_line_carries_request_id_and_user_and_is_written_off_the_calling_thread(stream: _Stream):
    setup_logging()
    set_request_context(RequestContext(request_id="req-123", user_id="42"))

    logging.getLogger(LOGGER).info("GET %s %s", "/api/users/me", 200)

    shutdown_logging()
    (line,) = stream.lines()
    assert re.fullmatch(
        r"test_logging\.py:\d+ #INFO     \[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}\] \[req:req-123\] \[user:42\] "
        rf"- {re.escape(LOGGER)} - GET /api/users/me 200",
        line,
    ), line
    assert threading.get_ident() not in stream.writer_threads


def test_line_format_is_unchanged(stream: _Stream):
    """Byte for byte what a plain StreamHandler with the filter on it printed before the queue."""
    setup_logging()
    set_request_context(RequestContext(request_id="r1", user_id="u1"))
    record = logging.LogRecord(LOGGER, logging.WARNING, __file__, 7, "a %s line", ("formatted",), None)

    logging.getLogger(LOGGER).handle(record)
    shutdown_logging()

    before = logging.Formatter(PLAIN_FORMAT)
    expected = before.format(record)  # the filter already put request_id / user_id on the record
    assert stream.lines() == [expected]


def test_outside_a_request_fields_are_dashes(stream: _Stream):
    setup_logging()

    logging.getLogger(LOGGER).info("startup")

    (line,) = _wait_for_lines(stream, 1)
    assert "[req:-] [user:-]" in line


def test_traceback_is_printed_in_full(stream: _Stream):
    setup_logging()
    set_request_context(RequestContext(request_id="req-err", user_id="7"))

    def fail() -> None:
        raise ValueError("boom")

    try:
        fail()
    except ValueError:
        logging.getLogger(LOGGER).exception("request failed")

    shutdown_logging()
    output = stream.getvalue()
    assert "[req:req-err] [user:7]" in output
    assert " - request failed\nTraceback (most recent call last):\n" in output
    assert 'raise ValueError("boom")' in output
    assert output.rstrip().endswith("ValueError: boom")


def test_setup_twice_does_not_duplicate_lines(stream: _Stream):
    setup_logging()
    setup_logging()

    root = logging.getLogger()
    assert sum(isinstance(handler, QueueHandler) for handler in root.handlers) == 1

    logging.getLogger(LOGGER).info("only once")
    shutdown_logging()
    (line,) = stream.lines()
    assert line.endswith(" - only once")


def test_shutdown_writes_out_pending_lines(stream: _Stream):
    stream.delay = 0.002  # a slow stdout pipe: lines pile up in the queue
    setup_logging()

    for i in range(100):
        logging.getLogger(LOGGER).info("line %d", i)
    shutdown_logging()

    lines = stream.lines()
    assert len(lines) == 100
    assert lines[-1].endswith(" - line 99")


def test_after_shutdown_lines_are_written_directly(stream: _Stream):
    setup_logging()
    shutdown_logging()
    shutdown_logging()  # idempotent
    set_request_context(RequestContext(request_id="late", user_id="9"))

    logging.getLogger(LOGGER).info("after shutdown")

    (line,) = stream.lines()  # no wait: written synchronously
    assert "[req:late] [user:9]" in line
    assert line.endswith(" - after shutdown")


def test_caplog_still_sees_the_original_record(stream: _Stream, caplog: pytest.LogCaptureFixture):
    """The queue handler works on a copy: handlers after it (pytest's caplog) keep exc_info and the args."""
    setup_logging()
    logging.getLogger().addHandler(caplog.handler)  # basicConfig(force=True) dropped the one pytest added
    set_request_context(RequestContext(request_id="cap", user_id="1"))

    try:
        raise RuntimeError("kept")
    except RuntimeError:
        logging.getLogger(LOGGER).exception("with %s", "args")

    (record,) = [r for r in caplog.records if r.name == LOGGER]
    assert record.args == ("args",)
    assert record.exc_info is not None
    assert record.getMessage() == "with args"
    assert caplog.messages[-1] == "with args"
