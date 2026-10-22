# CLAUDE.md — Project Guide

Monorepo: `core/` (shared platform) + `apps/` (per-product). This file is the **monorepo-wide** guide: its rules, conventions and `make` workflow apply to *every* app. Layer conventions live in `.claude/rules/` (auto-loaded when you read a file of that layer). If an app grows its own quirks, give it an `apps/<app>/CLAUDE.md` (auto-loaded when you work in that subtree).

---

## How to work here

**Default: do the work in-context.** Read the relevant files, implement, test. Routine changes don't need a sub-agent: delegating adds latency and loses context.

**Delegate (Agent tool) when it actually helps:**
- **Parallelism** — several independent slices that can run at once (e.g. two unrelated features, or fan-out search across many files). Use `general-purpose` for a self-contained implementation slice (ask for a short summary back: files changed, tests run), `Explore` for broad read-only search, `Plan` for a design pass.
- **Isolation** — a noisy exploration whose file dumps you don't want in the main thread; keep the conclusion, drop the dump.
- **Scale** — a migration/audit/sweep too big for one pass. Consider the `Workflow` tool for deterministic multi-agent fan-out.

**Big UI work goes in vertical slices, not layers.** The first deliverable is one screen or flow finished end to end, something a person can open and judge. Don't start with "foundations for every screen".

**Prefer built-ins over hand-rolled flows:** `/code-review` (`--fix` applies), `/security-review`, `/deep-research`, the `qa` agent / `/verify` to confirm a UI change in the browser.

**Reporting back:** after a UI change, say **where to look** (URL/route), **what changed** and **what to check**.

**Layer rules** (`.claude/rules/`, auto-loaded by path, readable any time): `backend`, `testing`, `vue`, `react`, `frontend-api`, `errors`, `packages`, `analytics`, `prod-scripts`, `seen-features`.

---

## Stack

- **Backend:** Python 3.14 + FastAPI + SQLAlchemy + Alembic (managed with `uv`)
- **Frontend (Vue):** Vue 3 + TanStack Query + Pinia + shadcn-vue (`reka-ui`), Vite, pnpm
- **Frontend (React):** Next.js 16 + React 19 + TanStack Query + shadcn/ui
- **Data:** PostgreSQL + Redis
- **Core vs app:** check whether `core/` already provides it; if not, **default to the app**. Promote code to `core/` only when a second app needs the identical thing (leave a `TODO: extract to core when a second app needs this` breadcrumb meanwhile). `core/` never imports from `app`.

### Apps

| App | Stack | Notes |
|-----|-------|-------|
| `template-vue` | Vue (Vite) | Template for new Vue apps — Telegram Mini App + web |
| `template-react` | React / Next | Template for new React apps — Telegram Mini App + web |

New app: copy a template (`docs/guides/NEW_APP_FROM_TEMPLATE.md`).

### CI & release
- **CI:** `test-backend.yml` runs core's tests (without any app installed), the template backends' tests, import-linter, ruff and pyright. `test-frontend.yml` lints, typechecks and builds the template frontends. Frontend CI doesn't watch `core/frontend/**`, so after touching it run template-vue's `pnpm typecheck && pnpm lint` yourself. Core CI runs **without** the `app` package, so a `patch("app…")` or an `app` import in a core test passes locally and fails there.
- **Per-app CI:** name app-only workflows `<app>-*.yml` and prefix their secrets and variables with the app name; no hardcoded values.
- **Release (optional):** `make release-dev APP=<app> BUMP=patch` bumps the version, syncs `uv.lock`, commits and pushes `dev`; `make release-main APP=<app>` merges `origin/dev` into `main` in a temporary worktree, tags and pushes. Wire your deploy (Dokploy, Coolify, a GitHub Action…) to those pushes. `GET /health` returns the running `version`, so a rollout is one request to check.
- **Branches & PRs:** feature branches come off `dev`, PRs go into `dev`. Conventional commits: `feat(scope): …`. Push or open a PR only when asked.

---

## Commands

**All `make` commands REQUIRE `APP=<name>`.** Run from the repo root. Never run docker/alembic/pytest directly — use these targets.

### Docker / dev
```bash
make up APP=template-vue            # Start services + frontend dev server (hot reload). Never returns (tails the log) — run in background
make restart-frontend APP=template-vue / make logs-frontend APP=template-vue   # the dev server alone
make up-shared                      # shared nginx + network (rerun if your Docker VM restarted)
make down APP=template-vue
make status APP=template-vue
make logs APP=template-vue
make shell-webhook APP=template-vue # Backend shell
```
Hot reload covers code changes. Rerun `make up` (it rebuilds) only after `.env`, Docker config or dependency changes.

### Backend
```bash
make test APP=template-vue          # Full suite (parallel)
make test-quick APP=template-vue    # Incremental (changed only)
make test-file file=src/app/tests/... APP=template-vue   # One file (instead of running pytest yourself)
make test-snapshots APP=template-vue / make test-snapshots-update APP=template-vue
make lint APP=template-vue          # ruff --fix + format + import-linter (rewrites files)
make typecheck APP=template-vue     # pyright
make migration msg="..." APP=template-vue   # Create migration
make upgrade APP=template-vue       # Apply migrations
make downgrade APP=template-vue     # Roll back one — before switching to a branch that lacks a migration you applied
make backup-db APP=template-vue / make restore-db file=<dump> APP=template-vue   # local dump / install a dump (wipes the local DB)
make schema APP=template-vue        # Regenerate frontend API types
make script name=<name> APP=template-vue    # Run a backend script locally
make script-list APP=template-vue           # List available scripts
```

