"""Auth errors: an invalid initData is a 401, the infrastructure failing is a 503, never "not logged in".

Regression (gramkit load test): Docker DNS failures (``[Errno -3] Temporary failure in name resolution``) while
opening a DB/Redis connection came back from ``resolve_user`` as 401 "Authentication failed", so a traffic spike
logged people out; on the session-cookie path the same failure silently turned a logged-in web user into the
shared guest. Now both are a 503 with ``Retry-After`` that the frontends retry.

Runs without the ``app`` package (core CI): ``settings`` is replaced by a stub, the DB and Redis by fakes.
"""

import hashlib
import hmac
import json
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import unquote, urlencode
from uuid import uuid4

import pytest
import redis.exceptions as redis_exc
import sqlalchemy.exc as sa_exc
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from core.infrastructure.auth.telegram import TelegramAuthenticator, generate_secret_key
from core.infrastructure.fastapi import auth
from core.infrastructure.fastapi.auth import MOCK_GUEST_USER_ID, get_mock_guest_user, resolve_user
from core.infrastructure.infra_errors import is_infrastructure_error
from core.schemas.users import UserSchema
from core.services import sessions as sessions_module
from core.services.sessions import SessionService

BOT_TOKEN = "123456:TEST-TOKEN"
COOKIE = "session_id"
DNS_ERROR = socket.gaierror(-3, "Temporary failure in name resolution")


def _db_operational_error() -> sa_exc.OperationalError:
    """What SQLAlchemy raises when the driver can't reach Postgres (the DNS error wrapped)."""
    return sa_exc.OperationalError("SELECT 1", {}, DNS_ERROR)


