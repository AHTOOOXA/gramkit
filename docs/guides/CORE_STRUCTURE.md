# Core Structure & Extension Guide

**Purpose:** What core provides and how apps extend it.

---

## Core Organization

```
core/
├── backend/src/core/
│   ├── domain/                 # Domain models (ProductCatalog)
│   ├── infrastructure/
│   │   ├── arq/               # Worker factory + jobs
│   │   ├── auth/              # Authentication utilities
│   │   ├── config/            # Settings classes
│   │   ├── database/
│   │   │   ├── models/        # User, Payment, Subscription, etc.
│   │   │   └── repo/          # Repositories + CoreRequestsRepo
│   │   ├── fastapi/
│   │   │   ├── routers/       # Auth, payments, users, webhooks
│   │   │   ├── dependencies.py
│   │   │   └── factory.py     # create_api()
│   │   ├── telegram/
│   │   │   ├── middlewares/   # Database, Service, Auth, I18n
│   │   │   └── factory.py     # create_tg_bot()
│   │   ├── i18n/              # Internationalization
│   │   ├── rabbit/            # Message queue
│   │   ├── session/           # Redis sessions
│   │   └── webhooks/          # Payment webhook validation
│   ├── schemas/               # Pydantic request/response models
│   ├── services/              # Business logic (CoreRequestsService)
│   └── testing/               # Test fixtures & contracts
│
├── frontend/src/              # Vue.js shared code
│   ├── platform/              # Telegram SDK abstraction
│   ├── api/                   # API client
│   ├── composables/           # useLayout, useLanguage, useScroll
│   ├── ui/                    # Loading components
│   ├── analytics/             # PostHog
│   ├── errors/                # Error classification
│   └── utils/                 # DOM, date, number, color
│
└── frontend-react/src/        # React shared code (same structure)
    ├── platform/              # SDKProvider, usePlatform
    ├── hooks/                 # Generic hooks
    └── ...
```

---

## Core Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | User account | `telegram_id`, `email`, `type`, `locale` |
| `Payment` | Transactions | `user_id`, `amount`, `provider`, `status` |
| `PaymentEvent` | Event log | `payment_id`, `event_type`, `data` |
| `Subscription` | Recurring | `user_id`, `tier`, `status`, `expires_at` |
| `Group` | User groups | `owner_id`, `name` |
| `GroupMember` | Membership | `group_id`, `user_id`, `is_admin` |
| `GroupInvite` | Invitations | `group_id`, `code`, `uses` |
| `Friendship` | Connections | `user_id`, `friend_id` |

**Enums:**
- `PaymentProvider`: `YOOKASSA`, `TELEGRAM_STARS`, `GIFT`
- `PaymentStatus`: `CREATED`, `WAITING_FOR_ACTION`, `SUCCEEDED`, `FAILED`, `CANCELED`
- `SubscriptionStatus`: `NONE`, `PENDING`, `ACTIVE`, `CANCELED`, `EXPIRED`
- `UserType`: `GUEST`, `REGISTERED`

---

## Core Repositories

### CoreRequestsRepo (Aggregator)

```python
class CoreRequestsRepo:
    @cached_property
    def users(self) -> UserRepo

    @cached_property
    def groups(self) -> GroupRepo

    @cached_property
    def members(self) -> GroupMemberRepo

    @cached_property
    def invites(self) -> InviteRepo

    @cached_property
    def payments(self) -> PaymentRepo

    @cached_property
    def payment_events(self) -> PaymentEventRepo

    @cached_property
    def subscriptions(self) -> SubscriptionRepo
```

### BaseRepo Methods

All repositories extend `BaseRepo[ModelType]`:

```python
async get_by_id(id) -> Model | None
async get_by_id_with_lock(id, read=False, nowait=False) -> Model | None
async get_all() -> Sequence[Model]
async create(data: dict) -> Model
async update(id, data: dict) -> Model | None
async delete(id) -> bool
async upsert(data: dict, index_elements: list) -> Model
```

---

## Core Services

### CoreRequestsService (Aggregator)

```python
class CoreRequestsService:
    @cached_property
    def users(self) -> UserService

    @cached_property
    def payments(self) -> PaymentsService

    @cached_property
    def subscriptions(self) -> SubscriptionsService

    @cached_property
    def groups(self) -> GroupService

    @cached_property
    def invites(self) -> InvitesService

    @cached_property
    def telegram_auth(self) -> AuthService

    @cached_property
    def worker(self) -> WorkerService

    @cached_property
    def start(self) -> StartService

    @cached_property
    def messages(self) -> MessageService
```

### Service Descriptions

| Service | Purpose |
|---------|---------|
| `UserService` | Create/update users, profile management |
| `PaymentsService` | Process payments via Stars or YooKassa |
| `SubscriptionsService` | Manage subscription lifecycle |
| `AuthService` | Telegram auth, email auth, deep-links |
| `GroupService` | Group CRUD operations |
| `InvitesService` | Generate/validate invite codes |
| `SessionService` | Redis session management |
| `WorkerService` | Schedule background jobs |
| `MessageService` | Send bot messages |

