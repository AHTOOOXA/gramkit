# Monorepo Structure

## ⚠️ CRITICAL: Read This First

**BEFORE writing ANY code, you MUST decide:**
- Does this go in `core/` (reusable) or `apps/{app}/` (app-specific)?

**Decision rule:**
- **Will 2+ apps need this exact functionality?**
  - YES → `core/`
  - NO → `apps/{app}/`
  - MAYBE → Start in `apps/{app}/`, move to `core/` when needed

**Common mistakes to avoid:**
- ❌ Putting app-specific business logic in `core/`
- ❌ Duplicating shared functionality in multiple apps
- ❌ Not checking if functionality already exists in `core/`

## Overview

This is a monorepo containing:
- **Core packages:** Reusable infrastructure (backend + frontend)
- **Apps:** Specific applications

**Current apps:**
- `tarot` - AI App feature app (production, Vue.js)
- `template-vue` - Vue.js web app template (reference)
- `template-react` - React/Next.js web app template (reference)

## Directory Layout

```
/path/to/project/
├── core/
│   ├── backend/            # Shared backend infrastructure
│   │   └── src/core/
│   │       ├── infrastructure/database/
│   │       │   ├── models/        # Core models (User, Payment, Balance, etc.)
│   │       │   └── repo/          # Core repositories
│   │       └── services/          # Core services
│   │
│   ├── frontend/           # Shared frontend infrastructure (Vue.js)
│   │   └── src/
│   │       ├── platform/          # Telegram SDK abstraction
│   │       ├── ui/                # Generic components & layouts
│   │       ├── composables/       # Generic composables
│   │       └── api/               # API client
│   │
│   └── frontend-react/     # Shared frontend infrastructure (React)
│       └── src/
│           ├── platform/          # Telegram SDK hooks
│           ├── hooks/             # Generic React hooks
│           ├── utils/             # Utilities
│           └── api/               # API client
│
├── apps/
│   ├── tarot/              # AI App feature app (Vue.js + FastAPI)
│   ├── template-vue/       # Vue.js web app template
│   └── template-react/     # React web app template (Next.js)
│       ├── backend/
│       │   └── src/app/
│       │       ├── webhook/           # FastAPI web API
│       │       ├── tgbot/             # Telegram bot (aiogram)
│       │       ├── worker/            # Background jobs (ARQ)
│       │       ├── services/          # App business logic
│       │       ├── infrastructure/
│       │       │   └── database/
│       │       │       ├── models/    # App-specific models
│       │       │       └── repo/      # App-specific repositories
│       │       ├── migrations/        # Alembic migrations
│       │       ├── scripts/           # Management scripts
│       │       └── tests/             # Test suite
│       │
│       └── frontend/
│           └── src/
│               ├── schema/            # Generated API types (DO NOT EDIT)
│               ├── app/
│               │   ├── store/         # Pinia stores
│               │   ├── presentation/  # UI (screens, components)
│               │   ├── composables/   # Business utilities
│               │   ├── router/        # Routing
│               │   └── i18n/          # Translations
│               └── main.ts
│
├── docs/                   # Documentation
├── .claude/                # Claude Code configuration
│   ├── shared/            # Shared instructions for agents
│   ├── agents/            # Custom agent definitions
│   ├── commands/          # Slash commands
│   └── skills/            # Auto-invoked skills
│
├── Makefile               # Main commands
├── docker-compose*.yml    # Docker configurations
├── .env                   # Environment variables (template)
└── CLAUDE.md             # Main guidance for Claude
```

## Core vs App (CRITICAL DISTINCTION)

### ✅ Core (Reusable Infrastructure)

**Use `core/` when the feature is:**
- Used by 2+ apps
- Generic platform functionality
- Shared business logic (User, Payment, Balance, Subscription)
- Common UI patterns and components
- Platform abstractions

**Backend examples:**
- ✅ `core/backend/src/core/infrastructure/database/repo/user.py` - User repo
- ✅ `core/backend/src/core/services/balance.py` - Balance service
- ✅ `core/backend/src/core/services/payment.py` - Payment processing

