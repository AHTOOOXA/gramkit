# DRY Review: Template-React → Core Extraction

**Date:** 2026-01-05
**Purpose:** Identify code duplication between `apps/template-react/` and `core/` before creating new apps from template.

---

## Executive Summary

After thorough analysis of `apps/template-react/` vs `core/`, I found **~1,500+ lines of duplicated code** across both frontend and backend that should be extracted to core before creating new apps.

| Category | Files | Lines | Priority |
|----------|-------|-------|----------|
| Backend routers | 2 | ~700 | HIGH |
| Backend dependencies | 2 | ~50 | HIGH |
| Frontend providers | 2 | ~600 | HIGH |
| Frontend hooks | 6 | ~300 | MEDIUM |
| Backend worker jobs | 2 | ~100 | MEDIUM |
| Frontend errors | 1 | ~50 | MEDIUM |
| **Total** | **15** | **~1,800** | |

---

## HIGH PRIORITY (Extract First)

### 1. Backend: `webhook/routers/base.py` — 100% IDENTICAL

**Files:**
- `apps/template-react/backend/src/app/webhook/routers/base.py` (68 lines)
- `apps/template/backend/src/app/webhook/routers/base.py` (68 lines)

**Duplicated Endpoints:**
```python
GET  /friends        # Get user's friends list
POST /add_friend     # Add friend by ID
GET  /create_invite  # Create invite code
POST /process_start  # TMA initialization endpoint
```

**Current Code (identical in both apps):**
```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from app.exceptions import FriendAlreadyExistsException, UserNotFoundException
from app.services.requests import RequestsService
from app.webhook.auth import get_user
from app.webhook.dependencies.service import get_services
from core.infrastructure.fastapi.rate_limiter import HARD_LIMIT, SOFT_LIMIT, limiter
from core.schemas.start import StartData, StartParamsRequest
from core.schemas.users import UserSchema

router = APIRouter()

@router.get("/friends")
@limiter.limit(SOFT_LIMIT)
async def get_friends(
    request: Request,
    services: RequestsService = Depends(get_services),
    user: UserSchema = Depends(get_user),
) -> list[UserSchema]:
    friends = await services.users.get_friends(user.id)
    return friends

# ... etc
```

**Proposed Solution:**
Move to `core/infrastructure/fastapi/routers/base.py` using dependency injection:

```python
# core/infrastructure/fastapi/routers/base.py
from typing import Callable, TypeVar

def create_base_router(
    get_services: Callable,
    get_user: Callable,
) -> APIRouter:
    router = APIRouter()

    @router.get("/friends")
    @limiter.limit(SOFT_LIMIT)
    async def get_friends(...):
        # Implementation

    return router
```

**App usage:**
```python
# app/webhook/routers/base.py
from core.infrastructure.fastapi.routers import create_base_router
from app.webhook.auth import get_user
from app.webhook.dependencies.service import get_services

router = create_base_router(get_services, get_user)
```

---

### 2. Backend: `webhook/dependencies/service.py` — 100% IDENTICAL

**Files:**
- `apps/template-react/backend/src/app/webhook/dependencies/service.py` (24 lines)
- `apps/template/backend/src/app/webhook/dependencies/service.py` (24 lines)

**Current Code (identical):**
```python
from aiogram import Bot
from arq import ArqRedis
from fastapi import Depends

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.webhook.dependencies.arq import get_arq_pool
from app.webhook.dependencies.bot import get_bot
from app.webhook.dependencies.database import get_repo
from app.webhook.dependencies.rabbit import get_rabbit_producer
from app.webhook.dependencies.redis import get_redis_client
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient

async def get_services(
    repo: RequestsRepo = Depends(get_repo),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis = Depends(get_arq_pool),
):
    yield RequestsService(repo, producer, bot, redis, arq)
```

**Proposed Solution:**
Create factory in `core/infrastructure/fastapi/dependencies/service.py`:

