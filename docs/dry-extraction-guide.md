# DRY Extraction Guide: Core Consolidation

**Date:** 2026-01-05
**Scope:** All apps — `tarot`, `template-react`, `template-vue`, `maxstat`
**Purpose:** Eliminate code duplication by extracting common functionality to `core/`

---

## Executive Summary

Analysis of all 4 apps reveals **~18,000+ lines** of duplicated code across backends. This guide provides detailed extraction plans with pros, cons, and implementation strategies for each category.

### Duplication Matrix

| File/Category | tarot | template-react | template-vue | maxstat | Total Lines |
|---------------|:-----:|:--------------:|:------------:|:-------:|------------:|
| `webhook/auth.py` | ✅ | ✅ | ✅ | ✅ | ~2,400 |
| `tgbot/handlers/admin.py` | ✅ | ✅ | ✅ | ✅ | ~6,400 |
| `webhook/routers/base.py` | ✅ | ✅ | ✅ | ~80%* | ~280 |
| `webhook/routers/demo.py` | ✅ | ✅ | ✅ | ❌ | ~2,700 |
| `services/statistics.py` | ✅ | ✅ | ✅ | ✅ | ~660 |
| `worker/jobs.py` (common) | ✅ | ✅ | ✅ | ✅ | ~1,200 |
| `exceptions.py` | ✅ | ✅ | ✅ | ✅ | ~240 |
| `services/notifications/` | ✅ | ✅ | ✅ | ✅ | ~420 |
| `webhook/dependencies/` | ✅ | ✅ | ✅ | ~90%* | ~400 |
| **Backend Total** | | | | | **~14,700** |
| Frontend providers | ✅ | ✅ | ✅ | N/A | ~1,200 |
| Frontend hooks | ✅ | ✅ | ✅ | N/A | ~600 |
| **Grand Total** | | | | | **~16,500** |

*maxstat has minor variations due to app-specific features

---

## 1. `webhook/auth.py` — Universal Authentication

### Current State
- **Files:** 4 identical copies (~583 lines each, ~19KB)
- **Location:** `apps/*/backend/src/app/webhook/auth.py`
- **Similarity:** 100% identical across tarot, template-react, template-vue, maxstat

### What It Contains
```
├── TelegramUser dataclass (lines 34-52)
├── TelegramAuthenticator class (lines 71-154)
│   ├── _parse_init_data()
│   ├── _parse_user_data()
│   ├── _validate()
│   └── verify_token()
├── Session Management (lines 212-319)
│   ├── create_session()
│   ├── validate_session()
│   ├── destroy_session()
│   ├── set_session_cookie()
│   └── clear_session_cookie()
├── Authentication helpers (lines 327-500)
│   ├── _get_mock_user_from_init_data()
│   ├── _authenticate_telegram()
│   ├── _authenticate_session()
│   └── _get_mock_guest_user()
└── get_user() dependency (lines 533-583)
```

### Critical Issue
**Core already has `TelegramAuthenticator`** at `core/infrastructure/auth/telegram.py` but apps duplicate it!

### Extraction Plan

**Move to core:**
```
core/infrastructure/auth/
├── telegram.py          # Already exists - enhance
├── session.py           # NEW - session management
└── dependencies.py      # NEW - get_user dependency
```

**What stays in apps:**
```python
# apps/*/backend/src/app/webhook/auth.py (minimal)
from core.infrastructure.auth.dependencies import create_get_user
from app.webhook.dependencies.service import get_services

# App-specific configuration only
get_user = create_get_user(get_services)
```

### Pros
- **Eliminates ~2,400 lines** of duplication
- **Security improvements** propagate to all apps automatically
- **TelegramAuthenticator already in core** — just need to use it
- Session management is app-agnostic (uses `settings.app_name` prefix)

### Cons
- Requires updating all 4 apps simultaneously
- Session cookie configuration may need per-app overrides
- Mock user handling for dev mode needs careful extraction

### Risk Level: 🟡 MEDIUM
- Authentication is critical path
- Extensive testing required before rollout
- Recommend: Extract to core, migrate one app at a time

### Implementation Order
1. Enhance `core/infrastructure/auth/telegram.py` with full `TelegramAuthenticator`
2. Create `core/infrastructure/auth/session.py` for session management
3. Create `core/infrastructure/auth/dependencies.py` with `create_get_user()` factory
4. Migrate `template-vue` first (lowest traffic)
5. Migrate `template-react`, then `tarot`, then `maxstat`

---

