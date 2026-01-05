# Architecture - DRY Core Extraction

## Overview

All file operations for extracting ~11,000+ lines of duplicated code from 4 apps into `core/`.

**Apps:** tarot, template-react, template-vue, maxstat

---

## Phase 00: Foundation & Cleanup

### DELETE
| Path | Reason |
|------|--------|
| ~~`core/frontend/`~~ | **KEEP** - Active usage by template-vue (20+ imports from @core) |

### MODIFY
| Path | Change |
|------|--------|
| `core/backend/src/core/exceptions.py` | Add `BackendException` base class |

**Note:** Phase 00 exploration discovered `core/frontend/` is actively used by template-vue frontend via Vite alias. Do NOT delete.

---

## Phase 01: Exceptions Consolidation

### MODIFY (Core)
| Path | Change |
|------|--------|
| `core/backend/src/core/exceptions.py` | Add: `FriendAlreadyExistsException`, `LLMError`, `AllLLMProvidersFailedError` |

### MODIFY (Apps - All 4)
| Path | Change |
|------|--------|
| `apps/template/backend/src/app/exceptions.py` | Remove duplicates, import from core |
| `apps/template-react/backend/src/app/exceptions.py` | Same |
| `apps/template-vue/backend/src/app/exceptions.py` | Same |
| `apps/template-react/backend/src/app/exceptions.py` | Same |

**Keep App-Specific:** `NoAvailableReadingsError`, `ReadingNotFoundError`, `NoChatMessagesError`, `NoTrainerAttemptsError`, `DailyReadingError`, `QuestionReadingError`

---

## Phase 02: Auth & Base Router

### CREATE (Core)
| Path | Description |
|------|-------------|
| `core/backend/src/core/infrastructure/fastapi/routers/base.py` | /friends, /add_friend, /create_invite, /process_start |

### DELETE (Apps - All 4)
| Path |
|------|
| `apps/template/backend/src/app/webhook/routers/base.py` |
| `apps/template-react/backend/src/app/webhook/routers/base.py` |
| `apps/template-vue/backend/src/app/webhook/routers/base.py` |
| `apps/template-react/backend/src/app/webhook/routers/base.py` |

### MODIFY (Apps - All 4)
| Path | Change |
|------|--------|
| `apps/*/backend/src/app/webhook/app.py` | Import base router from core, add dependency overrides |
| `apps/*/backend/src/app/webhook/auth.py` | Remove duplicated TelegramAuthenticator/session code, use core services |
| `apps/template-react/backend/src/app/webhook/app.py` | Also add process_start_hook for cookie logic |

**Auth.py After Refactor (~150 lines):**
- Keep: `get_user()` dependency, `get_mock_guest_user()`
- Remove: TelegramUser class, TelegramAuthenticator class, session functions (use core)

---

## Phase 03: Admin Bot Handlers

### CREATE (Core)
| Path | Description |
|------|-------------|
| `core/backend/src/core/infrastructure/telegram/handlers/admin/__init__.py` | Module exports |
| `core/backend/src/core/infrastructure/telegram/handlers/admin/states.py` | BroadcastStates, PromoStates FSM |
| `core/backend/src/core/infrastructure/telegram/handlers/admin/protocol.py` | KeyboardFactory protocol |
| `core/backend/src/core/infrastructure/telegram/handlers/admin/base.py` | /admin, /stats, /giftsub handlers |
| `core/backend/src/core/infrastructure/telegram/handlers/admin/broadcast.py` | /broadcast FSM handlers |
| `core/backend/src/core/infrastructure/telegram/handlers/admin/promo.py` | /promo handlers |

### MODIFY (Apps - All 4)
| Path | Change |
|------|--------|
| `apps/*/backend/src/app/tgbot/handlers/admin.py` | Replace with thin wrapper (~30 lines) implementing KeyboardFactory |

