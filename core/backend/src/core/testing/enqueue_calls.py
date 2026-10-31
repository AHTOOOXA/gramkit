"""Check every ``enqueue_job("name", ...)`` in the source against the worker's registered jobs.

arq resolves the job by name and calls it with the enqueued args only when the worker picks it up,
so a renamed parameter or an unregistered job fails in the worker, never at the call site. An app
test runs this over its own sources and core's::

    def test_enqueued_jobs_match_the_worker():
        from app.worker.worker import WorkerSettings
        assert find_enqueue_mismatches([APP_SRC, CORE_SRC], WorkerSettings.functions) == []

Only calls with a literal job name are checked; ``*args`` / ``**kwargs`` spreads are skipped.
"""

import ast
import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from arq.worker import Function, func

_PLACEHOLDER = object()


@dataclass(frozen=True)
class EnqueueCall:
    path: Path
    line: int
    job_name: str
    n_args: int
    kwargs: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.path}:{self.line} enqueue_job({self.job_name!r})"


def find_enqueue_calls(roots: Iterable[Path]) -> list[EnqueueCall]:
    """Every ``*.enqueue_job("literal", ...)`` under ``roots``, tests excluded."""
    calls = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.parts or "testing" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "enqueue_job"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    continue
                if any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords):
                    continue
                calls.append(
                    EnqueueCall(
                        path=path,
                        line=node.lineno,
                        job_name=node.args[0].value,
                        n_args=len(node.args) - 1,
                        # _-prefixed kwargs are arq's own options (_defer_by, _job_id, ...)
                        kwargs=tuple(k.arg for k in node.keywords if k.arg and not k.arg.startswith("_")),
                    )
                )
    return calls


def find_enqueue_mismatches(roots: Iterable[Path], worker_functions: Iterable) -> list[str]:
    """Problems with the enqueue calls under ``roots``: unknown job names and args the job rejects."""
    jobs: dict[str, Function] = {}
    for f in worker_functions:
        job = f if isinstance(f, Function) else func(f)
        jobs[job.name] = job

    problems = []
    for call in find_enqueue_calls(roots):
        job = jobs.get(call.job_name)
        if job is None:
            problems.append(f"{call}: no job registered under this name")
            continue
        try:
            inspect.signature(job.coroutine).bind(
                _PLACEHOLDER, *([_PLACEHOLDER] * call.n_args), **dict.fromkeys(call.kwargs, _PLACEHOLDER)
            )
        except TypeError as e:
            problems.append(f"{call}: {e}")
    return problems