## 2. `tgbot/handlers/admin.py` — Admin Bot Commands

### Current State
- **Files:** 4 copies (~39-40KB each, ~960 lines)
- **Location:** `apps/*/backend/src/app/tgbot/handlers/admin.py`
- **Similarity:** ~95% identical

### What It Contains
```
├── BroadcastStates FSM (lines 62-66)
├── PromoStates FSM (lines 69-76)
├── /admin command (lines 79-104)
├── /broadcast flow (lines 107-346)
│   ├── broadcast_command()
│   ├── process_broadcast_message()
│   ├── process_keyboard_selection()
│   ├── cancel_broadcast()
│   └── confirm_broadcast()
├── /promo flow (lines 404-785)
│   ├── promo_command()
│   ├── process_promo_message()
│   ├── process_time_slot()
│   ├── process_repeat_count()
│   └── confirm_promo()
├── /promo_list (lines 788-832)
├── /promo_cancel (lines 835-867)
├── /stats command (lines 369-398)
├── /giftsub command (lines 870-963)
└── _process_media_message() helper (lines 23-59)
```

### App-Specific Parts
| App | Unique Commands |
|-----|-----------------|
| tarot | `/keygo_prediction` |
| template-react | None |
| template-vue | None |
| maxstat | Custom stats commands |

### Extraction Plan

**Move to core:**
```
core/infrastructure/telegram/handlers/
├── admin/
│   ├── __init__.py
│   ├── broadcast.py      # BroadcastStates, broadcast flow
│   ├── promo.py          # PromoStates, promo flow
│   ├── stats.py          # /stats command
│   ├── giftsub.py        # /giftsub command
│   └── base.py           # /admin menu, helpers
└── factory.py            # create_admin_router()
```

**What stays in apps:**
```python
# apps/*/backend/src/app/tgbot/handlers/admin.py
from core.infrastructure.telegram.handlers.admin import create_admin_router

# Create router with app-specific extensions
router = create_admin_router()

# Add app-specific commands
@router.message(Command("keygo_prediction"))
async def keygo_prediction_command(message, user):
    # Tarot-specific
    ...
```

### Pros
- **Eliminates ~6,400 lines** (largest duplication)
- Admin features improve across all apps
- FSM states and flows are complex — single source of truth reduces bugs
- Promotional broadcast system is identical

### Cons
- Tight coupling to `app.tgbot.keyboards` for keyboard builders
- `command_keyboard()` varies per app
- Requires keyboard abstraction or injection

### Risk Level: 🟢 LOW-MEDIUM
- Bot handlers are isolated from main app flow
- Can test independently
- Failures don't break core functionality

### Implementation Order
1. Extract `_process_media_message()` helper first
2. Extract FSM states (`BroadcastStates`, `PromoStates`)
3. Extract broadcast flow
4. Extract promo flow
5. Extract utility commands (`/stats`, `/giftsub`)
6. Create factory with keyboard injection

---

## 3. `webhook/routers/base.py` — Core API Endpoints

### Current State
- **Files:** 4 copies (~68 lines each)
- **Location:** `apps/*/backend/src/app/webhook/routers/base.py`
- **Similarity:** 100% identical (tarot, template-react, template-vue), ~80% maxstat

### What It Contains
```python
GET  /friends        # Get user's friends list
POST /add_friend     # Add friend by ID
GET  /create_invite  # Create invite code
POST /process_start  # TMA initialization endpoint
```

### Maxstat Variation
```python
# maxstat adds onboarding cookie to /process_start
if result.current_user.is_onboarded:
    response.set_cookie(key="user_onboarded", ...)
```

### Extraction Plan

**⚠️ Important:** Do NOT use factory functions (violates CLAUDE.md patterns)

**Move to core:**
```python
# core/infrastructure/fastapi/routers/base.py
from core.infrastructure.fastapi.dependencies import get_services, get_user

router = APIRouter()

@router.get("/friends")
@limiter.limit(SOFT_LIMIT)
async def get_friends(
    request: Request,
    services = Depends(get_services),
    user: UserSchema = Depends(get_user),
) -> list[UserSchema]:
    return await services.users.get_friends(user.id)

# ... other endpoints
```

**App usage (dependency overrides):**
```python
# apps/*/backend/src/app/webhook/app.py
from core.infrastructure.fastapi.routers.base import router as base_router
from core.infrastructure.fastapi.dependencies import get_services, get_user
from app.webhook.dependencies.service import get_services as app_get_services
from app.webhook.auth import get_user as app_get_user

# Override dependencies
app.dependency_overrides[get_services] = app_get_services
app.dependency_overrides[get_user] = app_get_user
app.include_router(base_router)
```

