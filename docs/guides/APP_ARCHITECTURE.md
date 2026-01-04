# App Architecture & Core Integration

**Purpose:** How an app is structured, connects to core, and where the entry points are.

---

## App Structure Overview

```
apps/{app}/
├── backend/
│   └── src/app/
│       ├── webhook/          # FastAPI entry point
│       │   ├── app.py        # FastAPI app factory
│       │   ├── routers/      # App-specific endpoints
│       │   ├── auth.py       # get_user override
│       │   └── dependencies/ # get_services override
│       ├── tgbot/            # Telegram bot entry point
│       │   ├── bot.py        # Bot factory
│       │   └── handlers/     # Bot handlers
│       ├── worker/           # ARQ worker entry point
│       │   ├── worker.py     # Worker settings
│       │   └── jobs/         # Background jobs
│       ├── services/         # App business logic
│       │   └── requests.py   # RequestsService aggregator
│       ├── infrastructure/
│       │   └── database/
│       │       ├── models/   # App-specific models
│       │       └── repo/     # App-specific repositories
│       │           └── requests.py  # RequestsRepo aggregator
│       ├── config.py         # Settings from .env
│       ├── migrations/       # Alembic migrations
│       └── tests/
│
├── frontend/
│   └── src/
│       ├── gen/              # Generated API client (Kubb) - DO NOT EDIT
│       ├── app/
│       │   ├── store/        # Client state (theme, modals)
│       │   ├── presentation/ # UI components
│       │   └── composables/  # Business logic hooks
│       └── main.ts           # Frontend entry point
│
├── .env                      # App configuration
└── docker-compose.local.yml  # Docker services
```

---

## Entry Points

### FastAPI (webhook/app.py)

Creates HTTP API server with core + app routers.

```python
from core.infrastructure.fastapi import create_api
from core.infrastructure.fastapi import dependencies as core_deps
from core.infrastructure.fastapi.routers import (
    auth_telegram, payments, subscriptions, users, webhooks
)
from app.infrastructure.database.repo.requests import RequestsRepo
from app.webhook.auth import get_user as app_get_user
from app.webhook.dependencies.service import get_services as app_get_services

app = create_api(
    config=settings.web,
    db_config=settings.db,
    repo_class=RequestsRepo,      # App's composed repo
    routers=[
        # Core routers
        auth_telegram.router,
        payments.router,
        subscriptions.router,
        users.router,
        webhooks.yookassa_router,
        webhooks.telegram_stars_router,
        # App-specific routers
        app_routers.base.router,
        app_routers.custom.router,
    ],
    title="My App API",
    version="1.0.0",
    root_path=settings.web.api_root_path,
)

# REQUIRED: Override core dependencies with app-specific implementations
app.dependency_overrides[core_deps.get_user] = app_get_user
app.dependency_overrides[core_deps.get_services] = app_get_services
```

**Dependency Override - get_services:**
```python
# app/webhook/dependencies/service.py
async def get_services(
    repo: RequestsRepo = Depends(get_repo),
    producer = Depends(get_rabbit_producer),
    bot: Bot = Depends(get_bot),
    redis = Depends(get_redis_client),
    arq: ArqRedis = Depends(get_arq_pool),
):
    yield RequestsService(repo, producer, bot, redis, arq)
```

---

### Telegram Bot (tgbot/bot.py)

Creates bot with middleware chain and handlers.

```python
from core.infrastructure.telegram import create_tg_bot
from core.infrastructure.dependencies import Dependencies
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.tgbot.handlers import routers_list

bot, dp, deps = create_tg_bot(
    config=settings.bot,
    db_config=settings.db,
    redis_config=settings.redis,
    repo_class=RequestsRepo,
    service_class=RequestsService,
    routers=routers_list,
    dependencies=Dependencies(
        redis_config=settings.redis,
        rabbit_config=settings.rabbit,
    ),
)

# Start polling
await dp.start_polling(bot)
```

**Middleware chain (auto-configured):**
1. `DatabaseMiddleware` - Creates session + repo per update
2. `ServiceMiddleware` - Creates services from repo
3. `AuthMiddleware` - Authenticates user via services.users
4. `I18nMiddleware` - Sets locale from authenticated user

---

### ARQ Worker (worker/worker.py)

Creates background job processor.

```python
from core.infrastructure.arq import create_worker_settings
from arq import cron
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.worker.jobs import my_job, daily_cleanup_job

WorkerSettings = create_worker_settings(
    bot_config=settings.bot,
    db_config=settings.db,
    redis_config=settings.redis,
    repo_class=RequestsRepo,
    service_class=RequestsService,
    job_functions=[
        my_job,
        daily_cleanup_job,
    ],
    cron_jobs=[
        cron(daily_cleanup_job, hour=3, minute=0),
    ],
)
```

**Job pattern:**
```python
from core.infrastructure.arq.factory import inject_context, WorkerContext

@inject_context
async def my_job(ctx: WorkerContext, user_id: str):
    async with ctx.with_transaction() as services:
        await services.users.do_something(user_id)
```

---

## Composition Pattern

### RequestsRepo (Repository Aggregator)