**Frontend examples:**
- ✅ `core/frontend/src/platform/telegram.ts` - Telegram SDK wrapper
- ✅ `core/frontend/src/ui/layouts/MainLayout.vue` - Generic layout
- ✅ `core/frontend/src/composables/useFormatter.ts` - Formatting utilities

### ✅ App (App-Specific Code)

**Use `apps/{app}/` when the feature is:**
- Specific to ONE app's business domain
- App-specific models, repos, services
- App-specific UI screens and flows
- App-specific configuration and logic

**Backend examples:**
- ✅ `apps/template/backend/src/app/infrastructure/database/models/reading.py` - Reading model
- ✅ `apps/template/backend/src/app/services/template.py` - App feature service
- ✅ `apps/template/backend/src/app/webhook/template.py` - Tarot API endpoints

**Frontend examples:**
- ✅ `apps/template/frontend/src/app/presentation/screens/ReadingScreen.vue` - Reading UI
- ✅ `apps/template/frontend/src/app/store/reading.ts` - Reading store
- ✅ `apps/template/frontend/src/app/composables/useTarot.ts` - Tarot logic

### ❌ Common Mistakes

**DON'T put app-specific logic in core:**
```python
# ❌ WRONG - Tarot-specific in core
core/backend/src/core/services/tarot_reading.py

# ✅ CORRECT - Tarot-specific in tarot app
apps/template/backend/src/app/services/template.py
```

**DON'T duplicate shared functionality:**
```python
# ❌ WRONG - User repo duplicated in each app
apps/template/backend/src/app/infrastructure/database/repo/user.py
apps/template-vue/backend/src/app/infrastructure/database/repo/user.py

# ✅ CORRECT - User repo in core, used by all apps
core/backend/src/core/infrastructure/database/repo/user.py
```

## Composition Pattern

**Apps compose core packages:**

**Backend example:**
```python
# Core provides CoreRequestsRepo with users, payments, etc.
# App composes and extends:

class RequestsRepo:
    def __init__(self, session):
        self._core = CoreRequestsRepo(session)  # Composition

    @cached_property
    def users(self):
        return self._core.users  # Delegate to core

    @cached_property
    def readings(self):
        return ReadingsRepo(self.session)  # App-specific
```

**Frontend example:**
```typescript
// Core provides @core/api, @core/ui, @core/platform
// App imports and uses:

import apiClient from '@core/api';
import { usePlatform } from '@core/platform';
import { BaseLayout } from '@core/ui/layouts';

// App adds tarot-specific stores, components, screens
```

## Working with Multiple Apps

**Makefile APP Parameter (REQUIRED):**
- **CRITICAL:** APP parameter is REQUIRED for all make commands
- No default - must be explicitly specified
- Format: `make <command> APP=<app-name>`
- Examples:
  - `make up APP=template-react`
  - `make test APP=template`
  - `make schema APP=tarot`
  - `make upgrade APP=tarot`

**Each app has:**
- Own `.env` file (copy from root: `cp .env apps/<app>/.env`)
- Own `Makefile` in `apps/<app>/Makefile`
- Own `docker-compose.local.yml`
- Own ports (to avoid conflicts)

**App Ports:**
- **Tarot:** Frontend 5173, Backend 3779, DB 5432
- **Template Vue:** Frontend 5174, Backend 8002, DB 5434
- **Template-React:** Frontend 5176, Backend 8003, DB 5455

**App directory structure:**
```
apps/<app-name>/
├── frontend/           # Frontend code (Vue or React)
├── backend/            # Backend code (FastAPI)
├── .env                # App-specific environment
├── Makefile            # App-specific commands
└── docker-compose.local.yml  # App Docker config
```

**Determining which app to work on:**
- Check current task/feature context
- Look at file paths: `apps/template/` vs `apps/template-vue/` vs `apps/template-react/`
- **ALWAYS use `APP=<name>` parameter for ALL make commands**
- If unclear from context, ASK the user which app to work on
- NEVER assume which app - be explicit

## Working in the Monorepo

### ⚠️ STEP 1: Determine Where to Add Code (MANDATORY)

**BEFORE writing any code, answer this question:**

**"Will 2+ apps (tarot, template, template-react, or future apps) need this exact functionality?"**