### Frontend
```bash
cd apps/{app}/frontend
pnpm dev          # dev server with HMR (Vite for Vue apps, next dev for React apps)
pnpm build
pnpm typecheck
pnpm lint
```

### Local DB (psql)
Each app has its own Postgres container; **names and ports vary**, so check the app's `docker-compose.local.yml`. template-vue runs `template-vue-pg` on port `5454`; template-react runs `template-react-db` on the standard `5432` inside the container (`5455` on the host).
```bash
docker exec template-vue-pg psql -U postgres -d template -h /run/postgresql -p 5454 -c "SQL"   # DB name = DB__NAME in apps/template-vue/.env
```

### App URLs (local)
Open the dev server directly on localhost. Vue apps run **Vite** (fixed port, base path `/<app>/`, keep the trailing slash); React apps run **`next dev`**.

| App | Dev server | API docs |
|-----|------------|----------|
| template-vue (Vite) | `http://localhost:5174/template-vue/` | `http://localhost:8002/docs` |
| template-react (next) | `http://localhost:3001/template-react` | `http://localhost:8003/docs` |

An HTTPS Cloudflare tunnel (`https://local.<your-domain>/<app>`, see `.env.example`) is optional: you need it only to open the app inside Telegram. Hit localhost directly when in doubt.

---

## Conventions — NEVER do

Hooks in `.claude/hooks/` hard-block the ones marked 🔒 and explain the fix.

**Backend:**
- ❌ `datetime.now()` / `datetime.utcnow()` → use `datetime.now(UTC)`
- ❌ `commit()` in a repository → use `flush()`
- ❌ `if TYPE_CHECKING:` imports in new code → import directly
- ❌ `core/` importing from `app` → core is dependency-free of apps
- ❌ Factory functions for routers / wrapper dependencies → use regular routers + dependency overrides; access `services.auth` directly
- ❌ Mutating balance/payment/credit without pessimistic locking → race conditions

**Frontend:**
- ❌ 🔒 Editing `gen/` or `schema/` → auto-generated, run `make schema`
- ❌ Server state in Pinia/Zustand → it belongs in TanStack Query
- ❌ Manual API calls → use the generated `gen/` hooks
- ❌ PrimeVue → use shadcn-vue / `reka-ui`
- ❌ Shipping one language → both `en` + `ru` translations required

**Process:**
- ❌ 🔒 Running alembic/pytest directly → use `make` (docker too, except `docker exec` into a DB for queries)
- ❌ Restarting containers for code changes → hot reload handles it
- ❌ 🔒 `--no-verify` on commits → pre-commit hooks must run
- ❌ 🔒 `git add -A` / `git stash` (and ❌ `git checkout -- <file>` on files you didn't touch) → several Claude sessions may share one checkout. Commit your own paths only (`git commit -- <paths>`), check `git diff --cached --name-only` first, and expect a stray `index.lock` or commits appearing mid-task.
- ❌ Bash-isms when the shell is zsh (the macOS default) → quote globs (`grep -rn x --include='*.vue'`), and don't keep a command in a variable (`$CMD` doesn't word-split). Use a function or an array.

### Parallel sessions: worktrees
Create a worktree only when asked. `claude -w <name>` branches from your current `HEAD` (`worktree.baseRef: "head"` in `.claude/settings.json`) and copies the `.env` files listed in `.worktreeinclude`. Run `uv sync` / `pnpm install` there before tests or typecheck. In a worktree, write code, run backend tests (testcontainers, no Docker stack needed) and frontend typecheck/lint/build. Only the main checkout runs `make up`, because container names are fixed per app (`template-vue-webhook`, `template-vue-pg`), so a second stack would replace the first.

### After code changes
- Model change → `make migration` + `make upgrade`, **in every app** (core has no migrations of its own; a core model change needs a migration in each app).
- API change → `make schema`, then `git status <frontend>/src/gen`. Kubb sometimes fails mid-run ("fetch failed") and deletes hundreds of generated files. Rerun until only the files you expect changed.
- `uv run` rewrote `uv.lock` (pre-commit then fails: "files were modified by this hook"):
  - only the `version` line of a workspace app changed → the lock is stale after a version bump; commit it on its own (`chore: sync uv.lock`). `scripts/release.sh` runs `uv lock` on every bump.
  - dependencies changed that you didn't touch → don't commit that drift: `git checkout -- uv.lock`, then `UV_FROZEN=1 git commit …`.
- Analytics event added/renamed/removed → keep your event catalog in sync (`.claude/rules/analytics.md`)
- Tests: iterate with `make test-file` / `make test-quick` (only what the change touches); run the full `make test` **once**, before the commit or PR. Every app's suite already includes core's tests. Details: `.claude/rules/testing.md` → "What to run when".
- Always → `make lint` (frontend: `pnpm typecheck` + `pnpm lint`; use `pnpm exec`, not `npx`). `make lint` covers only the app's `backend/src`. The pre-commit hook formats `core/` too, so if the first commit attempt reformats files, re-stage them and commit again.

---

## Planning

Bigger work is planned in a free-form doc under `docs/tasks/{name}/` (brief → decisions → slices; a `HANDOFF.md` when a next session continues it). For design/research, use the built-in `/deep-research` skill or the `Plan` agent (output → `docs/designs/{name}.md`). To just build a feature, describe it.