**Maxstat extension:**
```python
# apps/template-react/backend/src/app/webhook/routers/base.py
from core.infrastructure.fastapi.routers.base import router as core_router

router = APIRouter()

# Include core routes
router.include_router(core_router)

# Override with extended version
@router.post("/process_start")
async def process_start_with_cookie(request, response, ...):
    result = await services.start.process_start(user, start_params)
    if result.current_user.is_onboarded:
        response.set_cookie(...)
    return result
```

### Pros
- **Eliminates ~280 lines**
- Uses FastAPI's built-in dependency override pattern
- No custom factory functions needed
- Core endpoints guaranteed consistent across apps

### Cons
- Maxstat requires override for cookie handling
- Apps lose direct control over base endpoints
- Changes to core affect all apps simultaneously

### Risk Level: 🟢 LOW
- Simple CRUD endpoints
- Well-tested FastAPI patterns
- Easy to override per-app if needed

---

## 4. `webhook/routers/demo.py` — TanStack Query Demos

### Current State
- **Files:** 3 copies (~638-650 lines, ~18KB each)
- **Location:** `apps/{tarot,template-react,template-vue}/backend/src/app/webhook/routers/demo.py`
- **Similarity:** ~95% identical
- **Note:** maxstat does NOT have demo router (production app)

### What It Contains
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
# ... 20+ more endpoints
```

### Differences
- Mock data structure (tarot uses list comprehension vs class)
- Minor response formatting variations

### Extraction Plan

**Move to core:**
```python
# core/infrastructure/fastapi/routers/demo.py
from typing import Any

router = APIRouter(prefix="/demo", tags=["Demo"])

# Configurable mock data
DEFAULT_MOCK_ITEMS = [{"id": i, "name": f"Item {i}"} for i in range(100)]

def configure_demo_router(mock_items: list[dict] | None = None):
    """Configure demo router with optional custom mock data."""
    items = mock_items or DEFAULT_MOCK_ITEMS
    # Store in router state for endpoints to access
    router.state.mock_items = items
    return router
```

**App usage:**
```python
# Template apps include demo router
from core.infrastructure.fastapi.routers.demo import configure_demo_router

demo_router = configure_demo_router()
app.include_router(demo_router)

# Maxstat doesn't include it (production app)
```

### Pros
- **Eliminates ~2,700 lines**
- Demo endpoints are reference implementation for TanStack Query
- Templates get improvements automatically
- Production apps can exclude entirely

### Cons
- Not needed for production apps (maxstat)
- Mock data customization adds complexity
- SSE streaming endpoint may have app-specific needs

### Risk Level: 🟢 LOW
- Demo endpoints only
- No production impact
- Can be excluded per-app

---

## 5. `services/statistics.py` — Analytics Service

### Current State
- **Files:** 4 identical copies (~164 lines each)
- **Location:** `apps/*/backend/src/app/services/statistics.py`
- **Similarity:** 100% identical

### What It Contains
```python
class StatisticsService(BaseService):
    async def get_daily_statistics(self) -> dict:
        # DAU/WAU/MAU calculations
        # Revenue tracking (all-time + today)
        # Product sales stats
        # Subscription counts

    def format_statistics_message(self, stats: dict) -> str:
        # Format for Telegram admin broadcast
```

### Extraction Plan

**Move to core:**
```python
# core/services/statistics.py
class StatisticsService(CoreBaseService):
    """Base statistics service with common metrics.

    Apps can extend to add custom metrics.
    """

    async def get_daily_statistics(self) -> dict:
        """Get standard metrics (DAU/WAU/MAU, revenue, subscriptions)."""
        ...

    async def get_app_specific_statistics(self) -> dict:
        """Override in app to add custom metrics."""
        return {}

    async def get_combined_statistics(self) -> dict:
        """Combine base + app-specific stats."""
        base = await self.get_daily_statistics()
        custom = await self.get_app_specific_statistics()
        return {**base, **custom}

    def format_statistics_message(self, stats: dict) -> str:
        """Format stats for admin broadcast. Override for custom formatting."""
        ...
```

**App extension:**
```python
# apps/template/backend/src/app/services/statistics.py
from core.services.statistics import StatisticsService as CoreStatisticsService

class StatisticsService(CoreStatisticsService):
    async def get_app_specific_statistics(self) -> dict:
        # Tarot-specific: readings count, cards drawn, etc.
        return {
            "readings": {"total": ..., "today": ...},
            "trainer": {"sessions": ..., "accuracy": ...},
        }
```

### Pros
- **Eliminates ~660 lines**
- Standard metrics (DAU/WAU/MAU) guaranteed consistent
- Apps can extend with domain-specific metrics
- Admin reporting improved across all apps

### Cons
- Apps may want different time boundaries (2 AM UTC is hardcoded)
- Message formatting may need customization
- Repository method names must be consistent across apps

### Risk Level: 🟢 LOW
- Read-only service
- No side effects
- Easy to test

---

## 6. `worker/jobs.py` — Background Jobs

### Current State
- **Files:** 4 copies (~266-332 lines each)
- **Location:** `apps/*/backend/src/app/worker/jobs.py`
- **Similarity:** ~80% common jobs, ~20% app-specific

### Common Jobs (100% identical)
| Job | Lines | Description |
|-----|-------|-------------|
| `admin_broadcast_job` | ~35 | Send message to admin users |
| `user_broadcast_job` | ~120 | Send message to all users |
| `daily_admin_statistics_job` | ~35 | Daily stats to admins |
| `send_delayed_notification` | ~30 | Delayed Telegram notification |
| `test_error_job` | ~5 | Test error handling |

### App-Specific Jobs
| App | Custom Jobs |
|-----|-------------|
| tarot | `morning_notification_job`, `evening_notification_job`, `topup_daily_chat_messages_job` |
| maxstat | Custom reporting jobs |

### Extraction Plan

**Move to core:**
```python
# core/infrastructure/arq/jobs/broadcast.py
@inject_context
async def admin_broadcast_job(ctx: WorkerContext, text: str):
    """Send message to all admin users."""
    ...