def _signed_init_data(user: dict | None = None) -> str:
    """A genuine initData for BOT_TOKEN, signed the way Telegram signs it."""
    fields = {"auth_date": "1700000000", "user": json.dumps(user or {"id": 42, "first_name": "Ann"})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    digest = hmac.new(generate_secret_key(BOT_TOKEN), unquote(check).encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def _user():
    return get_mock_guest_user().model_copy(update={"id": uuid4(), "display_name": "Ann", "telegram_id": 42})


class _DownRedis:
    """A Redis whose connection fails, as redis-py raises it."""

    async def get(self, key):
        raise redis_exc.ConnectionError("Error -3 connecting to redis:6379. Temporary failure in name resolution.")

    async def set(self, key, value, ex):
        raise AssertionError("unreachable")

    async def delete(self, key):
        raise AssertionError("unreachable")


@pytest.fixture(autouse=True)
def _no_app_settings(monkeypatch):
    stub = SimpleNamespace(debug=False, session=SimpleNamespace(cookie_name=COOKIE, key_prefix="t:", expire_days=1))
    monkeypatch.setattr(auth, "settings", stub)
    monkeypatch.setattr(sessions_module, "settings", stub)
    monkeypatch.setattr(auth, "set_sentry_user", lambda **_: None)


def _services(*, get_or_create_user=None, get_user_by_id=None, sessions=None):
    users = SimpleNamespace(
        # the guest row comes back as asked; a Telegram user gets an id, as the DB gives it one
        get_or_create_user=AsyncMock(side_effect=get_or_create_user or (lambda u: u if u.id else _user())),
        get_user_by_id=AsyncMock(side_effect=get_user_by_id or (lambda _id: _user())),
    )
    return SimpleNamespace(users=users, sessions=sessions or SimpleNamespace(validate_session=AsyncMock()))


def _client(services, cookies: dict | None = None) -> AsyncClient:
    api = FastAPI()
    api.state.telegram_auth = TelegramAuthenticator(generate_secret_key(BOT_TOKEN))

    @api.get("/me")
    async def me(request: Request):
        user = await resolve_user(request, services)
        return {"id": str(user.id)}

    # raise_app_exceptions=False: an unhandled error comes back as the 500 a server would send
    return AsyncClient(
        transport=ASGITransport(app=api, raise_app_exceptions=False), base_url="http://test", cookies=cookies
    )


@pytest.mark.regression
class TestInitDataPath:
    async def test_invalid_init_data_is_401(self):
        services = _services()
        async with _client(services) as client:
            response = await client.get("/me", headers={"initData": "user=%7B%7D&hash=deadbeef"})
        assert response.status_code == 401
        services.users.get_or_create_user.assert_not_awaited()

    async def test_malformed_hash_is_401_not_500(self):
        # hmac.compare_digest raises TypeError on a non-ASCII hash: still the client's fault
        async with _client(_services()) as client:
            response = await client.get("/me", headers={"initData": "user=%7B%7D&hash=%C3%A9"})
        assert response.status_code == 401

    async def test_valid_init_data_authenticates(self):
        async with _client(_services()) as client:
            response = await client.get("/me", headers={"initData": _signed_init_data()})
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "error",
        [_db_operational_error(), DNS_ERROR, sa_exc.TimeoutError("QueuePool limit reached"), ConnectionRefusedError()],
        ids=["db-operational", "gaierror", "pool-timeout", "refused"],
    )
    async def test_infrastructure_error_is_503_with_retry_after(self, error):
        services = _services(get_or_create_user=error)
        async with _client(services) as client:
            response = await client.get("/me", headers={"initData": _signed_init_data()})
        assert response.status_code == 503
        assert response.headers["Retry-After"] == str(auth.RETRY_AFTER_SECONDS)
        services.users.get_or_create_user.assert_awaited_once()

    async def test_unexpected_error_is_500_not_401(self):
        async with _client(_services(get_or_create_user=RuntimeError("a bug"))) as client:
            response = await client.get("/me", headers={"initData": _signed_init_data()})
        assert response.status_code == 500


@pytest.mark.regression
class TestSessionPath:
    async def test_redis_down_is_503_not_guest(self):
        services = _services(sessions=SessionService(redis=_DownRedis()))
        async with _client(services, cookies={COOKIE: "abc"}) as client:
            response = await client.get("/me")
        assert response.status_code == 503
        assert response.headers["Retry-After"] == str(auth.RETRY_AFTER_SECONDS)
        services.users.get_or_create_user.assert_not_awaited()  # never fell back to the guest

    async def test_db_down_during_user_lookup_is_503_not_guest(self):
        sessions = SimpleNamespace(validate_session=AsyncMock(return_value={"user_id": str(uuid4())}))
        services = _services(get_user_by_id=_db_operational_error(), sessions=sessions)
        async with _client(services, cookies={COOKIE: "abc"}) as client:
            response = await client.get("/me")
        assert response.status_code == 503
        services.users.get_or_create_user.assert_not_awaited()

    async def test_expired_session_falls_back_to_guest(self):
        sessions = SimpleNamespace(validate_session=AsyncMock(return_value=None))
        services = _services(sessions=sessions)
        async with _client(services, cookies={COOKIE: "expired"}) as client:
            response = await client.get("/me")
        assert response.status_code == 200
        assert services.users.get_or_create_user.await_args.args[0].id == MOCK_GUEST_USER_ID

    async def test_session_of_a_deleted_user_falls_back_to_guest(self):
        # UserService.get_user_by_id validates None into UserSchema when the row is gone
        sessions = SimpleNamespace(validate_session=AsyncMock(return_value={"user_id": str(uuid4())}))
        services = _services(get_user_by_id=lambda _id: UserSchema.model_validate(None), sessions=sessions)
        async with _client(services, cookies={COOKIE: "abc"}) as client:
            response = await client.get("/me")
        assert response.status_code == 200
        assert services.users.get_or_create_user.await_args.args[0].id == MOCK_GUEST_USER_ID


@pytest.mark.regression
async def test_no_init_data_and_no_cookie_is_the_guest():
    services = _services()
    async with _client(services) as client:
        response = await client.get("/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(MOCK_GUEST_USER_ID)
    services.sessions.validate_session.assert_not_awaited()


@pytest.mark.regression
async def test_guest_lookup_db_down_is_503():
    async with _client(_services(get_or_create_user=_db_operational_error())) as client:
        response = await client.get("/me")
    assert response.status_code == 503


class TestIsInfrastructureError:
    @pytest.mark.parametrize(
        "error",
        [
            _db_operational_error(),
            sa_exc.InterfaceError("SELECT 1", {}, Exception("connection is closed")),
            sa_exc.TimeoutError("QueuePool limit reached"),
            DNS_ERROR,
            TimeoutError(),
            ConnectionResetError(),
            OSError(101, "Network is unreachable"),
            redis_exc.ConnectionError("down"),
            redis_exc.TimeoutError("slow"),
        ],
    )
    def test_infrastructure(self, error):
        assert is_infrastructure_error(error)

    def test_wrapped_in_cause(self):
        try:
            try:
                raise DNS_ERROR
            except OSError as inner:
                raise RuntimeError("could not open the session") from inner
        except RuntimeError as outer:
            assert is_infrastructure_error(outer)

    def test_invalidated_dbapi_error(self):
        error = sa_exc.DBAPIError("SELECT 1", {}, Exception("gone"), connection_invalidated=True)
        assert is_infrastructure_error(error)

    @pytest.mark.parametrize(
        "error",
        [
            ValueError("bad"),
            RuntimeError("bug"),
            FileNotFoundError("locale.json"),
            PermissionError(),
            sa_exc.IntegrityError("INSERT", {}, Exception("duplicate key")),
        ],
    )
    def test_not_infrastructure(self, error):
        assert not is_infrastructure_error(error)