```python
from typing import Type, TypeVar

TRepo = TypeVar('TRepo')
TService = TypeVar('TService')

def create_get_services(
    RequestsServiceClass: Type[TService],
    get_repo: Callable,
    get_rabbit_producer: Callable,
    get_bot: Callable,
    get_redis_client: Callable,
    get_arq_pool: Callable,
):
    async def get_services(
        repo = Depends(get_repo),
        producer = Depends(get_rabbit_producer),
        bot = Depends(get_bot),
        redis = Depends(get_redis_client),
        arq = Depends(get_arq_pool),
    ):
        yield RequestsServiceClass(repo, producer, bot, redis, arq)

    return get_services
```

---

### 3. Frontend: `providers/AppInitProvider.tsx` — ~95% IDENTICAL

**Files:**
- `apps/template-react/frontend/providers/AppInitProvider.tsx` (366 lines)

**Functionality:**
- `/process_start` API call on app launch
- PostHog user identification with database ID
- Start param parsing (`i_` invite, `r_` referral, `m_` mode, `p_` page)
- User data caching in React Query
- Mode-based routing
- Subscription prefetching
- Session persistence across component remounts

**App-Specific Parts:**
- Import paths for generated hooks (`@/src/gen/hooks`)
- Mode routing destinations (e.g., `'draw' -> '/'`, `'settings' -> '/profile'`)

**Proposed Solution:**
Extract to `@tma-platform/core-react/providers/AppInitProvider`:

```tsx
// core/frontend/src/providers/AppInitProvider.tsx
export interface AppInitProviderProps {
  children: React.ReactNode;

  // Generated API functions
  processStartFn: (params: StartParamsRequest) => Promise<StartResult>;
  getUserQueryKey: () => QueryKey;
  getSubscriptionQueryKey: () => QueryKey;
  getSubscriptionFn: () => Promise<Subscription>;

  // App-specific routing
  modeRoutes?: Record<string, string>;

  // Router
  router: { push: (path: string) => void };
}

export function AppInitProvider({
  children,
  processStartFn,
  getUserQueryKey,
  getSubscriptionQueryKey,
  getSubscriptionFn,
  modeRoutes = {},
  router,
}: AppInitProviderProps) {
  // ... implementation
}
```

**App usage:**
```tsx
// app/providers/AppInitProvider.tsx
import { AppInitProvider as CoreAppInitProvider } from '@tma-platform/core-react/providers';
import { processStartProcessStartPost } from '@/src/gen/client';
import { getCurrentUserUsersMeGetQueryKey } from '@/src/gen/hooks';

export function AppInitProvider({ children }) {
  const router = useRouter();

  return (
    <CoreAppInitProvider
      processStartFn={processStartProcessStartPost}
      getUserQueryKey={getCurrentUserUsersMeGetQueryKey}
      modeRoutes={{ draw: '/', settings: '/profile' }}
      router={router}
    >
      {children}
    </CoreAppInitProvider>
  );
}
```

---

### 4. Frontend: `app/providers.tsx` — ~90% SIMILAR

**Files:**
- `apps/template-react/frontend/app/providers.tsx` (229 lines)

**Functionality:**
- Mock data injection (before SDK import)
- ErrorBoundary with fallback
- SDKProvider (Telegram SDK)
- QueryClientProvider with smart retry logic
- AppInitProvider
- ThemeProvider (next-themes)
- Sentry initialization
- PostHog initialization
- Eruda debug console (dev mode)

**App-Specific Parts:**
- Mock users config (`MOCK_USERS`)
- App-specific components (DebugPanel, ResponsiveToaster)

**Proposed Solution:**
Extract core provider setup:

```tsx
// core/frontend/src/providers/CoreProviders.tsx
export interface CoreProvidersProps {
  children: React.ReactNode;
  mockUsers: MockUser[];

  // Optional overrides
  queryClient?: QueryClient;
  sentryDsn?: string;
  posthogKey?: string;
  posthogHost?: string;

  // App-specific components
  ErrorScreen: React.ComponentType<{ error: Error }>;
  LoadingScreen: React.ComponentType;
  DebugPanel?: React.ComponentType;
  Toaster?: React.ComponentType;
}

export function CoreProviders({
  children,
  mockUsers,
  ErrorScreen,
  LoadingScreen,
  DebugPanel,
  Toaster,
  ...config
}: CoreProvidersProps) {
  // ... common setup
}
```

---

### 5. Backend: `webhook/routers/demo.py` — ~95% IDENTICAL

