# Task: DRY Core Extraction

**Created:** 2026-01-05
**Status:** Planning
**Apps:** tarot, template-react, template-vue, maxstat (all 4)
**Difficulty:** HARD

## Overview

Extract ~16,500 lines of duplicated code across 4 apps into the `core/` package. This consolidates backend infrastructure (auth, routers, handlers, workers, statistics, exceptions) and frontend React providers/hooks. All apps are updated simultaneously.

## Design Decisions

### Extraction Strategy

| Pattern | Usage |
|---------|-------|
| **Dependency Override** | Routers use `app.dependency_overrides[get_services]` - no factory functions |
| **Protocol-based Typing** | StatisticsService uses `StatisticsRepoProtocol` for repo access |
| **Keyboard Injection** | Admin handlers accept `KeyboardFactory` protocol for app-specific keyboards |
| **Hook Factories** | React hooks use `createUseAuth(useAppInit)` pattern |

### Files to Extract

| Category | Source (per app) | Destination (core) | Lines Saved |
|----------|------------------|---------------------|-------------|
| Exceptions | `app/exceptions.py` | `core/exceptions.py` | ~240 |
| Auth/Session | `webhook/auth.py` | Use existing `core/services/sessions.py` | ~2,400 |
| Base Router | `webhook/routers/base.py` | `core/infrastructure/fastapi/routers/base.py` | ~280 |
| Admin Handlers | `tgbot/handlers/admin.py` | `core/infrastructure/telegram/handlers/admin/` | ~6,400 |
| Worker Jobs | `worker/jobs.py` | `core/infrastructure/arq/jobs/` | ~1,200 |
| Statistics | `services/statistics.py` | `core/services/statistics.py` | ~660 |
| React Providers | `providers/AppInitProvider.tsx` | `core/frontend-react/src/providers/` | ~1,200 |

### What Stays in Apps

- App-specific exceptions (e.g., `TarotSpecificError`)
- App-specific bot handlers (e.g., `/keygo_prediction`)
- Keyboard implementations (e.g., `command_keyboard()`)
- Notification templates
- App-specific worker jobs

## Required Skills

- [x] Backend patterns (dependency injection, protocols)
- [x] FastAPI routers (dependency overrides)
- [x] Aiogram handlers (FSM, keyboard injection)
- [x] ARQ workers (job definitions)
- [x] React hooks (hook factories)
- [x] Testing (pytest, pnpm typecheck)

## Phases

| # | Focus | Description |
|---|-------|-------------|
| 00 | Foundation | Add BackendException to core |
| 01 | Exceptions | Consolidate exceptions to core, update app imports |
| 02 | Auth & Base Router | Use core SessionService, extract base router |
| 03 | Admin Handlers | Extract with KeyboardFactory protocol injection |
| 04 | Workers & Statistics | Extract jobs and StatisticsService with protocols |
| 05 | Frontend React | Extract AppInitProvider and auth hooks to core-react |

**Not extracted:** Demo router stays in template apps (template-specific boilerplate)

## Success Criteria

- [ ] All 4 apps pass `make test` and `make lint`
- [ ] React apps pass `pnpm typecheck` and `pnpm build`
- [ ] ~8,000+ backend lines removed from apps
- [ ] ~1,500+ frontend lines removed from React apps
- [ ] Dead `core/frontend/` package deleted
- [ ] No regression in functionality

## Testing Strategy

After each phase:
```bash
make test APP=tarot && make lint APP=tarot
make test APP=template-react && make lint APP=template-react
make test APP=template-vue && make lint APP=template-vue
make test APP=maxstat && make lint APP=maxstat
```

Frontend (Phase 06):
```bash
cd apps/template-react/frontend && pnpm typecheck && pnpm build
```

## References

- Plan: `/Users/anton/.claude/plans/steady-snacking-cocke.md`
- DRY Guide: `/Users/anton/tarot/docs/dry-extraction-guide.md`
