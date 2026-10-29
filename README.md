# gramkit

Production-ready monorepo for Telegram Mini Apps and web applications.

Vue.js or React. Telegram-native or web-only. Type-safe from database to UI.

**[Live Demo (React)](https://react.antonchaynik.ru)** · [Live Demo (Vue)](https://vue.antonchaynik.ru)

## Features

| Feature | What You Get |
|---------|--------------|
| **Authentication** | Email + OTP verification, Telegram OAuth, password reset, account linking |
| **Role-Based Access** | Admin/Owner/User roles, protected routes, permission checks |
| **Real-Time Data** | WebSocket, polling, AI streaming, optimistic updates |
| **Mobile-First** | Responsive layouts, bottom navigation, Telegram Mini App detection |
| **Type-Safe API** | Auto-generated TypeScript hooks from OpenAPI schema (Kubb) |
| **i18n + Theming** | Multi-language support, dark/light mode out of the box |
| **Payments** | YooKassa (cards, embedded widget, auto-renewal) and Telegram Stars (one-time + subscriptions), refunds, hardened money path |
| **Bot Notifications** | Scheduled per-user-local-time sends with a delivery log and blocked-bot detection |
| **Admin Alerts** | Purchase / renewal / cancel / failure alerts and deploy announcements in Telegram, with tappable hashtags |
| **Background Jobs** | ARQ for async tasks, email sending, scheduled jobs, nightly backups |

> Telegram features are opt-in. Leave `BOT__TOKEN` empty and you have a standard web app.

## What's Included

### Two Complete Templates

| Template | Stack | Best For | Demo |
|----------|-------|----------|------|
| **React** | Next.js 16 + React 19 + Turbopack | SSR, larger ecosystem | [react.antonchaynik.ru](https://react.antonchaynik.ru) |
| **Vue** | Vue 3 + Vite + Pinia | Lighter bundle, simpler state | [vue.antonchaynik.ru](https://vue.antonchaynik.ru) |

Both include:
- **5 production pages** — Home, demos, profile, admin panel (overview, users, analytics, audit log, tasks, broadcasts, marketing links), auth flows
- **17 tech demos** — Caching, mutations, infinite scroll, streaming, suspense
- **Full auth system** — Email+OTP, Telegram OAuth, password reset, session management
- **Tailwind CSS v4 + shadcn** — Consistent design system, dark mode
- **Dev debug panel** — "TG Mock" (pretend to run inside Telegram) and "Login as" (switch mock users), independently

### Shared Core

```
core/
├── backend/          # FastAPI, SQLAlchemy, auth, payments, notifications, bot, worker
├── frontend/         # Vue.js shared code (platform, errors, analytics)
└── frontend-react/   # React shared code (platform, errors, analytics)
```

Write once in `core/`, import into any app. No copy-paste between projects.

What core gives every app:

- **Payments** — one `PaymentsService` over YooKassa and Telegram Stars.
  - YooKassa: idempotency keys on every charge, the webhook re-fetches the payment instead of trusting the body, at most one live subscription per user (DB-enforced), a dunning state machine for failed renewals (`PAST_DUE` with grace and daily retries), refund webhooks, and an owner alert when a webhook fails.
  - Telegram Stars: one-time purchases and Stars subscriptions that renew and cancel correctly, plus Stars refunds.
  - PostHog events for payment success/failure, including how the user paid and why it failed.
- **Notifications engine** — templates sent in morning/evening slots in each user's local time; a `notification_deliveries` log (one row per attempt) for caps; users who blocked the bot (`users.bot_blocked_at`) are skipped and un-skipped when they come back. Templates can send text, photos or native polls.
- **`seen_features`** — a per-user JSONB map plus `PATCH /users/me/seen-features` (atomic merge) for one-time reveals, coachmarks, "what's new" and capped nudges, so each new one is frontend-only.
- **Telegram admin messages** — one sender (HTML with escaping, optional rich body, plain-text fallback so an alert never drops), contextual purchase/renewal/cancel alerts with customer context, `#hashtags` for tap-to-filter, and a silent `🚀 <app> <version> · webhook started` announcement when each process starts in production.
- **Ops** — `GET /health` returns `version` and `started_at`, so a rollout is one request to check; nightly database backups to the owners in Telegram and an owner-only `/backup` command (a failed `pg_dump` is reported, never sent as an empty file); `make backup-db` / `make restore-db` (restores older dumps and fast-forwards migrations).
- **Errors** — API errors reach the UI as an `ApiError` with the backend's `message` and `code`, for object details and 422 validation errors alike.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.14+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic |
| Frontend (Vue) | Vue 3, Vite, TanStack Query, Pinia, shadcn-vue |
| Frontend (React) | Next.js 16, React 19, Turbopack, TanStack Query, shadcn/ui |
| Database | PostgreSQL, Redis |
| Styling | Tailwind CSS v4, CSS variables theming |
| Type Generation | OpenAPI → Kubb → TypeScript hooks |
| Observability | Sentry, Logfire, PostHog (all optional) |
| Optional | aiogram 3.x (Telegram Bot), Cloudflare Tunnel |

## Two Development Modes

### Direct Localhost (Recommended)

The frontend dev server runs natively on your machine; the backend runs in Docker.

```
http://localhost:3001/template-react
http://localhost:5174/template-vue/
```

- Fast warm starts (Turbopack / Vite)
- Direct API calls (CORS enabled in dev)

### Tunnel Mode

Via nginx + Cloudflare tunnel — for Telegram Mini App testing.

```
https://local.<your-domain>/template-react
https://local.<your-domain>/template-vue
```

- HTTPS with valid certificate
- Telegram WebApp authentication works
- Production-like environment

## Quick Start

```bash
# Clone
git clone https://github.com/AHTOOOXA/gramkit.git
cd gramkit

# Shared config (Cloudflare tunnel token is optional)
cp .env.example .env

# App config — pick a template
cp apps/template-vue/.env.example apps/template-vue/.env        # Vue.js
cp apps/template-react/.env.example apps/template-react/.env    # React/Next.js

# Start (backend in Docker + frontend dev server)
make up APP=template-vue    # or APP=template-react

# Open
# http://localhost:5174/template-vue/ or http://localhost:3001/template-react
```

### Create Your Own App

See [docs/guides/NEW_APP_FROM_TEMPLATE.md](docs/guides/NEW_APP_FROM_TEMPLATE.md). In short:

```bash
cp -r apps/template-react apps/myapp
# Update: package.json, docker-compose*.yml, .env, ports
make upgrade APP=myapp
make up APP=myapp
```

Core has no migrations of its own: each app's Alembic history covers core's models too, so a core model
change needs `make migration APP=<app>` in every app.

## Built for Claude Code

```
CLAUDE.md          → always-on rules, conventions, make workflow
.claude/rules/     → layer conventions, auto-loaded by path (backend, testing, vue, react, errors, ...)
.claude/hooks/     → hard stops for the "never" rules (git add -A, --no-verify, raw pytest, editing gen/)
.mcp.json          → Chrome DevTools MCP (headless) for checking UI changes in a browser
```

Generic work leans on Claude Code's built-ins: `/code-review`, `/security-review`, `/deep-research`,
the `Plan` / `Explore` agents and the `Workflow` tool for multi-agent fan-out. Parallel sessions run in
worktrees (`claude -w <name>`); `.worktreeinclude` copies the `.env` files in.

## Testing

**80/15/5 rule:** Contract tests (API, bot) → Business logic → Regression.

| Package | Purpose |
|---------|---------|
| testcontainers | Real PostgreSQL, not SQLite |
| pytest-xdist | Parallel execution |
| pytest-testmon | Incremental (only changed code) |
| inline-snapshot | Snapshot assertions |
| respx | HTTP mocking (LLM, payments) |

```bash
make test APP=myapp       # Full parallel suite (app + core)
make test-quick APP=myapp # Incremental — sub-second feedback
```

Each test runs in an isolated transaction with automatic rollback. Core ships reusable contract suites
(`core/testing/contracts/`) that apps subclass.

## Commands Reference

All make commands require `APP=<name>`:

```bash
# Docker
make up APP=template-vue       # Start services + frontend dev server
make down APP=template-vue     # Stop services
make logs APP=template-vue     # View logs
make shell-webhook APP=template-vue  # Backend shell

# Backend
make test APP=template-vue     # Run tests
make lint APP=template-vue     # Ruff + import-linter
make typecheck APP=template-vue  # Pyright
make migration msg="..." APP=template-vue  # Create migration
make upgrade APP=template-vue  # Apply migrations
make schema APP=template-vue   # Generate TypeScript types
make backup-db APP=template-vue                 # Dump the local DB to ./backups/
make restore-db file=<dump> APP=template-vue    # Install a dump (wipe + restore + migrate)

# Release (optional): bump, push dev, then merge to main and tag
make release-dev APP=template-vue BUMP=patch
make release-main APP=template-vue

# Frontend
cd apps/template-vue/frontend
pnpm dev                       # Dev server
pnpm build                     # Production build
pnpm typecheck                 # Type checking
```

## Project Structure

```
gramkit/
├── .claude/
│   ├── rules/           # Layer conventions, auto-loaded by path
│   └── hooks/           # Guard + session-start hooks
├── core/
│   ├── backend/         # Shared Python (FastAPI, SQLAlchemy)
│   ├── frontend/        # Shared Vue.js code
│   └── frontend-react/  # Shared React code
├── apps/
│   ├── template-vue/    # Vue.js template
│   └── template-react/  # React/Next.js template
├── docs/                # Guides, architecture notes
├── nginx/               # Gateway configuration
├── scripts/             # release.sh, template sync checks
└── Makefile             # Unified commands
```

## Requirements

- Docker & Docker Compose
- Node.js 20+ & pnpm
- Python 3.14+ & uv
- Make

**Optional:**
- Telegram Bot Token (from @BotFather)
- Cloudflare Tunnel (for TMA testing)
- YooKassa shop credentials (card payments)

## Why gramkit?

- **Not a tutorial** — Production patterns from real apps shipping to users
- **Type-safe end-to-end** — Change backend, frontend types update automatically
- **Monorepo done right** — Shared core without dependency hell
- **Escape hatches** — Every feature can be disabled or swapped
- **Claude Code native** — Rules and guard hooks tuned to this codebase
- **Two frameworks** — Same patterns in Vue and React, pick your preference

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Upgrading from an earlier sync? Read its **Breaking** section first:
several releases add core columns that need a migration in every app.

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes and test: `make test APP=template-vue`
4. Commit: `git commit -m "feat: your feature"`
5. Push and open a Pull Request

## License

MIT — See [LICENSE](LICENSE)
