---
paths:
  - "core/backend/**"
  - "apps/*/backend/**"
---

# Backend rules (core + app backends)

Always-on rules (make-only, `datetime.now(UTC)`, `flush()` not `commit()` in repos, core never imports app, locking for money, no factory routers, no `TYPE_CHECKING`) live in the root `CLAUDE.md`. This file adds what the code won't tell you at a glance.

## Core or app?

- Ask: "Will a second app need this exact thing?" Yes → `core/`. No or maybe → the app. Promote to core only once a second app actually needs it. Leave a `TODO: extract to core` note rather than abstracting early.
- Check `core/` first. Don't re-implement users, auth, sessions, payments, subscriptions, groups or invites in an app.
- Core can hold routers, bot handlers and worker jobs too. It has 12 router modules in `core/backend/src/core/infrastructure/fastapi/routers/` (auth, users, payments, subscriptions, provider webhooks, health, admin, admin_broadcasts, admin_marketing_links, admin_statistics), handlers in `.../telegram/handlers/` and jobs in `.../arq/jobs/` (including `user_broadcast_job`, `marketing_links_alerts_job` and `daily_admin_statistics_job`). Put something in core when it's shared; otherwise it goes in the app.
- **Admin API is core** (`routers/admin.py`, `services/admin.py`, `services/audit_log.py`): users list/detail, payments, subscriptions, gift/revoke, role, reset, refund, the audit log and admin tasks (`GET /admin/tasks`, `POST /admin/tasks/{name}`, `services/admin_tasks.py`). Apps mount `core_admin.router` before their own `routers.admin.router` and add app-only admin endpoints there. Core's `GET /admin/users/{user_id}` catches any one-segment `/admin/users/<x>`, so app sub-routes need two segments (`/admin/users/{id}/balance`). Record admin actions with `services.audit_log.record(actor, action, ...)`.
- **Broadcasts are core** (`routers/admin_broadcasts.py`, included by `routers/admin.py`, never mounted on its own; `services/broadcasts.py`, `services/notifications/broadcasts.py`, `arq/jobs/broadcasts.py`): the 10 `/admin/broadcasts*` endpoints, scheduled promo templates and `user_broadcast_job` (send-now and the bot's `/broadcast`). Keyboard types are a registry: core has `main`; apps register theirs (e.g. `daily`) with `register_broadcast_keyboard(type, builder)` from `setup_infrastructure()`. Builders get `(button_text, locale)` and translate with `t(key, locale)`, not `i18n(key, locale=...)` (that ignores `locale` once a per-request translation is set). **One send path:** user broadcasts go through `MessageService.send_content` and `NotificationsService._deliver` (per-user delivery rows, blocked users skipped). Never call `bot.send_*` in a loop for user broadcasts.
- **Marketing links are core** (`routers/admin_marketing_links.py`, included by `routers/admin.py`; `services/marketing_links.py`, `arq/jobs/marketing.py`): `/admin/marketing-links` (list, create, `PATCH /{link_id}`), one acquisition code per placement with its `?startapp=r-<code>` / `?start=<code>` links and per-code users, activated, return after 1/7/30 days, payers, revenue, CAC/LTV/ROAS/payback, plus the hourly `marketing_links_alerts_job` (apps register it in their worker). Per-code results come from `users.referral_code` (first touch). An app defines what counts as activity by passing `CoreRequestsService(..., marketing_links_config=MarketingLinksConfig(activation=..., activity=..., activation_label=...))`: zero-argument query factories with rows labelled `(user_id, at)`; the default is "opened the app". The app's own link codes (notification buttons) go in `internal_referal_ids`, so they're never stored as a source or listed.
- **Overview, money analytics and the daily digest are core** (`routers/admin_statistics.py`, included by `routers/admin.py`; `services/statistics.py`, `services/analytics.py`, `services/admin_digest.py`, `arq/jobs/admin.py`): `GET /admin/statistics/overview` and `/admin/analytics/{revenue-timeseries,revenue-kpis,subscription-trend,subscription-breakdown,mrr}`, the `daily_admin_statistics_job` digest (apps schedule it in their worker; silent unless gathering failed) and the bot's `/stats` (core's bot admin router; it goes only to the requester). Apps add numbers through two registries in `core.services.admin_metrics`: `register_overview_card(key, fn)` (a tile on the Overview) and `register_digest_row(key, fn, order=...)` (a digest table row, a line under it, or a warning), called from one `register_admin_metrics()` in `setup_infrastructure()`. Callbacks get `(session, window: StatWindows)`, are read-only and run one after another on that session (never `gather`). `services.statistics` / `services.analytics` / `repo.analytics` must be core's (`BaseCompositionTests` checks the types). App-only analytics over app tables live on the app's admin router.
- **Balance is app code** (`apps/template-vue/backend/src/app/services/balance.py`, `.../repo/balance.py`, `.../models/balance.py`), not core. Core only knows it by name:
  - core `User.balance` is `relationship("Balance")`, so every app must define a `Balance` model;
  - core jobs (`arq/jobs/balance.py`) call `services.balance.*` on the app's service aggregator.