**Files:**
- `apps/template-react/backend/src/app/webhook/routers/demo.py` (638 lines)
- `apps/template/backend/src/app/webhook/routers/demo.py` (628 lines)

**Endpoints (TanStack Query pattern demos):**
```python
GET  /demo/loading          # Artificial delay demo
GET  /demo/error            # Error handling demo
GET  /demo/random-error     # Random failure demo
GET  /demo/cached-data      # Cache demonstration
POST /demo/optimistic       # Optimistic updates
GET  /demo/parallel-a       # Parallel queries
GET  /demo/parallel-b
GET  /demo/items            # Infinite scroll
GET  /demo/polling          # Polling demo
GET  /demo/ai-stream        # SSE streaming
POST /demo/mutation         # Mutation demo
GET  /demo/http-errors/{code}  # HTTP status codes
GET  /demo/flaky            # Retry demo
GET  /demo/network-status   # Network status
# ... more
```

**Differences:**
- Mock data structure (tarot uses list comprehension, template-react uses `MockItem` class)
- Minor response formatting

**Proposed Solution:**
Move to `core/infrastructure/fastapi/routers/demo.py`:

```python
# Make mock data configurable
def create_demo_router(
    mock_items: list[dict] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/demo", tags=["Demo"])
    items = mock_items or DEFAULT_MOCK_ITEMS
    # ... implementation
    return router
```

---

## MEDIUM PRIORITY

### 6. Frontend: Auth Hooks — Same Patterns

| Hook | Lines | Purpose |
|------|-------|---------|
| `hooks/useAuth.ts` | 65 | Auth state from AppInit context |
| `hooks/useLogout.ts` | ~40 | Session cleanup, cache clear |
| `hooks/useEmailAuth.ts` | ~80 | Email login/signup flow |
| `hooks/usePasswordReset.ts` | ~60 | Password reset flow |
| `hooks/useTelegramLink.ts` | ~50 | Telegram account linking |
| `hooks/useTelegramDeeplinkLogin.ts` | ~40 | Deeplink auth flow |

**Current `useAuth.ts`:**
```typescript
import { useAppInit } from '@/providers/AppInitProvider';

export type UserRole = 'user' | 'admin' | 'owner';

export function useAuth() {
  const { user, isLoading, isReady, error, reinitialize } = useAppInit();

  const isGuest = !user || user.user_type === 'GUEST';
  const isAuthenticated = user?.user_type === 'REGISTERED';
  const role = (isAuthenticated ? user.role : null) as UserRole | null;
  const isAdmin = role === 'admin';
  const isOwner = role === 'owner';
  const isAdminOrOwner = isAdmin || isOwner;

  return {
    user,
    role,
    isAuthenticated,
    isGuest,
    isAdmin,
    isOwner,
    isAdminOrOwner,
    isLoading,
    isReady,
    error,
    reinitialize,
  };
}
```

**Proposed Solution:**
Create hook factories in `@tma-platform/core-react/hooks`:

```typescript
// core/frontend/src/hooks/createUseAuth.ts
export function createUseAuth(useAppInit: () => AppInitContextValue) {
  return function useAuth() {
    const { user, isLoading, isReady, error, reinitialize } = useAppInit();
    // ... same logic
  };
}

// App usage:
import { createUseAuth } from '@tma-platform/core-react/hooks';
import { useAppInit } from '@/providers';

export const useAuth = createUseAuth(useAppInit);
```

---

### 7. Frontend: `lib/errors.ts` — Should Merge with Core

**Current app errors (52 lines):**
```typescript
export class InitializationError extends Error {
  constructor(message: string, public cause?: unknown) {
    super(message);
    this.name = 'InitializationError';
  }
}

export class SDKError extends Error { ... }
export class ProcessStartError extends Error { ... }
export class InitDataError extends Error { ... }
```

**Core already has:**
- `core/frontend/src/errors/types.ts` - ApiError type
- `core/frontend/src/errors/classify.ts` - HTTP/network error classification

**Proposed Solution:**
Merge into `@tma-platform/core-react/errors`:

```typescript
// core/frontend/src/errors/init-errors.ts
export class InitializationError extends Error { ... }
export class SDKError extends Error { ... }
export class ProcessStartError extends Error { ... }
export class InitDataError extends Error { ... }

// core/frontend/src/errors/index.ts
export * from './types';
export * from './classify';
export * from './init-errors';  // NEW
```

