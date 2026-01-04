# CLAUDE.md - Project Guide

## ⛔ MANDATORY GATE - READ BEFORE ANY ACTION

**STOP. Before writing ANY code, you MUST complete these steps IN ORDER:**

### Step 1: Determine if you should delegate
```
Is this task MORE than a single-line fix or running a command?
  ↓ YES
Does it involve backend code, frontend code, or both?
  ↓ YES
USE developer-agent VIA Task TOOL. DO NOT write the code yourself.
```

**You MUST use `developer-agent`** (Task tool with subagent_type) for:
- ANY backend code (routers, services, repos, models)
- ANY frontend code (components, hooks, pages)
- ANY multi-file changes
- ANY feature implementation

**You may handle directly ONLY:**
- Running make/pnpm commands
- Single-line typo/config fixes
- Answering questions (no code)

### Step 2: If you ARE writing code (rare), read the pattern doc FIRST
```
Backend? → Read .claude/shared/backend-patterns.md FIRST
Vue?     → Read .claude/shared/vue-frontend.md FIRST
React?   → Read .claude/shared/react-frontend.md FIRST
Tests?   → Read .claude/shared/testing-patterns.md FIRST
```

**Failure to read = wrong patterns = broken code. No exceptions.**

---

## Project Overview

Monorepo: `core/` (shared) + `apps/` (tarot, template-vue, template-react)

**Stack:**
- Backend: Python 3.14 + FastAPI + SQLAlchemy + Alembic
- Frontend (Vue): Vue.js 3 + TanStack Query + Pinia + shadcn-vue
- Frontend (React): Next.js 15/16 + TanStack Query + Zustand + shadcn/ui
- Database: PostgreSQL + Redis

**Core vs App:** "Will 2+ apps need this?" YES → `core/`, NO → `apps/{app}/`

---

## Commands

**All make commands REQUIRE `APP=<name>`!**

### Docker
```bash
make up APP=tarot           # Start services
make down APP=tarot         # Stop services
make status APP=tarot       # Check status
make logs APP=tarot         # View logs
make shell-webhook APP=tarot  # Backend shell
```

### Backend
```bash
make test APP=tarot         # Run full test suite (parallel)
make test-quick APP=tarot   # Run incremental tests (fast, only changed)
make lint APP=tarot         # Quality checks
make migration msg="..." APP=tarot  # Create migration
make upgrade APP=tarot      # Apply migrations
make schema APP=tarot       # Generate frontend types
```

### Frontend
```bash
cd apps/{app}/frontend
pnpm dev          # Development server
pnpm build        # Production build
pnpm typecheck    # Type checking
pnpm lint         # Linting
```

### App URLs (Local)

| App | Frontend | API Docs |
|-----|----------|----------|
| tarot | `https://local.gramkit.dev/tarot` | `https://local.gramkit.dev/api/tarot/docs` |
| template-vue | `https://local.gramkit.dev/template-vue` | `https://local.gramkit.dev/api/template-vue/docs` |
| template-react | `https://local.gramkit.dev/template-react` | `https://local.gramkit.dev/api/template-react/docs` |

**NEVER use `http://localhost:PORT`** - always use the domain above.

---

## Rules

### General
- Do what was asked; nothing more, nothing less
- NEVER create files unless necessary
- ALWAYS prefer editing existing files
- Read files before editing (verify whitespace)

### NEVER DO (Quick Reference)

**Python/Backend:**
- ❌ `if TYPE_CHECKING:` → causes import issues, just import directly
- ❌ `datetime.now()` / `datetime.utcnow()` → use `datetime.now(UTC)`
- ❌ `commit()` in repositories → use `flush()`
- ❌ Import `app` in `core/` → core never imports from app
- ❌ Factory functions for routers → use regular routers + dependency overrides
- ❌ Wrapper dependencies → access `services.auth` directly, don't create `get_auth_service()`

**Frontend:**
- ❌ Create new files for tiny changes → edit existing files
- ❌ Add features not requested → do exactly what was asked
- ❌ Edit `gen/` or `schema/` folders → auto-generated, use `make schema`

### After Code Changes
- Model changes → `make migration` + `make upgrade`
- API changes → `make schema`
- Always run `make test` + `make lint`

### Never Do
- Run Docker/Alembic/pytest directly (use make)
- Use naive datetimes (use `datetime.now(UTC)`)
- Skip migrations or tests
- Restart containers for code changes (hot reload works)

---

## Workflow Commands

| Command | Purpose |
|---------|---------|
| `/design [feature]` | Research approaches, compare, output design doc |
| `/create-task [desc]` | Create structured task plan from design |
| `/execute-task [name]` | Execute task phases |
| `/develop [feature]` | Quick full-stack implementation |
