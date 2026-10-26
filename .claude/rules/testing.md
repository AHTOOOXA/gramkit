---
paths:
  - "**/tests/**"
  - "**/conftest.py"
  - "**/test_*.py"
---

# Backend testing rules

## Running

### What to run when

- **While iterating:** `make test-file` for the test file you're working on, `make test-quick` for everything the change touches. Don't loop on the full suite.
- **Before the commit / PR:** one full `make test APP=<app>`.
- **Core is already in every app's run** (`testpaths`), so `make test APP=template-vue` covers core. Don't rerun it per app to "check core".
- **Changed `core/`:** the templates use the same core code. If the change touches something they use (services, the notification engine, models), run `make test-quick APP=template-vue` / `APP=template-react`. CI's `test-backend.yml` runs core + templates anyway.
- **Fresh worktree:** testmon has no baseline yet, so the first `test-quick` runs everything. It's incremental from the second run.

### Targets

- `make test APP=<app>` runs the full suite, parallel `-n 2`. That means the app tests **plus core's tests** (see `testpaths` in `apps/<app>/backend/pyproject.toml`).
- `make test-quick APP=<app>` is incremental (testmon + xdist). Use it while iterating.
- `make test-file file=src/app/tests/business/test_streak_calculation.py APP=<app>` runs one file. The path is relative to `apps/<app>/backend`. A node id (`…/test_x.py::test_name`) works too.
- Never call `pytest` directly. The targets set `ENV_FILE=.env.test` and the right cwd, and they run on the host through `uv` (not in the containers).
- Postgres comes from **testcontainers** (`postgres:16-alpine`) and Redis is in-memory. You need a running Docker daemon but **not** `make up`, and CI has no service containers either.
- `--strict-markers` is on. The registered markers are `contract`, `business_logic`, `regression`, `issue(id)` and `slow`. A typo in a marker fails collection.

## What kind of test