---

### 8. Backend: Worker Jobs — Partially Duplicated

**Common jobs in both apps:**
- `admin_broadcast_job` - Send notification to admin
- `user_broadcast_job` - Send notification to user

**Proposed Solution:**
Move to `core/infrastructure/arq/jobs/broadcast.py`:

```python
# core/infrastructure/arq/jobs/broadcast.py
async def admin_broadcast_job(ctx: dict, message: str):
    """Send notification to admin users."""
    ...

async def user_broadcast_job(ctx: dict, user_id: UUID, message: str):
    """Send notification to specific user."""
    ...
```

---

## LOW PRIORITY (Keep in Apps)

These items are correctly app-specific and should NOT be moved to core:

| Item | Location | Reason |
|------|----------|--------|
| `config.py` | `app/config.py` | App-specific settings (cookie names, feature flags) |
| `webhook/routers/admin.py` | `app/webhook/routers/admin.py` | Different admin actions per app |
| `services/requests.py` | `app/services/requests.py` | Service composition is app-specific |
| `domain/products.py` | `app/domain/products.py` | App-specific product catalog |
| Demo components | `components/demo/` | Different demos showcase app features |
| UI components | `components/ui/` | Already using shadcn pattern (copy-paste) |
| `services/base.py` | `app/services/base.py` | Minor differences (bot optional vs required) |

---

## Proposed Core Package Structure After Extraction

```
core/
├── backend/src/core/
│   ├── infrastructure/
│   │   ├── fastapi/
│   │   │   ├── routers/
│   │   │   │   ├── base.py          ← NEW (friends, invite, process_start)
│   │   │   │   ├── demo.py          ← NEW (TanStack Query demos)
│   │   │   │   ├── health.py        # existing
│   │   │   │   ├── auth_telegram.py # existing
│   │   │   │   └── ...
│   │   │   └── dependencies/
│   │   │       └── service.py       ← NEW (get_services factory)
│   │   └── arq/
│   │       └── jobs/
│   │           ├── balance.py       # existing
│   │           ├── notifications.py # existing
│   │           └── broadcast.py     ← NEW (admin/user broadcast)
│   └── ...
│
└── frontend/src/
    ├── providers/
    │   ├── AppInitProvider.tsx      ← NEW
    │   ├── CoreProviders.tsx        ← NEW
    │   └── index.ts
    ├── hooks/
    │   ├── createUseAuth.ts         ← NEW
    │   ├── createUseLogout.ts       ← NEW
    │   └── auth/
    │       ├── createUseEmailAuth.ts     ← NEW
    │       ├── createUseTelegramLink.ts  ← NEW
    │       └── index.ts
    ├── errors/
    │   ├── types.ts                 # existing
    │   ├── classify.ts              # existing
    │   ├── init-errors.ts           ← NEW
    │   └── index.ts
    └── ...
```

---

## Recommended Extraction Order

1. **`routers/base.py`** → Core
   - Simplest extraction
   - Zero risk (pure duplication)
   - Immediate benefit for new apps

2. **`dependencies/service.py`** → Core
   - Factory pattern
   - Required by routers

3. **`routers/demo.py`** → Core
   - Reference implementation
   - Large code reduction

4. **`AppInitProvider.tsx`** → Core
   - Biggest frontend impact
   - Complex but well-isolated

5. **`providers.tsx`** → Core
   - Provider stack
   - Depends on AppInitProvider

6. **Auth hooks** → Core
   - After providers work
   - Hook factories

7. **Worker jobs** → Core
   - Small impact
   - Can do anytime

---

## Migration Checklist

### For Each Extraction:

- [ ] Read both app implementations
- [ ] Identify differences
- [ ] Design core API (props/params for customization)
- [ ] Implement in core
- [ ] Update template-react to use core
- [ ] Update tarot to use core
- [ ] Test both apps
- [ ] Remove duplicated code from apps

### After All Extractions:

- [ ] Update template documentation
- [ ] Create new app checklist (what to customize)
- [ ] Run full test suite on all apps
- [ ] Update CLAUDE.md if patterns changed