- No domain wording in core. A message like "your report is ready" belongs in the app.

## Real layout

```
core/backend/src/core/
├── auth/rbac.py                  # AdminUser / OwnerUser annotated deps, require_role()
├── domain/products.py            # ProductCatalog protocol (apps inject their catalog)
├── schemas/                      # UserSchema, payments, subscriptions…
├── services/                     # auth, users, sessions, subscriptions, groups, invites,
│   │                             # messages, start, telegram_link, worker, base.py
│   ├── requests.py               # CoreRequestsService (aggregator)
│   ├── payments/service.py       # PaymentsService (+ providers/)
│   └── notifications/
├── infrastructure/
│   ├── config/                   # `settings` proxy → resolves to app.config.settings
│   ├── database/models/          # User, Payment(+Event), Subscription, Group, GroupInvite, Friendship, FailedWebhook, NotificationDelivery, AuditLog, PromotionalBroadcast, MarketingLink; base.py mixins
│   ├── database/repo/            # BaseRepo (base.py), users.py, payments.py, …, requests.py = CoreRequestsRepo
│   ├── fastapi/                  # factory.py (create_api), dependencies.py, routers/
│   ├── telegram/                 # factory.py (dispatcher + middlewares), handlers/, middlewares/
│   ├── arq/                      # factory.py (WorkerContext, inject_context, create_worker_settings), jobs/
│   └── session/                  # set_session_cookie / clear_session_cookie / get_session_from_request
├── scripts/                      # base.py + runner.py for `make script`
├── testing/                      # shared fixtures + reusable contract suites
└── tests/

apps/template-vue/backend/       # template-react and new apps follow the same shape
├── migrations/versions/          # Alembic for this app. Covers core AND app models
└── src/app/
    ├── config.py                 # the concrete Settings that `settings` resolves to
    ├── exceptions.py             # BackendException + subclasses
    ├── domain/, schemas/
    ├── infrastructure/database/{models,repo}/   # repo/requests.py = RequestsRepo
    ├── services/                 # requests.py = RequestsService; balance.py, admin_metrics.py, notifications/
    ├── webhook/                  # app.py, auth.py (get_user), dependencies/, routers/{base,admin,demo}.py
    ├── tgbot/                    # bot.py, handlers/__init__.py (routers_list)
    ├── worker/                   # jobs.py, worker.py (job + cron registration)
    ├── scripts/
    └── tests/
```

## Layers and boundaries

- Interface (webhook router / bot handler / worker job) → service → repo. Routers stay thin; business rules and validation go in services.
- import-linter (`apps/<app>/backend/.importlinter`, checked by `make lint`) enforces:
  - `app.services` must not import `app.webhook` / `app.tgbot` / `app.worker`, so services never raise `HTTPException`;
  - `app.infrastructure.database.repo` must not import `app.services`;
  - `app.domain` / `app.schemas` must not import services or the interface layers.
