# Critical Rules - MUST FOLLOW

These rules apply to ALL work in this monorepo. READ CAREFULLY.

## ⚠️ Core vs App Split (MOST CRITICAL)

**BEFORE writing ANY code, decide: `core/` or `apps/{app}/`?**

**Decision rule:**
- **"Will 2+ apps need this exact functionality?"**
  - **YES** → `core/` (User, Payment, Balance, Telegram SDK, shared UI)
  - **NO** → `apps/{app}/` (App features, app-specific business logic)
  - **MAYBE** → Start in `apps/{app}/`, move to `core/` when needed

**Common mistakes:**
- ❌ Putting app-specific business logic in `core/` (e.g., `core/services/tarot_reading.py`)
- ❌ Duplicating shared functionality in multiple apps (e.g., user repo in each app)
- ❌ Not checking if functionality already exists in `core/` before implementing

**Always ask yourself first:**
1. Is this specific to ONE app? → `apps/{app}/`
2. Is this reusable across ALL apps? → `core/`
3. Does it involve User/Payment/Balance/Subscription? → Almost always `core/`

**See:** `.claude/shared/monorepo-structure.md` for detailed decision trees.

## File Editing

**CRITICAL:** Whitespace corruption is a common failure mode.

- ✅ Before editing ANY file: Use `Read` tool to verify exact whitespace
- ✅ Preserve EXACT indentation (tabs vs spaces) from original file
- ✅ Match the original file's whitespace character by character
- ❌ NEVER convert tabs to spaces or vice versa
- ❌ NEVER assume indentation style without reading the file first

**Example workflow:**
1. Read the file you want to edit
2. Note the indentation style (tabs or spaces, how many)
3. Make your changes preserving exact indentation
4. Verify the edit preserves original whitespace

## Command Usage

**CRITICAL:** Always use make commands, never run tools directly.

- ✅ ALWAYS use `make` commands when available
- ❌ NEVER run docker, alembic, pytest directly
- ✅ Check `Makefile` if unsure what commands exist

**Common commands (ALWAYS with APP parameter):**
- `make test APP=<name>` - Run all tests (parallel)
- `make test-file file=<path> APP=<name>` - Run specific test file
- `make migration msg="description" APP=<name>` - Create migration after model changes
- `make upgrade APP=<name>` - Apply migrations
- `make schema APP=<name>` - Generate OpenAPI schema for frontend
- `make lint APP=<name>` - Run all quality checks
- `make status APP=<name>` - Check container status
- `make logs APP=<name>` - View all logs
- `make shell-webhook APP=<name>` - Backend shell
- `make shell-bot APP=<name>` - Bot shell

## Hot Reload

**All services have hot reload configured.**

- ✅ Code changes take effect immediately
- ❌ NEVER restart containers for code changes
- ⚠️ Only restart for: `.env` changes, Docker config changes, new dependencies

## Working Directory

- Project root: `/path/to/project/`
- All `make` commands run from project root
- **Monorepo structure:** `core/` (reusable) vs `apps/<app-name>/` (app-specific)
- **Apps:** tarot, template, template-react

## App URLs

**CRITICAL:** All apps run behind a reverse proxy. NEVER use localhost URLs!

**Local development URLs:**
- Base domain: `https://local.gramkit.dev`
- Frontend pattern: `https://local.gramkit.dev/{app-name}`
- API pattern: `https://local.gramkit.dev/api/{app-name}`
- API docs pattern: `https://local.gramkit.dev/api/{app-name}/docs`

**Examples:**
- Tarot frontend: `https://local.gramkit.dev/tarot`
- Tarot API: `https://local.gramkit.dev/api/tarot`
- Tarot API docs: `https://local.gramkit.dev/api/tarot/docs`
- Template API docs: `https://local.gramkit.dev/api/template/docs`
- Template-React API docs: `https://local.gramkit.dev/api/template-react/docs`

**NEVER use these (will fail):**
- ❌ `http://localhost:3779`
- ❌ `http://localhost:8002`
- ❌ `http://localhost:8003`

## APP Parameter

**CRITICAL:** ALL make commands REQUIRE explicit `APP=<name>` parameter.

- ❌ NEVER omit APP parameter
- ❌ NEVER assume default app
- ✅ ALWAYS specify: `make <command> APP=<app-name>`
- ✅ Examples:
  - `make test APP=tarot`
  - `make up APP=template-react`
  - `make schema APP=template`

## Database Migrations

**CRITICAL:** Never skip migrations.

- After model changes: `make migration msg="description"`
- Then: `make upgrade`
- Test after migration: `make test`
- NEVER skip migrations even if "seems simple"

## API Schema Sync

**CRITICAL:** Keep frontend types in sync with backend.

- After backend API changes: `make schema APP=<app-name>`
- This regenerates schema files:
  - Vue apps: `apps/<app>/frontend/src/schema/api.d.ts`
  - React apps: `apps/<app>/frontend/types/api.d.ts`
- Fix any type errors in frontend before proceeding
- Never edit generated schema files manually (they're auto-generated)

**Examples:**
```bash
make schema APP=tarot           # Tarot (Vue.js)
make schema APP=template        # Template (Vue.js)
make schema APP=template-react  # Template-React (Next.js)
```

## Transaction Management

**Pattern:** 1 Request → 1 Session → 1 Transaction → Commit/Rollback

- Repository layer: Use `flush()` NOT `commit()`
- Transactions managed at interface layer (webhook/bot/worker)
- Pessimistic locking: Use `get_by_id_with_lock()` for balance/payment operations

## Testing

- Run tests after significant changes: `make test`
- Fix failing tests before marking task complete
- Write tests following project patterns (see testing docs)

## Code Quality

- Run linting before completion: `make lint`
- Fix lint issues before marking task complete
- Backend: Uses ruff + import-linter
- Frontend: Uses eslint + typescript

## Frontend UI Components

**CRITICAL:** ALWAYS use shadcn components. NEVER write raw HTML for UI elements.

- ✅ Use `<Button>`, `<Card>`, `<Input>`, `<Dialog>`, etc. from shadcn
- ✅ Check existing components in `components/ui/` before creating anything
- ❌ NEVER use raw `<button>`, `<input>`, `<div class="card">` etc.
- ❌ NEVER write custom CSS for standard UI patterns (shadcn handles it)

**Vue:** Import from `@/components/ui/` (shadcn-vue)
**React:** Import from `@/components/ui/` (shadcn/ui)

## Git Commits

- ❌ NEVER use `--no-verify` (pre-commit hooks must run)
- ✅ Fix any pre-commit hook failures properly
- ✅ Use conventional commit format: `feat(scope): description`

## Reporting Back

When returning to main thread:

- ✅ Return CONCISE summaries, not full code
- ✅ List files changed with paths:line_numbers
- ✅ Report test results and any issues
- ❌ Don't dump entire code listings unless specifically requested