```python
# app/infrastructure/database/repo/requests.py
from functools import cached_property
from core.infrastructure.database.repo.requests import CoreRequestsRepo

class RequestsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._core = CoreRequestsRepo(session)  # Compose core

    # === DELEGATED FROM CORE ===
    @cached_property
    def users(self) -> UserRepo:
        return self._core.users

    @cached_property
    def payments(self) -> PaymentRepo:
        return self._core.payments

    @cached_property
    def subscriptions(self) -> SubscriptionRepo:
        return self._core.subscriptions

    @cached_property
    def groups(self) -> GroupRepo:
        return self._core.groups

    # === APP-SPECIFIC ===
    @cached_property
    def readings(self) -> ReadingsRepo:
        return ReadingsRepo(self.session)

    @cached_property
    def chat_sessions(self) -> ChatSessionRepo:
        return ChatSessionRepo(self.session)
```

### RequestsService (Service Aggregator)

```python
# app/services/requests.py
from functools import cached_property
from core.services.requests import CoreRequestsService

class RequestsService:
    def __init__(self, repo: RequestsRepo, producer, bot, redis, arq):
        self.repo = repo
        self.producer = producer
        self.bot = bot
        self.redis = redis
        self.arq = arq
        self._core = CoreRequestsService(
            repo=repo._core,
            producer=producer,
            bot=bot,
            redis=redis,
            arq=arq,
            products=products,  # App-specific product catalog
        )

    # === DELEGATED FROM CORE ===
    @cached_property
    def users(self) -> UserService:
        return self._core.users

    @cached_property
    def payments(self) -> PaymentsService:
        return self._core.payments

    @cached_property
    def subscriptions(self) -> SubscriptionsService:
        return self._core.subscriptions

    # === APP-SPECIFIC ===
    @cached_property
    def readings(self) -> ReadingsService:
        return ReadingsService(self.repo, self.producer, self, self.bot)

    @cached_property
    def chat(self) -> ChatService:
        return ChatService(self.repo, self.producer, self, self.bot)
```

---

## Configuration Flow

```
.env file
    ↓
Settings class (app/config.py)
    ↓
Entry points (app.py, bot.py, worker.py)
    ↓
Core factories (create_api, create_tg_bot, create_worker_settings)
    ↓
Running services
```

**Config class pattern:**
```python
# app/config.py
from core.infrastructure.config import (
    BotSettings, DatabaseSettings, RedisSettings, WebSettings
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",  # DB__HOST -> db.host
    )

    app_name: str = "myapp"
    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    bot: BotSettings = BotSettings()
    web: WebSettings = WebSettings()

settings = Settings()
```

---

## Core Provides

### Models
- `User` - User account (Telegram + Email auth)
- `Payment`, `PaymentEvent` - Payment transactions
- `Subscription` - Recurring subscriptions
- `Group`, `GroupMember`, `GroupInvite` - Groups
- `Friendship` - User connections

### Services
- `UserService` - User management
- `PaymentsService` - Payment processing (Stars + YooKassa)
- `SubscriptionsService` - Subscription lifecycle
- `AuthService` - Authentication (Telegram, email, deep-link)
- `GroupService`, `InvitesService` - Group management
- `SessionService` - Redis sessions
- `WorkerService` - Job scheduling
- `MessageService` - Broadcasting

### FastAPI Routers
- `/auth/*` - Authentication endpoints
- `/users/*` - User profile
- `/payments/*` - Payment processing
- `/subscriptions/*` - Subscription management
- `/webhooks/*` - Payment webhooks

### Infrastructure
- `create_api()` - FastAPI factory
- `create_tg_bot()` - Bot factory
- `create_worker_settings()` - Worker factory
- Database session management
- Redis session management
- Rate limiting, CORS, security headers

---

## App Adds

### Required
1. **RequestsRepo** - Compose `CoreRequestsRepo` + app repos
2. **RequestsService** - Compose `CoreRequestsService` + app services
3. **Config class** - Implement core config protocols
4. **Dependency overrides** - `get_services`, `get_user`
5. **App-specific routers** - Business logic endpoints

### Optional
- App-specific models (in `infrastructure/database/models/`)
- App-specific services (in `services/`)
- Bot handlers (in `tgbot/handlers/`)
- Worker jobs (in `worker/jobs/`)
- Frontend screens

---

## Dependency Injection

### Core provides stubs (MUST override):
```python
# These raise NotImplementedError if not overridden
get_services(repo) -> RequestsService
get_user(request) -> User | None
```

### Core provides working defaults:
```python
# These work automatically
get_repo(request) -> RequestsRepo  # Uses app.state.repo_class
get_telegram_auth(request) -> TelegramAuthenticator  # Uses app.state.telegram_auth
```

### App overrides pattern:
```python
# In app.py
app.dependency_overrides[core_deps.get_services] = app_get_services
app.dependency_overrides[core_deps.get_user] = app_get_user
```

---

## Related Docs

- `CLAUDE.md` - Project overview and commands
- `docs/guides/CORE_STRUCTURE.md` - What core provides in detail
- `docs/guides/NEW_APP_FROM_TEMPLATE.md` - Creating new apps
- `docs/architecture/CORE_APP_SPLIT_GUIDE.md` - Core vs app decisions