- Everything is **async**. `BaseRepo` methods are `async` and use `await self.session.execute(...)`:
  ```python
  class MyEntityRepo(BaseRepo[MyEntity]):
      async def get_by_user_id(self, user_id: UUID) -> Sequence[MyEntity]:
          result = await self.session.execute(select(MyEntity).where(MyEntity.user_id == user_id))
          return result.scalars().all()
  ```
- Services subclass `BaseService(repo, producer, services, bot)`, using `app/services/base.py` in the app and `core/services/base.py` in core. Use `self.repo.<repo>` for data and `self.services.<other>` to call sibling services.

## Aggregators (composition, not inheritance)

- `RequestsRepo` wraps `CoreRequestsRepo` as `self._core`. `RequestsService` wraps `CoreRequestsService(repo=repo._core, products=..., ...)`. Each entry is a `@cached_property`.
- **There's no `__getattr__` fallback.** A new core repo or service must be added to `CoreRequests*` and also get a delegating `@cached_property` in every app's `RequestsRepo` / `RequestsService` that uses it. Adding it to core alone isn't enough.
- A new app repo or service goes only in the app aggregator. Its constructor is `XService(self.repo, self.producer, self, self.bot)`.
- Core services see only `CoreRequestsRepo` / `CoreRequestsService`. They can't reach app repos or services. If core needs app behaviour, inject it (the products catalog pattern) or do it in a core job, which gets the app's aggregator.

## Transactions: who commits

| Entry point | Unit of work | Commit |
|---|---|---|
| Webhook | `get_repo()` (`app/webhook/dependencies/database.py`): `session.begin()` per request | auto on exit, rollback on exception. **Before** the response is sent (function scope, below) |
| Bot | `DatabaseMiddleware` (`core/.../telegram/middlewares/database.py`): one transaction per update | auto |
| Worker | `async with ctx.with_transaction() as services:` (`core/.../arq/factory.py`) | auto on block exit. `ctx.with_repo()` has **no** transaction |
| Scripts (`core/scripts/base.py`) | `with_session()` / `with_repo()` / `with_services()` open a bare session | **you** `await session.commit()` |
| Admin tasks | run inside the admin request's transaction | auto (with the audit row) |