@inject_context
async def user_broadcast_job(ctx: WorkerContext, broadcast_data: dict, requester_telegram_id: int):
    """Send broadcast to all users."""
    ...

# core/infrastructure/arq/jobs/statistics.py
@inject_context
async def daily_admin_statistics_job(ctx: WorkerContext):
    """Send daily statistics to admins."""
    ...

# core/infrastructure/arq/jobs/notifications.py
@inject_context
async def send_delayed_notification(ctx: WorkerContext, telegram_user_id: int, delay_seconds: int):
    """Send delayed notification."""
    ...
```

**App worker configuration:**
```python
# apps/*/backend/src/app/worker/worker.py
from core.infrastructure.arq.jobs import (
    admin_broadcast_job,
    user_broadcast_job,
    daily_admin_statistics_job,
    send_delayed_notification,
)
from app.worker.jobs import (
    morning_notification_job,  # App-specific
    evening_notification_job,  # App-specific
)

worker_settings = create_worker_settings(
    job_functions=[
        # Core jobs
        admin_broadcast_job,
        user_broadcast_job,
        daily_admin_statistics_job,
        send_delayed_notification,
        # App-specific jobs
        morning_notification_job,
        evening_notification_job,
    ],
    ...
)
```

### Pros
- **Eliminates ~1,200 lines** of common jobs
- Broadcast infrastructure shared (complex code)
- Apps compose their worker with core + custom jobs
- Bug fixes propagate automatically

### Cons
- `user_broadcast_job` has one difference: `u.user_id` vs `u.id` (needs standardization)
- Keyboard builders vary per app (`command_keyboard()`)
- i18n keys may differ (`tarot.open_app_button`)

### Risk Level: 🟡 MEDIUM
- Background jobs are critical for notifications
- Failures may be silent
- Requires careful testing of job composition

---

## 7. `exceptions.py` — Custom Exceptions

### Current State
- **Files:** 4 nearly-identical copies (~59-65 lines each)
- **Location:** `apps/*/backend/src/app/exceptions.py`
- **Similarity:** ~90% identical

### Common Exceptions
```python
BackendException          # Base class
UserNotFoundException     # User not found (also in core!)
FriendAlreadyExistsException  # Duplicate friend
NoAvailableReadingsError  # No readings left
NoChatMessagesError       # No chat messages left
NoTrainerAttemptsError    # No trainer attempts left
DailyReadingError         # Daily reading issues
QuestionReadingError      # Question reading issues
LLMError                  # LLM failure
AllLLMProvidersFailedError  # All LLM providers failed
```

### Critical Issue
**Core has `UserNotFoundException`** at `core/exceptions.py` but apps define their own incompatible version!

### Extraction Plan

**Merge into core:**
```python
# core/exceptions.py (enhanced)
class BackendException(Exception):
    """Base exception for all backend errors."""
    def __init__(self, message: str = "Service is unavailable", name: str = "BackendException"):
        self.message = message
        self.name = name
        self.code = self.__class__.__name__
        super().__init__(self.message, self.name)

class UserNotFoundException(BackendException):
    """User not found in database."""

class FriendAlreadyExistsException(BackendException):
    """Friend relationship already exists."""

# Resource limit exceptions
class ResourceLimitException(BackendException):
    """Base for resource limit errors."""

class NoAvailableReadingsError(ResourceLimitException):
    """User has no available readings."""

class NoChatMessagesError(ResourceLimitException):
    """User has no available chat messages."""

class NoTrainerAttemptsError(ResourceLimitException):
    """User has no available trainer attempts."""

# LLM exceptions
class LLMException(BackendException):
    """Base for LLM-related errors."""

class LLMError(LLMException):
    """Single LLM provider failed."""

class AllLLMProvidersFailedError(LLMException):
    """All LLM providers failed."""
```

**App usage:**
```python
# apps/*/backend/src/app/exceptions.py
from core.exceptions import (
    BackendException,
    UserNotFoundException,
    FriendAlreadyExistsException,
    NoAvailableReadingsError,
    # ... etc
)

