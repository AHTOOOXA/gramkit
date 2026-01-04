# Backend Patterns

## Quick Checklist

- [ ] Core vs App decision made ("Will 2+ apps need this?")
- [ ] 3-layer pattern: Interface → Service → Repository
- [ ] `flush()` not `commit()` in repositories
- [ ] `@cached_property` on aggregator properties
- [ ] `datetime.now(UTC)` for all datetimes
- [ ] `TIMESTAMP(timezone=True)` for model columns
- [ ] Migration created after model changes
- [ ] Tests written with correct markers

---

## Tech Stack

- Python 3.14
- FastAPI (web framework)
- SQLAlchemy (ORM)
- Alembic (migrations)
- Aiogram (Telegram bot)
- ARQ (worker queue)
- PostgreSQL + Redis

---

## Core vs App Decision

**Ask: "Will 2+ apps need this exact functionality?"**
- **YES** → `core/`
- **NO** → `apps/{app}/`

| Code Type | Core (shared) | App (specific) |
|-----------|---------------|----------------|
| Models | User, Payment, Subscription | Reading, Card, Spread |
| Repositories | UserRepo, PaymentRepo | ReadingsRepo, CardsRepo |
| Services | UserService, PaymentService | AppService |
| API Routes | /auth/*, /payments/*, /users/* | /readings, /spreads |
| Bot Handlers | Payment pre_checkout | /start, /daily, custom |
| Worker Jobs | (framework only) | generate_daily_reading |

---

## Layer Architecture

**3-Layer Pattern:**
```
Interface Layer (webhook/tgbot/worker)
    ↓
Service Layer (business logic)
    ↓
Repository Layer (data access)
```

## Repository Layer

**Pattern:** Repository handles all database operations.

- Use `BaseRepo` as parent class
- Use `flush()` NOT `commit()` (transactions managed at interface layer)
- Custom query methods belong in repository, not service
- Pessimistic locking: `get_by_id_with_lock()` for race-prone operations (balance, payments)

**Example:**
```python
class MyEntityRepo(BaseRepo[MyEntity]):
    def get_by_user_id(self, user_id: int) -> list[MyEntity]:
        return self.session.scalars(
            select(MyEntity).where(MyEntity.user_id == user_id)
        ).all()
```

**Location:**
- Core entities: `core/backend/src/core/infrastructure/database/repo/`
- App entities: `apps/template/backend/src/app/infrastructure/database/repo/`

## Service Layer

**Pattern:** Service contains business logic only.

- No database commits (use repository's flush())
- No direct database queries (use repository methods)
- Return domain objects or DTOs
- Handle business validation and orchestration

**Example:**
```python
class MyService:
    def __init__(self, repo: RequestsRepo):
        self.repo = repo

    def do_business_logic(self, user_id: int) -> MyEntity:
        entity = self.repo.my_entity.get_by_user_id(user_id)
        # Business logic here
        self.repo.my_entity.flush()
        return entity
```

**Location:**
- Core services: `core/backend/src/core/services/`
- App services: `apps/template/backend/src/app/services/`

## Composition + Aggregator Pattern

**Core provides base aggregators:**
```python
class CoreRequestsRepo:
    @cached_property
    def users(self) -> UserRepo:
        return UserRepo(self.session)
```

**App composes core + adds app-specific:**
```python
class RequestsRepo:
    def __init__(self, session: AsyncSession):
        self._core = CoreRequestsRepo(session)

    @cached_property
    def users(self) -> UserRepo:
        return self._core.users  # Delegated to core

    @cached_property
    def readings(self) -> ReadingsRepo:
        return ReadingsRepo(self.session)  # App-specific
```

**Same pattern for services:**
- `CoreRequestsService` → `RequestsService`

## Transaction Management

**Pattern:** 1 Request → 1 Session → 1 Transaction → Commit/Rollback

**Transaction boundaries:**
- **Webhook (FastAPI):** Managed by `get_repo()` dependency
- **Bot (Telegram):** Managed by `DatabaseMiddleware`
- **Worker (ARQ):** Managed by `WorkerContext.with_transaction()`

**In repository layer:**
- Use `flush()` to write to database within transaction
- Don't use `commit()` - transaction will commit at interface layer
- Use `get_by_id_with_lock()` for pessimistic locking

## Interface Layers

### Webhook (FastAPI API)

**Location:** `apps/template/backend/src/app/webhook/`

**Pattern:**
```python
@router.get("/endpoint")
async def endpoint(
    services: RequestsService = Depends(get_services)
) -> ResponseModel:
    result = services.my_service.do_something()
    return ResponseModel.from_domain(result)
```

### Bot (Telegram handlers)

**Location:** `apps/template/backend/src/app/tgbot/handlers/`

**Pattern:**
```python
@router.message(F.text == "command")
async def handler(message: Message):
    services = router.services
    result = services.my_service.do_something()
    await message.answer(str(result))
```

### Worker (Background jobs)

**Location:** `apps/template/backend/src/app/worker/jobs/`

**Pattern:**
```python
async def my_job(ctx: WorkerContext, param: str):
    async with ctx.with_transaction() as services:
        result = services.my_service.do_something(param)
    # Transaction commits here
```

## Datetime Handling (CRITICAL)

**ALWAYS use timezone-aware datetimes. This is required for PostgreSQL `TIMESTAMP WITH TIME ZONE` columns.**

### Correct Pattern
```python
from datetime import UTC, datetime
from sqlalchemy import TIMESTAMP

# Getting current time
now = datetime.now(UTC)  # ✅ Timezone-aware UTC

# Creating fixed datetime
fixed = datetime(2024, 1, 1, tzinfo=UTC)  # ✅ Timezone-aware

# In SQLAlchemy models
created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))  # ✅
```

### NEVER Use (Deprecated/Broken)
```python
# ❌ WRONG - creates naive datetime, will cause DB errors
datetime.now()           # Naive, local timezone - BREAKS with TIMESTAMPTZ
datetime.utcnow()        # Naive, deprecated in Python 3.12+
datetime(2024, 1, 1)     # Naive datetime

# ❌ WRONG - DateTime without timezone
from sqlalchemy import DateTime
created_at = mapped_column(DateTime)  # Creates TIMESTAMP WITHOUT TIME ZONE
```

### Why This Matters
- PostgreSQL columns are `TIMESTAMP WITH TIME ZONE` (timestamptz)
- asyncpg driver throws error when mixing aware/naive datetimes:
  ```
  can't subtract offset-naive and offset-aware datetimes
  ```
- Python 3.12+ deprecates `datetime.utcnow()` with warnings

### Quick Reference
| Operation | Correct | Wrong |
|-----------|---------|-------|
| Current time | `datetime.now(UTC)` | `datetime.now()`, `datetime.utcnow()` |
| Fixed date | `datetime(2024, 1, 1, tzinfo=UTC)` | `datetime(2024, 1, 1)` |
| Model column | `TIMESTAMP(timezone=True)` | `DateTime`, `DateTime()` |

## Database Models

**Location:**
- Core models: `core/backend/src/core/infrastructure/database/models/`
- App models: `apps/template/backend/src/app/infrastructure/database/models/`

**Pattern:**
```python
class MyEntity(Base):
    __tablename__ = "my_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
```

**After creating/modifying models:**
1. `make migration msg="add my_entity table"`
2. `make upgrade`
3. `make test`

## Database Migrations

**ALWAYS create migrations after model changes.**

**Workflow:**
1. Change model file
2. `make migration msg="descriptive message"`
3. Review generated migration in `apps/template/backend/src/app/migrations/versions/`
4. `make upgrade`
5. `make test`

**Migration location:**
- `apps/template/backend/src/app/migrations/versions/`

## Authentication Architecture (IMPORTANT)

**All authentication methods live in ONE service: `AuthService`**

```
AuthService (core/services/auth.py)
├── Telegram code auth
│   ├── send_verification_code()
│   └── verify_code()
├── Deep link auth
│   ├── create_link_token()
│   ├── get_link_status()
│   ├── verify_link_token()
│   └── consume_link_token()
└── Email auth (email_ prefix)
    ├── email_start_signup()
    ├── email_complete_signup()
    ├── email_login()
    ├── email_start_link()
    ├── email_complete_link()
    ├── email_start_reset()
    ├── email_complete_reset()
    └── email_resend_code()
```

**Why NOT separate EmailAuthService?**
- Consolidates all auth logic in one place
- Uses same BaseService pattern as other services
- Email sending is built directly into AuthService (via `email_config`)
- No need for separate EmailSender protocol - just `import resend` directly

**Email config passed through service chain:**
```python
# App's RequestsService passes email_config to core
self._core = CoreRequestsService(
    repo=repo,
    email_config=email_config,  # Has: resend_api_key, email_from_address, email_from_name
    ...
)

# CoreRequestsService passes to AuthService
@cached_property
def auth(self) -> AuthService:
    return AuthService(self.repo, self.producer, self, self.bot, email_config=self.email_config)
```

## FastAPI Router Patterns (IMPORTANT)

### Use Regular Routers, NOT Factory Functions

**❌ WRONG - Factory pattern (unnecessary complexity):**
```python
def create_email_auth_router(get_services: Callable, ...) -> APIRouter:
    router = APIRouter(...)
    @router.post(...)
    async def endpoint(services=Depends(get_services)):
        ...
    return router

# In app.py
email_router = create_email_auth_router(get_services=app_get_services)
app.include_router(email_router)
```

**✅ CORRECT - Regular router with dependency overrides:**
```python
# In core/infrastructure/fastapi/routers/auth_email.py
from core.infrastructure.fastapi.dependencies import get_services

router = APIRouter(prefix="/auth", tags=["email-auth"])

@router.post("/login/email")
async def login(services: CoreRequestsService = Depends(get_services)):
    ...

# In app.py - just add to routers list
app = create_api(
    routers=[
        auth_email.router,  # Add to list like all other routers
        auth_telegram.router,
        payments.router,
        ...
    ],
)

# Dependency override handles app-specific services
app.dependency_overrides[core_deps.get_services] = app_get_services
```

### Core Dependencies (use these, don't create wrappers)

```python
from core.infrastructure.fastapi.dependencies import (
    get_services,        # Returns RequestsService
    get_current_user_id, # Returns user_id or None
    get_user,            # Returns authenticated user
)
```

**❌ WRONG - Creating wrapper dependencies:**
```python
# Don't do this - useless wrapper
async def get_auth_service(services = Depends(get_services)) -> AuthService:
    return services.auth  # Just access services.auth directly!
```

**✅ CORRECT - Use services directly:**
```python
from core.infrastructure.session import set_session_cookie

@router.post("/endpoint")
async def endpoint(response: Response, services: RequestsService = Depends(get_services)):
    result = await services.auth.email_login(...)  # Access auth directly
    set_session_cookie(response, result["session_id"], services.session_config)  # Cookie via function
```

### Router Registration

**All routers go in the `routers=[]` list:**
```python
from core.infrastructure.fastapi.routers import (
    auth_email,
    auth_telegram,
    auth_telegram_link,
    payments,
    subscriptions,
    users,
    webhooks,
)

app = create_api(
    routers=[
        auth_telegram.router,
        auth_email.router,
        auth_telegram_link.router,
        payments.router,
        subscriptions.router,
        users.router,
        webhooks.yookassa_router,
        webhooks.telegram_stars_router,
        routers.base.router,      # App-specific routers
        routers.admin.router,
    ],
)
```

**No separate `app.include_router()` calls needed!**

## Session Management

**Separation of concerns:**
- `services.sessions` → SessionService (CRUD, Redis)
- Cookie functions → HTTP concern only

```python
# Service creates session
session_id = await services.sessions.create_session(user_id, user_type)

# Router handles cookie
from core.infrastructure.session import set_session_cookie, clear_session_cookie

set_session_cookie(response, session_id, services.session_config)
clear_session_cookie(response, services.session_config)
```

## Testing

**Testing pattern: 80/15/5**
- 80% contract tests (interfaces: API, bot, worker)
- 15% business logic tests (complex algorithms)
- 5% regression tests (bug fixes)

**Fixtures available:**
- `session` - Database session
- `repo` - RequestsRepo instance
- `services` - RequestsService instance
- `user` - Test user
- `balance` - User balance

**Markers:**
```python
@pytest.mark.contract
def test_api_endpoint(): ...

@pytest.mark.business_logic
def test_complex_calculation(): ...

@pytest.mark.regression
def test_bug_123_fix(): ...
```

**Location:**
- `apps/template/backend/src/app/tests/`

**Run tests:**
- `make test` - All tests (parallel)
- `make test-file file=path/to/test.py` - Specific file

---

## Red Flags (Anti-Patterns)

**Using TYPE_CHECKING:**
```python
# ❌ WRONG - causes import issues at runtime, breaks dependency injection
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services import SomeService

# ✅ CORRECT - just import directly
from app.services import SomeService
```

**Importing app in core:**
```python
# ❌ WRONG - core should never import from app
from app.services.readings import ReadingsService
```

**Duplicating core features:**
```python
# ❌ WRONG - core already has PaymentService
class MyPaymentService: ...
```

**Hard-coding app logic in core:**
```python
# ❌ WRONG - "App feature" is app-specific
message = "Your tarot reading is ready"
```

**Using commit() in repository:**
```python
# ❌ WRONG - transactions managed at interface layer
self.session.commit()

# ✅ CORRECT
self.session.flush()
```

**Naive datetimes:**
```python
# ❌ WRONG
datetime.now()
datetime.utcnow()

# ✅ CORRECT
datetime.now(UTC)
```

**Business logic in interface layer:**
```python
# ❌ WRONG - logic should be in service
@router.post("/endpoint")
async def endpoint(services):
    user = services.repo.users.get(id)
    if user.balance < price:  # Business logic in router!
        raise HTTPException(...)

# ✅ CORRECT - delegate to service
@router.post("/endpoint")
async def endpoint(services):
    result = services.my_service.do_business_logic()
    return result
```
