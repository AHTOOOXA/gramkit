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
| **Payments** | YooKassa integration, Telegram Stars, subscription billing |
| **Background Jobs** | ARQ for async tasks, email sending, scheduled jobs |

> Telegram features are opt-in. Leave `BOT__TOKEN` empty and you have a standard web app.

## What's Included

### Two Complete Templates

| Template | Stack | Best For | Demo |
|----------|-------|----------|------|
| **React** | Next.js 16 + Turbopack + Zustand | SSR, React 19, larger ecosystem | [react.antonchaynik.ru](https://react.antonchaynik.ru) |
| **Vue** | Vue.js 3 + Vite + Pinia | Lighter bundle, simpler state | [vue.antonchaynik.ru](https://vue.antonchaynik.ru) |

Both include:
- **5 production pages** — Home, demos, profile, admin, auth flows
- **17 tech demos** — Caching, mutations, infinite scroll, streaming, suspense
- **Full auth system** — Email+OTP, Telegram OAuth, password reset, session management
- **Tailwind CSS + shadcn** — Consistent design system, dark mode

### Shared Core

```
core/
├── backend/          # FastAPI, SQLAlchemy, auth, payments, email
├── frontend/         # Vue.js shared components
└── frontend-react/   # React shared components
```

Write once in `core/`, import into any app. No copy-paste between projects.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.14+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic |
| Frontend (Vue) | Vue.js 3, Vite, TanStack Query, Pinia, shadcn-vue |
| Frontend (React) | Next.js 16, Turbopack, TanStack Query, Zustand, shadcn/ui |
| Database | PostgreSQL, Redis |
| Styling | Tailwind CSS 3, CSS variables theming |
| Type Generation | OpenAPI → Kubb → TypeScript hooks |
| Optional | aiogram 3.x (Telegram Bot), Cloudflare Tunnel |

## Two Development Modes

### Direct Localhost (Recommended)

Native Turbopack — fastest iteration, no Docker overhead for frontend.

```
http://localhost:3001/template-react
http://localhost:5174/template-vue
```

- ~10x faster warm starts with Turbopack cache
- Frontend runs natively on your machine
- Direct API calls (CORS enabled in dev)

### Tunnel Mode

Via nginx + Cloudflare tunnel — for Telegram Mini App testing.

```
https://local.gramkit.dev/template-react
https://local.gramkit.dev/template-vue
```

- HTTPS with valid certificate
- Telegram WebApp authentication works
- Production-like environment

## Quick Start

```bash
# Clone
git clone https://github.com/AHTOOOXA/gramkit.git
cd gramkit

# Choose template
cd apps/template-vue    # Vue.js
cd apps/template-react  # React/Next.js

# Setup
cp .env.example .env    # Edit with your settings

# Start
make up APP=template-vue    # or APP=template-react

# Open
# Localhost: http://localhost:3001/template-react or http://localhost:5174/template-vue
# Tunnel: https://local.gramkit.dev/template-react
```

### Create Your Own App

```bash
cp -r apps/template-react apps/myapp
# Update: package.json, docker-compose.yml, .env
make upgrade APP=myapp
make up APP=myapp
```

## Built for Claude Code

4-layer orchestration architecture — context-efficient, parallel-ready.

```
Layer 0: CLAUDE.md           → Orchestration rules, quick reference
Layer 1: .claude/commands/   → /develop, /create-task, /execute-task, /review
Layer 2: .claude/skills/     → Auto-invoked procedures
Layer 3: .claude/agents/     → developer-agent, testing-polish-agent
```

### Slash Commands

| Command | What It Does |
|---------|--------------|
| `/create-task` | PRD → phases → parallel enrichment agents |
| `/execute-task` | Phase-by-phase execution with auto-commits |
| `/develop` | Quick delegation to developer-agent |
| `/design` | Research approaches, compare options |
| `/review` | Deep architectural review |
| `/add-testing` | Add test phases to existing task |

### Pattern Docs

10 docs in `.claude/shared/` that agents read before coding:

```
backend-patterns.md    react-frontend.md    vue-frontend.md
testing-patterns.md    monorepo-structure.md    error-handling.md
critical-rules.md    playwright-testing.md    react-animations.md
adding-packages.md
```

### Structured Task System

Auto-detects difficulty. Simple tasks: inline. Hard tasks: parallel agents.

```
docs/tasks/user-settings/
├── README.md           # PRD
├── ARCHITECTURE.md     # Contracts between phases
├── CONTEXT.md          # Current state, resumable
├── 01-models.md        # Phase with file:line refs
└── 02-api.md
```

## Commands Reference

All make commands require `APP=<name>`:

```bash
# Docker
make up APP=template-vue       # Start services
make down APP=template-vue     # Stop services
make logs APP=template-vue     # View logs
make shell-webhook APP=template-vue  # Backend shell

# Backend
make test APP=template-vue     # Run tests
make lint APP=template-vue     # Ruff + type checks
make migration msg="..." APP=template-vue  # Create migration
make upgrade APP=template-vue  # Apply migrations
make schema APP=template-vue   # Generate TypeScript types

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
│   ├── commands/        # Slash commands
│   ├── skills/          # Auto-invoked procedures
│   ├── agents/          # Subagents (developer, testing)
│   └── shared/          # Pattern docs
├── core/
│   ├── backend/         # Shared Python (FastAPI, SQLAlchemy)
│   ├── frontend/        # Shared Vue.js components
│   └── frontend-react/  # Shared React components
├── apps/
│   ├── template-vue/    # Vue.js template
│   └── template-react/  # React/Next.js template
├── docs/                # Documentation
├── nginx/               # Gateway configuration
└── Makefile             # Unified commands
```

## Requirements

- Docker & Docker Compose
- Node.js 20+ & pnpm
- Python 3.14+
- Make

**Optional:**
- Telegram Bot Token (from @BotFather)
- Cloudflare Tunnel (for TMA testing)

## Why gramkit?

- **Not a tutorial** — Production patterns from real apps shipping to users
- **Type-safe end-to-end** — Change backend, frontend types update automatically
- **Monorepo done right** — Shared core without dependency hell
- **Escape hatches** — Every feature can be disabled or swapped
- **Claude Code native** — Orchestration architecture for AI-assisted development
- **Two frameworks** — Same patterns in Vue and React, pick your preference

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes and test: `make test APP=template-vue`
4. Commit: `git commit -m "feat: your feature"`
5. Push and open a Pull Request


## License

MIT — See [LICENSE](LICENSE)