# App-specific exceptions only
class TarotSpecificError(BackendException):
    """Tarot-specific error."""
```

### Pros
- **Eliminates ~240 lines**
- Single exception hierarchy
- Consistent error handling across apps
- No more duplicate `UserNotFoundException`

### Cons
- Apps may have truly app-specific exceptions that don't belong in core
- Existing imports need updating
- Error messages may need app-specific customization

### Risk Level: 🟢 LOW
- Exception classes are simple
- No runtime logic changes
- Easy to test

---

## 8. Frontend Providers (React/Vue)

### Current State
- **Files:** `providers/AppInitProvider.tsx`, `app/providers.tsx`
- **Location:** `apps/{template-react,tarot}/frontend/`
- **Similarity:** ~95% identical

### What They Contain
```
AppInitProvider.tsx (~366 lines)
├── /process_start API call on app launch
├── PostHog user identification
├── Start param parsing (i_, r_, m_, p_ prefixes)
├── User data caching in React Query
├── Mode-based routing
├── Subscription prefetching
└── Session persistence

providers.tsx (~229 lines)
├── Mock data injection
├── ErrorBoundary with fallback
├── SDKProvider (Telegram SDK)
├── QueryClientProvider with smart retry
├── ThemeProvider
├── Sentry initialization
├── PostHog initialization
└── Eruda debug console
```

### Extraction Plan

**Move to core frontend:**
```typescript
// core/frontend/src/providers/AppInitProvider.tsx
export interface AppInitProviderProps {
  children: React.ReactNode;
  processStartFn: (params: StartParamsRequest) => Promise<StartResult>;
  getUserQueryKey: () => QueryKey;
  modeRoutes?: Record<string, string>;
  router: { push: (path: string) => void };
}

export function AppInitProvider(props: AppInitProviderProps) {
  // Core implementation
}
```

**App usage:**
```typescript
// apps/template/frontend/providers/AppInitProvider.tsx
import { AppInitProvider as CoreProvider } from '@tma-platform/core-react';
import { processStartProcessStartPost } from '@/src/gen/client';

