"""The request session commits before the response is sent (``Depends(get_repo, scope="function")``).

Regression, 2026-10: FastAPI runs the exit code of a ``yield`` dependency **after** the response
is sent unless it is declared with ``scope="function"``. ``get_repo`` commits on exit, so a 200
reached the client before its data was committed: QA created a marketing link and the list
refetched empty; cancelled a broadcast and the detail still said active. A commit that failed
(an ``IntegrityError`` at flush-on-commit) was invisible too: the client already had its 200.

The probe app below reads the response-start moment from outside: an ASGI wrapper checks, on
another connection, whether the row is committed when ``http.response.start`` goes out. The
request scope (kept only for streaming endpoints) is the contrast that shows the probe works.
Core only: no ``app`` imports.
"""

import random
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.fastapi import dependencies as core_deps
from core.infrastructure.fastapi.dependencies import get_repo
from core.testing.dependency_scopes import dependency_scopes, iter_api_routes

# A unique key whose check runs at COMMIT, not at INSERT: a duplicate passes the endpoint and
# fails in get_repo's exit, the "flush-on-commit" failure.
_CREATE_PROBE_TABLE = """
CREATE TABLE IF NOT EXISTS request_scope_probe (
    key BIGINT NOT NULL,
    CONSTRAINT request_scope_probe_key UNIQUE (key) DEFERRABLE INITIALLY DEFERRED
)
"""


class ResponseStartProbe:
    """ASGI wrapper: when the response starts, record whether ``key`` is committed."""

    def __init__(self, app: ASGIApp, engine: AsyncEngine) -> None:
        self.app = app
        self.engine = engine
        self.committed_at_response_start: list[bool] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        key = int(scope["path"].rsplit("/", 1)[-1]) if scope["type"] == "http" else None

        async def probing_send(message: Message) -> None:
            if message["type"] == "http.response.start" and key is not None:
                async with self.engine.connect() as conn:
                    count = await conn.scalar(
                        text("SELECT count(*) FROM request_scope_probe WHERE key = :key"), {"key": key}
                    )
                self.committed_at_response_start.append(bool(count))
            await send(message)

        await self.app(scope, receive, probing_send)


def _probe_app(engine: AsyncEngine) -> FastAPI:
    app = FastAPI()
    app.state.session_pool = async_sessionmaker(engine, expire_on_commit=False)
    app.state.repo_class = CoreRequestsRepo

    async def _insert(repo: CoreRequestsRepo, key: int, times: int) -> dict:
        for _ in range(times):
            await repo.session.execute(text("INSERT INTO request_scope_probe (key) VALUES (:key)"), {"key": key})
        return {"key": key}

    @app.post("/function/{key}")
    async def insert_function_scope(
        key: int, times: int = 1, repo: CoreRequestsRepo = Depends(get_repo, scope="function")
    ) -> dict:
        return await _insert(repo, key, times)

    @app.post("/request/{key}")
    async def insert_request_scope(
        key: int, times: int = 1, repo: CoreRequestsRepo = Depends(get_repo, scope="request")
    ) -> dict:
        return await _insert(repo, key, times)

    return app


@pytest_asyncio.fixture
async def probe(db_engine: AsyncEngine) -> AsyncGenerator[tuple[ResponseStartProbe, AsyncClient]]:
    async with db_engine.begin() as conn:
        await conn.execute(text(_CREATE_PROBE_TABLE))
    wrapped = ResponseStartProbe(_probe_app(db_engine), db_engine)
    # raise_app_exceptions=False: a failed commit must reach the test as the HTTP response.
    transport = ASGITransport(app=wrapped, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield wrapped, client


async def _committed(engine: AsyncEngine, key: int) -> bool:
    async with engine.connect() as conn:
        count = await conn.scalar(text("SELECT count(*) FROM request_scope_probe WHERE key = :key"), {"key": key})
    return bool(count)


def _key() -> int:
    return random.randint(1, 2**62)


@pytest.mark.regression
class TestRequestSessionScope:
    async def test_function_scope_commits_before_response_is_sent(self, probe, db_engine):
        wrapped, client = probe
        key = _key()

        response = await client.post(f"/function/{key}")

        assert response.status_code == 200
        assert wrapped.committed_at_response_start == [True]
        assert await _committed(db_engine, key)

    async def test_request_scope_commits_after_response_is_sent(self, probe, db_engine):
        """The streaming scope: the response goes out first, the commit follows (the old bug)."""
        wrapped, client = probe
        key = _key()

        response = await client.post(f"/request/{key}")

        assert response.status_code == 200
        assert wrapped.committed_at_response_start == [False]
        assert await _committed(db_engine, key)  # committed after all, once the response was out

    async def test_function_scope_commit_failure_is_an_error_response(self, probe, db_engine):
        wrapped, client = probe
        key = _key()

        response = await client.post(f"/function/{key}", params={"times": 2})

        assert response.status_code == 500
        assert wrapped.committed_at_response_start == [False]
        assert not await _committed(db_engine, key)

    async def test_request_scope_commit_failure_still_answers_200(self, probe, db_engine):
        """Why request scope is only for streaming: a failed commit there is invisible to the client."""
        _, client = probe
        key = _key()

        response = await client.post(f"/request/{key}", params={"times": 2})

        assert response.status_code == 200
        assert not await _committed(db_engine, key)


@pytest.mark.contract
class TestDependencyScopes:
    def test_core_get_services_opens_the_session_at_function_scope(self):
        """Core routers depend on ``get_services``; its stub fixes the scope for every override that copies it."""
        app = FastAPI()

        @app.get("/services")
        async def uses_services(services=Depends(core_deps.get_services)) -> None: ...

        (route,) = iter_api_routes(app.routes)
        assert dependency_scopes(app, route, get_repo) == {"function"}

    def test_scopes_follow_overrides_and_report_mixing(self):
        app = FastAPI()

        async def app_get_services(repo=Depends(get_repo, scope="function")) -> CoreRequestsRepo:
            return repo

        app.dependency_overrides[core_deps.get_services] = app_get_services

        @app.get("/mixed")
        async def mixed(services=Depends(core_deps.get_services), repo=Depends(get_repo)) -> None: ...

        @app.get("/streaming")
        async def streaming(repo=Depends(get_repo, scope="request")) -> None: ...

        @app.get("/none")
        async def no_session() -> None: ...

        scopes = {route.path: dependency_scopes(app, route, get_repo) for route in iter_api_routes(app.routes)}
        assert scopes["/mixed"] == {"function", "request"}
        assert scopes["/streaming"] == {"request"}
        assert scopes["/none"] == set()