- **YES** → `core/` (examples: User, Payment, Balance, Telegram SDK, generic UI)
- **NO** → `apps/{app}/` (examples: App features, app-specific flows)
- **MAYBE** → Start in `apps/{app}/`, move to `core/` when second app needs it

**Quick checks:**
1. ✅ Is this specific to one app? → `apps/<app-name>/`
   - App features, cards → `apps/template/`
   - Template-specific features → `apps/template-vue/` or `apps/template-react/`
2. ✅ Is this reusable across apps? → `core/`
3. ✅ Does it involve users, payments, balance, subscriptions? → Almost always `core/`
4. ✅ Is it a UI component used by multiple apps? → `core/frontend/` or `core/frontend-react/`
5. ✅ Check if similar functionality already exists in `core/` → Use it, don't duplicate!

### Backend Decision Tree

**New Model:**
- Generic (User, Payment, Balance)? → `core/backend/src/core/infrastructure/database/models/`
- App-specific (Reading, Card)? → `apps/template/backend/src/app/infrastructure/database/models/`

**New Repository:**
- For core model? → `core/backend/src/core/infrastructure/database/repo/`
- For app model? → `apps/template/backend/src/app/infrastructure/database/repo/`
- Add to appropriate aggregator (CoreRequestsRepo or RequestsRepo)

**New Service:**
- Generic business logic? → `core/backend/src/core/services/`
- App business logic? → `apps/template/backend/src/app/services/`
- Add to appropriate aggregator (CoreRequestsService or RequestsService)

**New API Endpoint:**
- Always app-specific → `apps/template/backend/src/app/webhook/`

**New Bot Handler:**
- Always app-specific → `apps/template/backend/src/app/tgbot/handlers/`

**New Worker Job:**
- Always app-specific → `apps/template/backend/src/app/worker/jobs/`

### Frontend Decision Tree

**New Store:**
- Always app-specific → `apps/template/frontend/src/app/store/`

**New Component:**
- Generic reusable UI? → `core/frontend/src/ui/components/`
- App-specific? → `apps/template/frontend/src/app/presentation/components/`

**New Screen:**
- Always app-specific → `apps/template/frontend/src/app/presentation/screens/`

**New Composable:**
- Generic utility (formatting, validation)? → `core/frontend/src/composables/`
- Platform abstraction? → `core/frontend/src/platform/`
- App-specific business logic? → `apps/template/frontend/src/app/composables/`

## Commands and Configuration

**All make commands run from project root:** `/path/to/project/`

**Docker configuration:**
- `docker-compose.yml` - Local development (hot reload)
- `docker-compose.dev.yml` - Dev environment
- `docker-compose.prod.yml` - Production

**Environment files:**
- Each app needs `.env` file
- Copy from `.env` template: `cp .env apps/template/.env`

## Key Principles

1. **Core is reusable, app is specific**
2. **Apps compose core, don't modify core for app needs**
3. **Use aggregator pattern for repositories and services**
4. **All commands from project root via Makefile**
5. **Hot reload for all services, no restart needed**

---

<!-- TODO: Consider adding from deleted docs/guides/WRITING_NEW_CODE_GUIDE.md:

## 5-Second Decision Framework (Visual Flowchart)

```
Does core already provide this?
├─ YES → Use it (don't reimplement)
│
└─ NO → Is this domain-specific?
    ├─ YES → Write in app
    │
    └─ NO → Is it infrastructure/framework?
        ├─ YES → Might go to core (add TODO, start in app)
        │
        └─ UNSURE → Default to app
            Add TODO: "Consider extracting to core when second app needs this"
```

## "Default to App" Principle

**Why start in app?**
- ✅ Faster development (no abstraction overhead)
- ✅ No premature abstraction
- ✅ Easy to extract later when proven reusable
- ✅ Clear ownership

**Move to core only when:**
- Second app needs identical functionality
- Third app will definitely need it
- It's pure infrastructure with zero domain logic

## TODO Pattern for Uncertain Cases

```python
class MyFeatureService(BaseService):
    """
    My feature logic.

    TODO: Consider extracting to core when:
    - Second app needs similar functionality
    - Pattern becomes clear
    - Can abstract away app-specific details
    """
    pass
```

-->