export function AppInitProvider({ children }) {
  return (
    <CoreProvider
      processStartFn={processStartProcessStartPost}
      modeRoutes={{ draw: '/', settings: '/profile' }}
    >
      {children}
    </CoreProvider>
  );
}
```

### Pros
- **Eliminates ~1,200 lines** of provider code
- TMA initialization logic is identical
- PostHog/Sentry setup standardized
- Error boundaries consistent

### Cons
- React Query key generation tied to generated client
- Import paths vary per app
- Mode routes are app-specific

### Risk Level: 🟡 MEDIUM
- Frontend initialization is critical path
- TypeScript generics may be complex
- Testing requires E2E verification

---

## 9. Frontend Hooks

### Current State
- **Files:** 6 hooks (~40-80 lines each)
- **Location:** `apps/*/frontend/hooks/`
- **Similarity:** ~90% identical patterns

### Hooks to Extract
| Hook | Lines | Description |
|------|-------|-------------|
| `useAuth.ts` | ~65 | Auth state from AppInit context |
| `useLogout.ts` | ~40 | Session cleanup, cache clear |
| `useEmailAuth.ts` | ~80 | Email login/signup flow |
| `usePasswordReset.ts` | ~60 | Password reset flow |
| `useTelegramLink.ts` | ~50 | Telegram account linking |
| `useTelegramDeeplinkLogin.ts` | ~40 | Deeplink auth flow |

### Extraction Plan

**Move to core frontend (using hook factories):**
```typescript
// core/frontend/src/hooks/createUseAuth.ts
export function createUseAuth(useAppInit: () => AppInitContextValue) {
  return function useAuth() {
    const { user, isLoading, isReady, error, reinitialize } = useAppInit();

    const isGuest = !user || user.user_type === 'GUEST';
    const isAuthenticated = user?.user_type === 'REGISTERED';
    // ... rest of logic

    return { user, isAuthenticated, isGuest, ... };
  };
}
```

**App usage:**
```typescript
// apps/template/frontend/hooks/useAuth.ts
import { createUseAuth } from '@tma-platform/core-react/hooks';
import { useAppInit } from '@/providers';

export const useAuth = createUseAuth(useAppInit);
```

### Pros
- **Eliminates ~600 lines**
- Auth logic guaranteed consistent
- Hook factories allow dependency injection
- TypeScript types shared

### Cons
- Factory pattern adds indirection
- Import chains become deeper
- Testing requires mock providers

### Risk Level: 🟢 LOW
- Hooks are stateless logic
- Easy to unit test
- No side effects beyond existing dependencies

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. **Exceptions** → Merge into core (lowest risk)
2. **Statistics Service** → Extract to core (read-only)
3. **Demo Router** → Extract to core (templates only)

### Phase 2: Authentication (Week 2)
4. **`webhook/auth.py`** → Use core TelegramAuthenticator + extract session
5. **`webhook/routers/base.py`** → Extract with dependency overrides

### Phase 3: Bot & Workers (Week 3)
6. **Worker Jobs** → Extract common jobs to core
7. **Admin Bot Handlers** → Extract to core with keyboard injection

### Phase 4: Frontend (Week 4)
8. **AppInitProvider** → Extract to core-react
9. **Auth Hooks** → Extract hook factories

---

## Migration Checklist

### For Each Extraction:
- [ ] Read all app implementations side-by-side
- [ ] Identify ALL differences (even minor)
- [ ] Design core API with extension points
- [ ] Implement in core with comprehensive tests
- [ ] Migrate template-vue first (lowest traffic)
- [ ] Migrate template-react
- [ ] Migrate tarot
- [ ] Migrate maxstat (most customizations)
- [ ] Remove duplicated code from apps
- [ ] Update CLAUDE.md if patterns changed

### After All Extractions:
- [ ] Run full test suite on all apps
- [ ] Deploy to staging and verify
- [ ] Update template documentation
- [ ] Create "new app" checklist

---

## Files That Should STAY in Apps

These are correctly app-specific and should NOT be moved:

| File | Reason |
|------|--------|
| `config.py` | App-specific settings, feature flags, cookie names |
| `domain/products.py` | Product catalog is unique per app |
| `services/requests.py` | Service composition varies by app |
| `webhook/routers/admin.py` | Different admin API endpoints |
| `services/base.py` | Minor differences in bot dependency handling |
| `tgbot/handlers/start.py` | App-specific welcome flow |
| `tgbot/keyboards/` | App-specific keyboard layouts |
| App-specific routers | `tarot.py`, `trainer.py`, `chat.py`, etc. |
| App-specific services | `llm.py`, `readings.py`, `trainer.py`, etc. |

---

## Appendix: File Size Comparison

### Backend Files (All Apps)

| File | tarot | template-react | template-vue | maxstat |
|------|------:|---------------:|-------------:|--------:|
| `webhook/auth.py` | 19K | 19K | 19K | 19K |
| `tgbot/handlers/admin.py` | 39K | 40K | 40K | 39K |
| `webhook/routers/demo.py` | 18K | 18K | 18K | — |
| `webhook/routers/base.py` | 2.1K | 2.1K | 2.1K | 2.4K |
| `services/statistics.py` | 6.6K | 6.6K | 6.6K | 6.6K |
| `worker/jobs.py` | 13K | 10K | 10K | 10K |
| `exceptions.py` | 1.4K | 1.3K | 1.3K | 1.3K |

### Potential Savings
- **Current total:** ~400KB of duplicated code
- **After extraction:** ~50KB of thin wrappers
- **Net reduction:** ~350KB (~87.5%)