- **Contract** (`@pytest.mark.contract`, the bulk): drive the real interface, meaning HTTP through `authenticated_client` / `client`, a worker job through `worker_ctx`, or a bot router. Use the real DB and mock only external systems (YooKassa, LLM, Telegram, PostHog, ARQ).
- **Business logic** (`@pytest.mark.business_logic`): call `services.<x>` directly for algorithms, state machines and races (`asyncio.gather` against a locked row).
- **Regression** (`@pytest.mark.regression`, plus `@pytest.mark.issue(N)` when there's an issue): reproduce the bug first. Put the date, impact and root cause in the docstring.
- Reusable core suites live in `core/testing/contracts/`: `BaseAuthTests`, `BaseHealthTests`, `BasePaymentTests`, `BaseUserTests`, `BaseAppSetupTests`, `BaseCompositionTests`, `BaseProductProtocolTests` and `BaseAdminTests` (needs `admin_client` / `owner_client`; also covers `/admin/tasks` with a registered probe task) and `BaseBroadcastTests` (the 10 `/admin/broadcasts*` endpoints; needs `admin_client` / `owner_client` and a `test_app` that overrides `get_bot` with `api_bot_mock()`, because preview and media upload send through the bot) and `BaseMarketingLinksTests` (the 3 `/admin/marketing-links*` endpoints, economics and audit rows; needs `admin_client`) and `BaseSeenFeaturesTests` (`PATCH /users/me/seen-features`: merge, key validation, 403 for the shared GUEST; needs `authenticated_client` and an unauthenticated `client`) and `BaseAdminStatisticsTests` (`GET /admin/statistics/overview` and the 5 money `/admin/analytics/*` endpoints: shapes, 403, 422 bounds, Stars vs cash series; needs `admin_client`). Subclass one in an app test (`class TestPayments(BasePaymentTests): pass`). It uses the fixtures of the directory it's in.

## Fixtures: where they come from

A test only sees the fixtures of its own folder's `conftest.py` and the ones above it. Neither core nor the
templates have a `tests/fixtures/` folder.

| Folder (`apps/template-vue/backend/src/app/tests/`) | Fixtures available |
|---|---|
| `conftest.py` (root) | `test_app` (its `get_bot` is `api_bot_mock()`), `client`, `authenticated_client`, `admin_client`, `owner_client`, `test_user`, `services`, `products_module`, `reset_demo_counters` (autouse), db + `mock_redis` |
| `contracts/worker/` | the root ones plus `mock_bot`, `worker_ctx` |
| `business/`, `regression/`, `contracts/{api,bot,core}` | the root ones |

- "db" means `postgres_container` (session scope), `db_engine` and `db_session`.
- `template-react` has `client` and `reset_demo_counters` in its root `conftest.py` and a DB-backed harness
  (with `admin_client` / `owner_client`) in `tests/admin/conftest.py`; copy that when another folder needs a DB.
- The admin route-table guards (`contracts/api/test_admin_routes.py` in template-vue, `admin/test_admin_routes.py`
  in template-react) need no DB: they read the module-level `app` (imported under the `RedisClient.__init__` patch)
  and fail when two routes share a method + path, which would shadow the later one silently.
- As an app grows, split tests **by domain** (`payments/`, `admin/`, …) with a `conftest.py` per domain that
  builds only the harness that domain needs (e.g. `admin_client` / `owner_client`, `mock_yookassa`).
- None of these exist: `unauthenticated_client` (use `client`), `test_bot` (bot tests call handlers or inspect
  `routers_list`), `mock_llm_provider`.

**Core fixtures** live in `core/backend/src/core/testing/fixtures/`:

- `database.py`: `postgres_container`, `db_engine` (runs `Base.metadata.create_all` for each test and **no Alembic**, so tests won't catch a missing migration), `db_session` (opens a transaction and rolls it back on teardown).
- `redis.py`: `mock_redis` (an `InMemoryRedis`).
- `mocks.py`: `mock_yookassa`, `mock_yookassa_webhook`, `mock_arq_enqueue`, `mock_posthog`.
- `bot.py`: `mock_bot`, `message_factory`, `update_factory`, `callback_query_factory`, and `api_bot_mock()` (a helper, not a fixture: the bot for a webhook `get_bot` override; awaitable sends, media sends return a message carrying a `file_id`).
- `worker.py`: `MockBot` (captures `messages`, `photos`, `rich_messages`, and video / animation / document sends in `media`), `create_worker_context(...)`.
- `auth.py`: `generate_telegram_init_data(...)` (a helper, not a fixture).
- `admin.py`: `admin_client`, `owner_client` (an `authenticated_client` whose user has the admin / owner role; needs the app's `test_app`).

Core has **no** `repo` or `services` fixture. Its own `core/tests/conftest.py` loads the `auth` and `database` fixtures through `pytest_plugins` and adds `balance_repo` plus a stub `Balance` model.

To use core fixtures in a new folder, import them into that folder's `conftest.py` and list them in `__all__` (copy the root `conftest.py`). Don't redefine `postgres_container` / `db_session`.

## How the harness is wired

```
postgres_container (session) ─ db_engine ─ db_session ──┐      mock_redis
                                                        ▼          │
                                                    test_app ◄─────┘   # app.dependency_overrides
                                                    /      \
                                              client   authenticated_client   # headers={"initData": generate_telegram_init_data(...)}
                                                               │
                                                           test_user          # GET /users/me → UserSchema
```

- `test_app` overrides the **app's** deps: `get_repo`, which yields `RequestsRepo(db_session)`, plus `get_redis_client`, `get_bot`, `get_arq_pool` and `get_rabbit_producer`. It also swaps `app.webhook.auth.session_redis` for `mock_redis`. On teardown it restores `dependency_overrides` and `session_redis`. Do the same in any fixture you write.
- Domain conftests import the `Balance` model **first** (core `User` references it by name). They also wrap their app imports in `patch("core.infrastructure.redis.RedisClient.__init__", ...)` so importing the app doesn't open a Redis connection.
- An `admin_client` / `owner_client` fixture should create a user through the auth flow, then change its DB role. `RBAC__OWNER_IDS` is empty in tests.
- `worker_ctx` uses `db_engine` with a real session pool, so worker jobs **really commit**. Data outlives the test, which is why it passes `clean_tables=[...]`. Add any table your job writes to that list.

## Writing tests

- The user id is random on every run and tests run in parallel. Never assert a specific id (`user_id == 1`). Create your own data in each test.
- Assert on shape with `dirty_equals` (`IsInt`, `IsStr`, `IsList`).
- Snapshots: `inline-snapshot` is installed (`snapshot()` from `inline_snapshot`) but nothing uses it yet. Snapshot tests need sequential runs, so use `make test-snapshots APP=<app>` to check them and `make test-snapshots-update APP=<app>` to rewrite them. Both run `-n0`.
- Name tests `test_<what>_<expected_behaviour>`.

## Gotchas

- **Time-window flake.** Rows get `created_at` from Postgres `now()` (`CreatedAtMixin` uses `server_default=func.now()`), while the window end comes from Python's `datetime.now(UTC)`, a few ms apart. A "created in the last N hours" query can then miss a row the same test just created. Pass an explicit window or `now=` into the code under test instead of reading the wall clock. The admin statistics take a `StatWindows` (`core.services.admin_metrics`): tests patch `StatisticsService._compute_windows` with windows that end a few minutes after now (`core/tests/integration/test_statistics_service.py`).
- **Core CI runs without `app`.** The `test-core` job in `.github/workflows/test-backend.yml` runs core's pytest with only core installed. A core test that imports `app…` passes locally and fails in CI. So does `patch("…settings")` **without `new=`**: `core.infrastructure.config.settings` is a lazy proxy, and `patch` touches its attributes, which imports `app.config`. Pass `new=` or patch a concrete attribute. To reproduce locally, hide the app with `sys.modules["app"] = None` in a conftest shim.