---

## Core Routers (FastAPI)

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `auth_telegram` | `/auth/login/telegram/*`, `/auth/logout` | Telegram auth |
| `auth_email` | `/auth/email/*` | Email verification |
| `users` | `/users/me`, `/users/profile` | User profile |
| `payments` | `/payments/products`, `/payments/start`, `/payments/status` | Payment flow |
| `subscriptions` | `/subscriptions/status`, `/subscriptions/cancel` | Subscription mgmt |
| `webhooks` | `/webhooks/yookassa`, `/webhooks/telegram-stars` | Payment callbacks |
| `health` | `/health` | Health check |

---

## Core Frontend

### Vue (`core/frontend/src/`)

| Module | Exports |
|--------|---------|
| `platform` | `useTelegram()`, `usePlatform()`, `usePlatformMock()` |
| `api` | `apiClient`, `apiFetch()` |
| `composables` | `useLanguage()`, `useLayout()`, `useScroll()` |
| `ui/loading` | `Skeleton`, `SkeletonCard`, `ContentState` |
| `analytics` | `usePostHog()` |
| `errors` | `classify()`, `ErrorType` |
| `utils` | DOM, date, number, color helpers |

### React (`core/frontend-react/src/`)

Same structure with React conventions:
- `SDKProvider` - Telegram SDK context
- `hooks/` instead of `composables/`

---

## Extension Points

### 1. Repository Composition

```python
# apps/{app}/backend/src/app/infrastructure/database/repo/requests.py
class RequestsRepo:
    def __init__(self, session):
        self._core = CoreRequestsRepo(session)  # Compose

    # Delegate core
    @cached_property
    def users(self):
        return self._core.users

    # Add app-specific
    @cached_property
    def my_feature(self):
        return MyFeatureRepo(self.session)
```

### 2. Service Composition

```python
# apps/{app}/backend/src/app/services/requests.py
class RequestsService:
    def __init__(self, repo, producer, bot, redis, arq):
        self._core = CoreRequestsService(
            repo=repo._core,
            producer=producer,
            bot=bot,
            products=my_products,  # App's product catalog
        )

    # Delegate core
    @cached_property
    def payments(self):
        return self._core.payments

    # Add app-specific
    @cached_property
    def my_feature(self):
        return MyFeatureService(self.repo, self.producer, self, self.bot)
```

### 3. App-Specific Models

```python
# apps/{app}/backend/src/app/infrastructure/database/models/my_feature.py
from core.infrastructure.database.models.base import (
    Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin
)

class MyFeature(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    # App-specific fields...
```

### 4. Worker Jobs

```python
from core.infrastructure.arq.factory import inject_context, WorkerContext

@inject_context
async def my_job(ctx: WorkerContext, user_id: str):
    async with ctx.with_transaction() as services:
        await services.my_feature.do_work(user_id)
```

### 5. Frontend Hooks

```typescript
// Wrap generated hooks for app-specific logic
import { useGetMyFeature } from '@/gen/hooks';

export function useMyFeature(id: string) {
  const query = useGetMyFeature(id);
  // Add optimistic updates, side effects, etc.
  return query;
}
```

---

## Key Patterns

### Transaction Management

**Rule:** 1 Request → 1 Session → 1 Transaction

| Layer | Transaction Owner |
|-------|-------------------|
| FastAPI | `get_repo()` dependency |
| Bot | `DatabaseMiddleware` |
| Worker | `WorkerContext.with_transaction()` |

**Repository rule:** Use `flush()` not `commit()` - transactions managed above.

### Pessimistic Locking

For race-prone operations:

```python
# Exclusive lock
user = await repo.users.get_by_id_with_lock(user_id)
user.credits -= 1
await session.flush()

# Fail-fast (don't wait)
try:
    user = await repo.users.get_by_id_with_lock(user_id, nowait=True)
except OperationalError:
    # Row locked, retry later
```

### Lazy Loading

All aggregators use `@cached_property`:
- Instantiated only on first access
- Cached for subsequent access
- No circular dependency issues

---

## What Apps Must Provide

| Required | Description |
|----------|-------------|
| `RequestsRepo` | Compose `CoreRequestsRepo` + app repos |
| `RequestsService` | Compose `CoreRequestsService` + app services |
| `get_services` override | FastAPI dependency returning `RequestsService` |
| `get_user` override | FastAPI dependency returning authenticated user |
| Config class | Settings implementing core protocols |

---

## Related Docs

- `docs/guides/APP_ARCHITECTURE.md` - How apps are structured
- `docs/guides/NEW_APP_FROM_TEMPLATE.md` - Creating new apps
- `docs/architecture/CORE_APP_SPLIT_GUIDE.md` - Core vs app decisions
- `docs/architecture/WHY_COMPOSITION.md` - Why composition over inheritance
