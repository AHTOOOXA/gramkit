# React Web App Template

Production-ready web application template with Next.js frontend and FastAPI backend. Supports both web and Telegram Mini App platforms.

## Features

- **Authentication** - Email login/signup, Telegram OAuth, web login via code
- **Payments** - Telegram Stars, YooKassa integration
- **Subscriptions** - Monthly/yearly plans with cancellation flow
- **Friends** - Invite system, friend management
- **Theme** - Light/dark mode with system preference
- **i18n** - English and Russian translations
- **Analytics** - PostHog integration

## Tech Stack

### Frontend

- **Framework:** Next.js 15 (App Router) + React 19
- **State:** Zustand (client) + TanStack Query (server)
- **Styling:** Tailwind CSS
- **Components:** shadcn/ui
- **i18n:** next-intl

### Backend

- **Framework:** FastAPI
- **Database:** PostgreSQL + SQLAlchemy
- **Cache:** Redis
- **Background Jobs:** ARQ
- **Migrations:** Alembic

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and pnpm
- Make

### Setup

1. **Clone and configure:**
   ```bash
   cd apps/template-react
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Start services:**
   ```bash
   make up APP=template-react
   ```

3. **Open in browser:**
   ```
   http://localhost:3001/template-react
   ```

### Key URLs

- Frontend: `http://localhost:3001/template-react`
- API: `http://localhost:8001/api/template-react`
- API Docs: `http://localhost:8001/api/template-react/docs`

## Project Structure

```
apps/template-react/
├── backend/
│   └── src/app/
│       ├── webhook/          # FastAPI routes
│       │   └── routers/      # API endpoints
│       ├── services/         # Business logic
│       ├── infrastructure/   # Database, repos
│       ├── tgbot/            # Telegram bot
│       ├── worker/           # Background jobs
│       └── migrations/       # Alembic migrations
│
├── frontend/
│   ├── app/                  # Next.js App Router
│   │   └── [locale]/
│   │       ├── (app)/        # Main app (authenticated)
│   │       │   ├── page.tsx  # Home
│   │       │   ├── profile/
│   │       │   ├── demo/
│   │       │   └── payments/
│   │       ├── (web)/        # Web users only
│   │       └── (public)/     # Public routes
│   ├── components/
│   │   ├── ui/               # shadcn components
│   │   ├── layout/           # Layout components
│   │   └── shared/           # Shared components
│   ├── hooks/                # Custom React hooks
│   ├── src/gen/              # Generated API hooks (DO NOT EDIT)
│   └── i18n/                 # next-intl translations
│
└── docker-compose.local.yml
```

## Development

### Commands

```bash
# Start all services
make up APP=template-react

# Stop services
make down APP=template-react

# View logs
make logs APP=template-react

# Run tests
make test APP=template-react

# Lint code
make lint APP=template-react

# Generate API types
make schema APP=template-react
```

### Frontend Development

```bash
cd apps/template-react/frontend

pnpm install      # Install dependencies
pnpm dev          # Dev server (or use make up)
pnpm typecheck    # Type checking
pnpm lint         # Linting
```

### Hot Reload

All services have hot reload. Code changes take effect immediately without restart.

## Building Your App

### Step 1: Copy Template

```bash
cp -r apps/template-react apps/myapp
```

### Step 2: Configure

- Update `APP_NAME` in `.env`
- Set `BOT_TOKEN` for your Telegram bot
- Configure database credentials

### Step 3: Customize

1. **Add pages:** Create in `frontend/app/[locale]/(app)/`
2. **Add API endpoints:** Create in `backend/src/app/webhook/routers/`
3. **Add services:** Create in `backend/src/app/services/`
4. **Add components:** Create in `frontend/components/`
5. **Add translations:** Edit `frontend/i18n/messages/`

### Step 4: Run

```bash
make up APP=myapp
```

## Architecture

### Backend: 3-Layer Pattern

```
Interface Layer (webhook, tgbot, worker)
    |
Service Layer (business logic)
    |
Repository Layer (data access)
```

### Frontend: Query + Store Pattern

```
Server State: TanStack Query (generated hooks from src/gen/)
Client State: Zustand (theme, modals only)
```

### Routing: Server Component Layouts

Route groups with Server Component layouts:
- `(app)/` - Main app pages (all authenticated users)
- `(public)/` - Auth flows (login, register)
- `(web)/` - Web-only routes (redirects Telegram users)

Platform detection uses cookies set by `PlatformDetector` component.

### Code Generation

After backend API changes:
```bash
make schema APP=template-react
```

This generates TypeScript hooks in `frontend/src/gen/`.

## Testing

```bash
# Run all tests
make test APP=template-react

# Run specific test file
make test-file file=src/app/tests/webhook/test_demo.py APP=template-react
```

## Deployment

### Production Setup

1. Build frontend:
   ```bash
   cd frontend && pnpm build
   ```

2. Run migrations:
   ```bash
   make upgrade APP=template-react
   ```

3. Start with production compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## References

- [CLAUDE.md](/CLAUDE.md) - Project guide
- [React Best Practices](/.claude/shared/react-frontend.md)
- [Backend Patterns](/.claude/shared/backend-patterns.md)
- [ROUTING.md](ROUTING.md) - Routing quick reference
- [SIMPLIFIED-ARCHITECTURE.md](SIMPLIFIED-ARCHITECTURE.md) - Architecture details