**KeyboardFactory Protocol:**
```python
class KeyboardFactory(Protocol):
    def command_keyboard(self) -> InlineKeyboardMarkup: ...
    def daily_keyboard(self) -> InlineKeyboardMarkup: ...
    def keygo_keyboard(self) -> InlineKeyboardMarkup | None: ...
    def keygo_image_path(self) -> str | None: ...
```

---

## Phase 04: Workers & Statistics

### CREATE (Core)
| Path | Description |
|------|-------------|
| `core/backend/src/core/infrastructure/arq/jobs/broadcast.py` | admin_broadcast_job, user_broadcast_job |
| `core/backend/src/core/infrastructure/arq/jobs/statistics.py` | daily_admin_statistics_job |
| `core/backend/src/core/infrastructure/arq/jobs/demo.py` | send_delayed_notification |
| `core/backend/src/core/services/statistics.py` | StatisticsService with StatisticsRepoProtocol |

### DELETE (Apps - All 4)
| Path |
|------|
| `apps/*/backend/src/app/services/statistics.py` |

### MODIFY (Apps - All 4)
| Path | Change |
|------|--------|
| `apps/*/backend/src/app/worker/jobs.py` | Remove common jobs, import from core; keep app-specific |
| `apps/*/backend/src/app/services/requests.py` | Import StatisticsService from core |

**App-Specific Jobs to Keep:** `morning_notification_job`, `evening_notification_job`, `topup_daily_chat_messages_job`

---

## Phase 05: Frontend React

### CREATE (Core)
| Path | Description |
|------|-------------|
| `core/frontend-react/src/providers/AppInitProvider.tsx` | Provider factory with config |
| `core/frontend-react/src/providers/index.ts` | Exports |
| `core/frontend-react/src/hooks/auth/createUseAuth.ts` | Hook factory |
| `core/frontend-react/src/hooks/auth/createUseLogout.ts` | Hook factory |

### MODIFY (Apps - React only)
| Path | Change |
|------|--------|
| `apps/template-react/frontend/providers/AppInitProvider.tsx` | Use core provider factory |
| `apps/template-react/frontend/hooks/useAuth.ts` | Use `createUseAuth(useAppInit)` |
| `apps/template-react/frontend/hooks/useLogout.ts` | Use `createUseLogout(...)` |

**Hook Factory Pattern:**
```typescript
export const useAuth = createUseAuth(useAppInit);
```

---

## Naming Conventions

| Entity | Pattern |
|--------|---------|
| Core Exception | `core.exceptions.{Name}Exception` |
| Core Router | `core.infrastructure.fastapi.routers.{name}` |
| Core Handler | `core.infrastructure.telegram.handlers.admin.{name}` |
| Core Job | `core.infrastructure.arq.jobs.{name}` |
| Core Service | `core.services.{name}` |
| Protocol | `{Name}Protocol` or `{Name}Factory` |

---

## Phase Dependencies

```
Phase 00 → Phase 01 → Phase 02 (can run after 01)
                   → Phase 03 (depends on 01)
                   → Phase 04 (depends on 01)
                   → Phase 05 (depends on 01, 04)
                   → Phase 06 (independent)
```

---

## Critical Constraints (from CLAUDE.md)

1. **NO factory functions for routers** - use `app.dependency_overrides`
2. **NO `if TYPE_CHECKING:`** - direct imports only
3. **Use `flush()` not `commit()`** in repositories
4. **Use `datetime.now(UTC)`** not `datetime.now()`

---

## Line Count Savings

| Phase | Savings |
|-------|---------|
| 00 Foundation | ~20 lines added |
| 01 Exceptions | ~225 lines |
| 02 Auth & Base | ~1,000 lines |
| 03 Admin Handlers | ~2,894 lines |
| 04 Workers & Stats | ~847 lines |
| 05 Frontend React | ~355 lines |
| **Total Backend** | **~4,970+ lines** |
| **Total Frontend** | **~355+ lines** |