- **Request session scope.** FastAPI runs a `yield` dependency's exit (our commit) *after the response is sent* unless it's declared `Depends(..., scope="function")`. So:
  - **Default:** `get_services` / `get_user` open `get_repo` at `scope="function"`: the commit runs when the endpoint returns, before the client gets its 200, and a failing commit is a 500. `get_services` must `return`, not `yield` (FastAPI refuses a request-scoped `yield` dep over a function-scoped one).
  - **Streaming:** an endpoint whose `StreamingResponse` generator still uses the services after it returned takes `get_services_streaming` **and** `get_user_streaming` (request scope: the session stays open for the stream, commits after it). The templates have none that touch the database (the demo `/demo/stream` takes no session).
  - Never mix them in one endpoint, and never write a bare `Depends(get_repo)` (that's request scope): FastAPI caches the two scopes apart, so the endpoint opens a second session and can block on its own row locks. Need the repo directly? `Depends(get_repo, scope="function")`. Each app's `tests/contracts/api/test_session_scope.py` checks every route (via `core.testing.dependency_scopes`).
- Repos and services only `flush()`. In worker jobs, keep slow external calls (LLM, Telegram sends) outside `with_transaction()` blocks.
- Money: `await self.repo.<x>.get_by_id_with_lock(id)` (`SELECT … FOR UPDATE`; `read=True` / `nowait` / `skip_locked` exist) before a read-modify-write. Real uses are in `app/services/balance.py` and `core/services/payments/service.py`.

## Interfaces

- **Webhook:** `services: RequestsService = Depends(get_services)` and `user: UserSchema = Depends(get_user)`, both from `core.infrastructure.fastapi.dependencies`. Core's `get_services` / `get_user` raise `NotImplementedError` until the app overrides them. Don't write wrapper deps like `get_auth_service`. Use `services.auth` directly.
- **Router registration:** every router goes in the `routers=[...]` list of `create_api(...)` in `app/webhook/app.py`, core routers and app routers alike. Then `app.dependency_overrides[core_deps.get_services] = app_get_services` (same for `get_user`). `create_api` adds the health router itself.
- **Auth (`app/webhook/auth.py::get_user`):** checks the `Mock-Platform` header (debug only), then the Telegram `initData` header, then the session cookie. With none of them it falls back to a **shared mock guest user**. It never returns 401 for "not logged in", so gate with `core.auth.rbac`: `user: AdminUser` / `user: OwnerUser` or `Depends(require_role(...))`. Config `settings.rbac.owner_ids` always pass.
- **Sessions:** `session_id = await services.sessions.create_session(user_id, user_type)`, then `set_session_cookie(response, session_id)` / `clear_session_cookie(response)` from `core.infrastructure.session`. Cookie options come from `settings.session`; there's no config argument.
- **Bot handlers:** services are **injected as a handler argument** by `ServiceMiddleware` (`core/.../telegram/middlewares/service.py`). Write `async def cmd(message: Message, user: UserSchema, services: RequestsService)`. `repo`, `session` and `user` are injected the same way. There's no `router.services`. Register routers in `app/tgbot/handlers/__init__.py::routers_list`. Order matters: core auth/link routers must come before `start_router`, whose `CommandStart()` swallows every `/start`.
- **Worker jobs:** `@inject_context async def job(ctx: WorkerContext, ...)`, then add them to `job_functions=[...]` (and `cron_jobs`) in `app/worker/worker.py`. A job that isn't registered never runs. To wrap a core job that already has `@inject_context`, don't decorate the wrapper again (see `worker/jobs.py`).

## Errors → HTTP

- Domain errors subclass `BackendException` (`app/exceptions.py`). Its `code` is the class name, and it also carries `message` and `name`.
- **No global handler maps them.** `create_exception_handler` in `webhook/app.py` is defined but not registered. Routers catch specific exceptions and translate them:
  ```python
  except NoChatMessagesError as e:
      raise HTTPException(status_code=402, detail={"code": "NoChatMessagesError", "message": str(e)})
  ```
- `detail` is a plain string for simple cases, or `{"code", "message"}` (object detail) when the frontend branches on the error type. Streaming endpoints (see the streaming demo in `routers/demo.py`) can't change status mid-stream, so they emit an error line (`{"type": "error", "payload": {"detail": {"code", "message"}}}`) instead.
- Unhandled exceptions hit core's global handler and return `500 {"detail": str(exc)}`. Details and the frontend side are in `.claude/rules/errors.md`.

## Config, email, models, migrations

- Always `from core.infrastructure.config import settings`. It's a lazy proxy that imports `app.config` on first attribute access, so new settings go in the app's `config.py`, built from the core components in `core/infrastructure/config/components.py`.
- Email: `AuthService` (`core/services/auth.py`) holds every auth flow: Telegram code, deep-link and `email_*`. It reads `settings.email` (`api_key`, `from_address`, `from_name`) and imports `resend` lazily inside the send method. Nothing is passed through the aggregators, and there's no separate email service.
- Models: use the `CreatedAtMixin` / `UpdatedAtMixin` / `TableNameMixin` in `core/.../models/base.py` (`TIMESTAMP(timezone=True)`, `server_default=func.now()`). Never use a bare `DateTime`.
- Export new models from the package `__init__.py`. `migrations/env.py` star-imports core and app models, so an unexported model gets no migration.
- Core has **no migrations of its own**. A core model change needs `make migration` in **each app** that uses it.

## Data fixes and one-off jobs

- Data fixes on a running server are admin tasks: `@admin_task(name, description, destructive=...)` on `async def fn(session, *, dry_run) -> dict` in `app/services/admin_tasks.py` (framework: `core/services/admin_tasks.py`; register by importing the module in `app/webhook/app.py`). They run at `/admin/tasks`, owner-only and audit-logged, with dry run and apply. See `.claude/rules/prod-scripts.md`.
- Other one-off backend work (backfills, backup/restore, benchmarks) is a script under `app/scripts/` or `core/scripts/common/`, run with `make script`. Running one against a live server has a memory catch: see `.claude/rules/prod-scripts.md`.
