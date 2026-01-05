# Task Context

**Last Updated:** 2026-01-05
**Current Phase:** 0 (not started)
**Status:** Not Started
**Difficulty:** HARD

## Key Decisions

1. **core/frontend/ is ACTIVE** - Phase 00 exploration discovered template-vue uses it (20+ imports). Removed from deletion list.
2. **Dependency Override Pattern** - Per CLAUDE.md, no factory functions for routers. Using `app.dependency_overrides`.
3. **KeyboardFactory Protocol** - Admin handlers use protocol injection for app-specific keyboards.
4. **Hook Factories** - React auth hooks use `createUseAuth(useAppInit)` pattern for dependency injection.
5. **All 4 apps updated simultaneously** - No sequential migration.

## Files Modified

None yet.

## Phase Summary

| Phase | Focus | Lines Saved | Status |
|-------|-------|-------------|--------|
| 00 | Foundation (BackendException) | ~20 added | Not Started |
| 01 | Exceptions Consolidation | ~225 | Not Started |
| 02 | Auth & Base Router | ~1,000 | Not Started |
| 03 | Admin Bot Handlers | ~2,894 | Not Started |
| 04 | Workers & Statistics | ~847 | Not Started |
| 05 | Frontend React | ~355 | Not Started |

**Total Estimated Savings:** ~5,300 lines

**Not extracted:** Demo router stays in template apps (template-specific boilerplate)

## Critical File References

**Core (to modify/create):**
- `core/backend/src/core/exceptions.py` - Add BackendException, shared exceptions
- `core/backend/src/core/infrastructure/fastapi/routers/base.py` - CREATE
- `core/backend/src/core/infrastructure/telegram/handlers/admin/` - CREATE (6 files)
- `core/backend/src/core/infrastructure/arq/jobs/broadcast.py` - CREATE
- `core/backend/src/core/services/statistics.py` - CREATE
- `core/frontend-react/src/providers/` - CREATE factory
- `core/frontend-react/src/hooks/auth/` - CREATE factories

**Apps (to modify):**
- `apps/*/backend/src/app/exceptions.py` - Import from core
- `apps/*/backend/src/app/webhook/app.py` - Use core routers
- `apps/*/backend/src/app/webhook/auth.py` - Reduce to ~150 lines
- `apps/*/backend/src/app/tgbot/handlers/admin.py` - Reduce to ~30 lines
- `apps/*/backend/src/app/worker/jobs.py` - Import from core
- `apps/*/backend/src/app/services/requests.py` - Import StatisticsService from core

## Next Steps

1. Begin Phase 00: Add BackendException to core/exceptions.py
2. Run `make test APP=tarot && make lint APP=tarot` to verify no breaks

## Blockers

None identified.

## Testing Commands

```bash
# After each phase
make test APP=tarot && make lint APP=tarot
make test APP=template-react && make lint APP=template-react
make test APP=template-vue && make lint APP=template-vue
make test APP=maxstat && make lint APP=maxstat

# Frontend (Phase 06)
cd apps/template-react/frontend && pnpm typecheck && pnpm build
```
