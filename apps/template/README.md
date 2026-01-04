# Vue Web App Template

Production-ready web application template with Vue.js frontend and FastAPI backend. Supports both web and Telegram Mini App platforms.

## Features

- **Authentication** - Telegram OAuth, web login via code
- **Payments** - Telegram Stars, YooKassa integration
- **Subscriptions** - Monthly/yearly plans with cancellation flow
- **Friends** - Invite system, friend management
- **Theme** - Light/dark mode with system preference
- **i18n** - English and Russian translations
- **Analytics** - PostHog integration

## Tech Stack

### Frontend

- **Framework:** Vue 3 (Composition API)
- **Build:** Vite
- **State:** Pinia (client) + TanStack Query (server)
- **Styling:** Tailwind CSS
- **Components:** shadcn-vue
- **i18n:** vue-i18n

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
   cd apps/template
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Start services:**
   ```bash
   make up APP=template
   ```

3. **Open in browser:**
   ```
   http://localhost:5174/template
   ```

### Key URLs

- Frontend: `http://localhost:5174/template`
- API: `http://localhost:8000/api/template`
- API Docs: `http://localhost:8000/api/template/docs`

## Project Structure

```
apps/template/
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
│   └── src/
│       ├── app/
│       │   ├── presentation/ # Screens, components
│       │   │   ├── screens/  # Page components
│       │   │   ├── components/
│       │   │   └── layouts/
│       │   ├── store/        # Pinia stores
│       │   ├── composables/  # Custom hooks
│       │   ├── router/       # Vue Router
│       │   └── i18n/         # Translations
│       ├── gen/              # Generated API hooks (DO NOT EDIT)
│       └── components/ui/    # shadcn components
│
└── docker-compose.local.yml
```

## Development

### Commands

```bash
# Start all services
make up APP=template

# Stop services
make down APP=template

# View logs
make logs APP=template

# Run tests
make test APP=template

# Lint code
make lint APP=template

# Generate API types
make schema APP=template
```

### Frontend Development

```bash
cd apps/template/frontend

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
cp -r apps/template apps/myapp
```

### Step 2: Configure

- Update `APP_NAME` in `.env`
- Set `BOT_TOKEN` for your Telegram bot
- Configure database credentials

### Step 3: Customize

1. **Add screens:** Create in `frontend/src/app/presentation/screens/`
2. **Add API endpoints:** Create in `backend/src/app/webhook/routers/`
3. **Add services:** Create in `backend/src/app/services/`
4. **Update navigation:** Edit `frontend/src/app/router/`
5. **Add translations:** Edit `frontend/src/app/i18n/locales/`

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
Server State: TanStack Query (generated hooks from gen/)
Client State: Pinia (theme, modals only)
```

### Code Generation

After backend API changes:
```bash
make schema APP=template
```

This generates TypeScript hooks in `frontend/src/gen/`.

## Testing

```bash
# Run all tests
make test APP=template

# Run specific test file
make test-file file=src/app/tests/webhook/test_demo.py APP=template
```

## Deployment

### Production Setup

1. Build frontend:
   ```bash
   cd frontend && pnpm build
   ```

2. Run migrations:
   ```bash
   make upgrade APP=template
   ```

3. Start with production compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## References

- [CLAUDE.md](/CLAUDE.md) - Project guide
- [Vue Best Practices](/.claude/shared/vue-frontend.md)
- [Backend Patterns](/.claude/shared/backend-patterns.md)
