# Creating a New App from Template

**Purpose:** Step-by-step guide to create a new web application from template.

---

## Prerequisites

- Docker & Docker Compose installed
- pnpm installed (frontend)
- Telegram Bot Token (from @BotFather)
- Access to `https://local.gramkit.dev` configured

---

## Step 1: Choose Your Template

| Template | Framework | Best For |
|----------|-----------|----------|
| `apps/template-vue/` | Vue 3 + Vite | Prefer Vue, simpler setup |
| `apps/template-react/` | Next.js 16 + React 19 | Prefer React, SSR support |

Both templates include:
- Complete authentication (Email + Telegram Mini App)
- Payment system (Stars + YooKassa)
- Subscription management
- Friends/groups
- Theme management
- i18n (en, ru)
- PostHog analytics

---

## Step 2: Copy Template

```bash
# Vue template
cp -r apps/template-vue apps/myapp

# OR React template
cp -r apps/template-react apps/myapp
```

---

## Step 3: Configure Docker Compose

Edit `apps/myapp/docker-compose.local.yml`:

### 3.1 Project Name (line 3)
```yaml
name: myapp  # Was: template or template-react
```

### 3.2 Container Names
Replace all container name references:

| Old (Vue) | Old (React) | New |
|-----------|-------------|-----|
| `template-app` | `template-react-frontend` | `myapp-app` |
| `template-webhook` | `template-react-webhook` | `myapp-webhook` |
| `template-bot` | `template-react-bot` | `myapp-bot` |
| `template-worker` | `template-react-worker` | `myapp-worker` |
| `template-pg` | `template-react-pg` | `myapp-pg` |
| `template-redis` | `template-react-redis` | `myapp-redis` |

### 3.3 Ports (avoid conflicts)

Current port usage:
```
template-vue:   Frontend 5175, Backend 8002, DB 5454, Redis 6390
template-react: Frontend 5176, Backend 8003, DB 5455, Redis 6391
```

For new app, use next available:
```yaml
# Frontend
ports:
  - "5177:5173"  # Vue: external:internal
  # OR
  - "5177:3000"  # React: external:internal

# Backend (webhook)
ports:
  - "8004:8000"

# Database
ports:
  - "5456:5432"

# Redis
ports:
  - "6392:6379"
```

### 3.4 Volume Names
```yaml
volumes:
  pgdata_myapp:      # Was: pgdata_template
  cache_myapp:       # Was: cache_template
```

Note: Network names (`template-react-network` → `myapp-network`) are handled by the sed commands in Step 3.5.

### 3.5 Update Other Docker Files (React template)

The React template has multiple Docker files that need updating. Run these from your app directory:

```bash
# Production compose file
sed -i '' 's/template-react/myapp/g' docker-compose.yml

# Dev compose file (for staging deployments like Dokploy)
sed -i '' 's/template-react/myapp/g' docker-compose.dev.yml

# Production Dockerfile for frontend
sed -i '' 's/template-react/myapp/g' frontend/Dockerfile.prod
```

Files to update:
| File | What to change |
|------|----------------|
| `docker-compose.yml` | Container names, dockerfile paths, working dirs, PYTHONPATH, volumes |
| `docker-compose.dev.yml` | Same as above, but with `dev-` prefix on containers/volumes |
| `frontend/Dockerfile.prod` | Package.json paths, COPY paths, WORKDIR, static file paths |

**Already correct (no changes needed):**
- `docker-compose.local.yml` - Should be updated in Step 3
- `frontend/Dockerfile.local` - Should be updated per Step 5 instructions
- `backend/Dockerfile` - Should be updated per Step 5 instructions

---

## Step 4: Configure Environment

Copy and edit `.env`:

```bash
cp apps/template-vue/.env.example apps/myapp/.env
```

Key changes in `.env`:

```env
# App identity
APP_NAME=myapp

# API paths
WEB__API_URL=https://local.gramkit.dev/api/myapp
WEB__API_ROOT_PATH=/api/myapp

# Database (match docker-compose container name)
DB__NAME=myapp
DB__HOST=myapp-db
DB__PORT=5456

# Redis (match docker-compose container name)
REDIS__HOST=myapp-redis
REDIS__PORT=6392

# Frontend
VITE_APP_NAME=myapp
VITE_BASE_PATH=/myapp/
VITE_API_HOST=https://local.gramkit.dev/api/myapp

# Bot token (get from @BotFather)
BOT__TOKEN=your_bot_token_here
```

---

## Step 5: Update Package Metadata

### Backend Settings (required)
`apps/myapp/backend/src/app/config.py`:
```python
class Settings(BaseSettings):
    """My App application settings."""  # Update docstring

    # App identity
    app_name: str = "myapp"  # Change from "template" or "template-react"
```

This is required because `app_name` is used for:
- Session cookie name (`myapp_session`)
- Redis key prefix (`myapp:session:`)
- Bot startup message ("myapp has been started")

### Backend Package (optional, metadata only)
`apps/myapp/backend/pyproject.toml`:
```toml
[project]
name = "myapp-backend"
description = "My App - Backend"
```

### Frontend (required for pnpm)
`apps/myapp/frontend/package.json`:
```json
{
  "name": "@tma-platform/myapp-frontend"
}
```

### Browser Title & Favicon (required)

**Vue template** - Edit `apps/myapp/frontend/index.html`:
```html
<head>
  <title>My App</title>
  <link rel="icon" type="image/svg+xml" href="/myapp-icon.svg" />
</head>
```

Add your favicon file to `apps/myapp/frontend/public/` (create the directory if needed).

**React template** - Edit `apps/myapp/frontend/app/layout.tsx`:
```typescript
export const metadata: Metadata = {
  title: 'My App',  // Change from 'TMA Template React'
  description: 'My App description',
};
```

For favicon in Next.js, either:
- Add `favicon.ico` to `apps/myapp/frontend/public/`, or
- Add icon metadata:
```typescript
export const metadata: Metadata = {
  title: 'My App',
  description: 'My App description',
  icons: {
    icon: '/myapp-icon.svg',
  },
};
```

### App Logo & Name (React template only)
`apps/myapp/frontend/components/shared/logo.tsx`:

The Logo component displays in the header navigation. Update the app name and icon:

```tsx
import { Ghost } from 'lucide-react';  // Choose your icon from lucide-react

export function Logo({ size = 'md', showText = true }: LogoProps) {
  // ...
  return (
    <Link href="/" className="...">
      <Ghost className={cn(iconSize, 'text-primary')} />  {/* Change icon */}
      {showText && (
        <span className={cn(textSize, 'font-semibold text-foreground')}>
          My App  {/* Change from 'Template' */}
        </span>
      )}
    </Link>
  );
}
```

Browse available icons at [lucide.dev/icons](https://lucide.dev/icons).

### Frontend Next.js Config (React template only)
`apps/myapp/frontend/next.config.ts`:

Update the basePath to your app name:
```typescript
const nextConfig: NextConfig = {
  basePath: '/myapp',  // Change from '/template-react'
  // ...
};
```

### Frontend Kubb Config (required)
`apps/myapp/frontend/kubb.config.ts`:

Update the OpenAPI input path to your app's API endpoint:

**Vue template:**
```typescript
input: {
  // Change from template port (8002) to your app's port
  path: "http://localhost:8004/openapi.json",
},
```

**React template:**
```typescript
input: {
  // Change from template-react to your app name
  path: 'https://local.gramkit.dev/api/myapp/openapi.json',
},
```

This is required for `make schema` to generate correct TypeScript types from your API.

### Frontend API Client Config (React template only)
`apps/myapp/frontend/config/kubb-config.ts`:

**Two updates required:**

**1. Localhost port (line ~55)** - Update to match your app's backend port:
```typescript
if (hostname === 'localhost' || hostname === '127.0.0.1') {
  return 'http://localhost:8004';  // Use your backend port from docker-compose
}
```

**2. Nginx fallback path (line ~66)** - Update to your app's API path:
```typescript
// 3. Via nginx (domain access fallback)
return '/api/myapp';  // Change from '/api/template-react'
```

Both are required to avoid "Network error" messages:
- Localhost port: for local development via `localhost:3000`
- Nginx fallback: for domain access via `local.gramkit.dev/myapp`

### Frontend Dockerfile (React template only)
`apps/myapp/frontend/Dockerfile.local`:

Update paths from `template-react` to your app name:
```dockerfile
# Change this line:
COPY apps/template-react/frontend ./apps/template-react/frontend
# To:
COPY apps/myapp/frontend ./apps/myapp/frontend

# And change this line:
WORKDIR /workspace/apps/template-react/frontend
# To:
WORKDIR /workspace/apps/myapp/frontend
```

### Update pnpm Lockfile (required)
After updating package.json, run from monorepo root:
```bash
pnpm install
```

This adds the new workspace package to `pnpm-lock.yaml`. Without this step, Docker builds will fail with `ERR_PNPM_OUTDATED_LOCKFILE`.

### Update Makefile (required - CRITICAL)
`apps/myapp/Makefile`:

**This is critical!** The Makefile contains hardcoded container names. If not updated, migrations will run against the wrong database!

Replace all occurrences of `template-react` (or `template`) with your app name:
```bash
# Quick find/replace from app directory:
sed -i '' 's/template-react/myapp/g' Makefile
sed -i '' 's/template_react/myapp/g' Makefile
# OR for Vue template:
sed -i '' 's/template-webhook/myapp-webhook/g' Makefile
sed -i '' 's/template-bot/myapp-bot/g' Makefile
sed -i '' 's/apps\/template\//apps\/myapp\//g' Makefile
```

**Commands that use container names (verify these are updated):**
| Command | Container Used |
|---------|---------------|
| `shell-webhook` | `myapp-webhook` |
| `shell-bot` | `myapp-bot` |
| `migration` | `myapp-webhook` |
| `upgrade` | `myapp-webhook` |
| `downgrade` | `myapp-webhook` |
| `script` | `myapp-webhook` |
| `script-list` | `myapp-webhook` |

**Verify after updating:**
```bash
grep -n "docker exec" Makefile
# All lines should show myapp-webhook or myapp-bot, NOT template-webhook
```

### Add Backend to uv Workspace (required)
Root `pyproject.toml`:

Add your app backend to workspace members:
```toml
[tool.uv.workspace]
members = [
  "core/backend",
  "apps/template/backend",
  "apps/template-vue/backend",
  "apps/template-react/backend",
  "apps/myapp/backend"  # Add this line
]
```

Then sync the lockfile:
```bash
uv sync
```

This is required for pre-commit hooks (import linting, tests) to work.

### Update Root Makefile (required)
Root `Makefile`:

Add port mapping and color for your app:
```makefile
# Near line 10, add port:
PORT_myapp := 3003  # Use next available port

# In the `up:` target color case statement (around line 47), add:
myapp) color="\033[1;32m" ;;  # Choose a color
```

Without this, `make up APP=myapp` won't know which port to use for the frontend.

### Add Frontend lib/ to .gitignore Exception (required)
Root `.gitignore`:

The root `.gitignore` has `lib/` which ignores all lib folders (for Python). Add an exception for your app's frontend lib folder:
```gitignore
# Exception: Frontend lib directories contain source code (not Python libs)
!apps/template-vue/frontend/src/lib/
!apps/template-react/frontend/lib/
!apps/myapp/frontend/lib/  # Add this line
```

Without this, the `lib/` folder won't be committed and production builds will fail with missing imports (`cn`, error classes, etc.).

### Test Configuration

**See `.claude/rules/testing.md` for full fixture documentation.**

By default, apps use core's test fixtures. **Most apps don't need any special test setup** - just keep the minimal conftest.py that was copied from template.

#### Default Pattern (most apps - no changes needed)

Your `apps/myapp/backend/src/app/tests/conftest.py` should be minimal:

```python
from app.infrastructure.database.models.balance import Balance  # noqa: F401
from app.webhook.routers.demo import _counters

@pytest_asyncio.fixture
async def client():
    # ... HTTP client fixture
```

Core's `db_session`, `postgres_container`, etc. are automatically available.

#### Override Pattern (pgvector or special extensions)

If your app needs **pgvector** or other PostgreSQL extensions, you must override fixtures.

**Create `apps/myapp/backend/conftest.py`** (at backend root, NOT in src/app/tests/):

```python
"""Root conftest for myapp backend tests.

Overrides core's database fixtures to use pgvector.
This file is at the backend root level so it's discovered before core's fixtures.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer

from core.infrastructure.database.models.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container with pgvector support."""
    with PostgresContainer("pgvector/pgvector:pg17") as postgres:
        yield postgres


@pytest_asyncio.fixture
async def db_engine(postgres_container: PostgresContainer) -> AsyncEngine:
    """Create async database engine with pgvector extension enabled."""
    connection_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    engine = create_async_engine(
        connection_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
```

**Keep `apps/myapp/backend/src/app/tests/conftest.py` minimal** (like template-react):

```python
"""Pytest configuration for myapp app tests."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.models.balance import Balance  # noqa: F401
from app.webhook.routers.demo import _counters

# Import db_session from core - it uses our overridden db_engine
from core.testing.fixtures.database import db_session  # noqa: F401


@pytest_asyncio.fixture
async def client():
    """Create AsyncClient for testing FastAPI endpoints."""
    from app.webhook.app import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def reset_demo_counters():
    """Reset demo counters before each test."""
    _counters.clear()
    yield
    _counters.clear()
```

**Why this structure?**
- Root `backend/conftest.py` is discovered first, overriding core's fixtures
- App's `src/app/tests/conftest.py` stays minimal like template-react
- Core tests run with your fixtures when executed from your app
- `db_session` is imported from core (it uses your overridden `db_engine`)

**Apps that DON'T need special extensions:** Just copy template-react's minimal conftest - no `backend/conftest.py` needed.

---

## Step 6: Configure Nginx

Add to `nginx/nginx.conf`:

**Vue template** (frontend runs in Docker):
```nginx
# Frontend (Docker container)
location /myapp/ {
    set $myapp_frontend myapp-app:5173;
    proxy_pass http://$myapp_frontend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**React template** (frontend runs locally on host):
```nginx
# Frontend (local dev server on host machine)
location /myapp/ {
    proxy_pass http://host.docker.internal:3003/myapp/;  # Use your PORT from Makefile
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Both templates** (backend API + redirects):
```nginx
location = /myapp {
    return 301 /myapp/;
}

# Backend API
location /api/myapp {
    set $myapp_backend myapp-webhook:8000;
    proxy_pass http://$myapp_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Optional: Error pages for graceful degradation**
```nginx
# Add error handlers (show friendly message when app is down)
location @myapp_unavailable {
    default_type text/html;
    return 503 '<!DOCTYPE html><html><head><title>MyApp - Starting</title></head><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#1a1a2e;color:#fff"><div style="text-align:center"><h1>MyApp is starting...</h1><p>Please refresh in a few seconds</p></div></body></html>';
}

location @myapp_api_unavailable {
    default_type application/json;
    return 503 '{"error": "MyApp API is starting up", "retry_after": 5}';
}
```

Then add `proxy_intercept_errors on;` and `error_page 502 503 504 = @myapp_unavailable;` to each location block.

Reload nginx after changes:
```bash
docker exec nginx nginx -s reload
```

---

## Step 6.1: Add to Landing Page

Edit `nginx/landing.html` to add your app to the gateway homepage:

**1. Add CSS variable** (in `<style>` section):
```css
--myapp-color: #34D399;  /* Choose your theme color */
```

**2. Add app card** (in `apps-grid` div):
```html
<div class="app-card">
    <div class="app-header">
        <span class="app-icon">🎯</span>  <!-- Choose an emoji -->
        <div>
            <div class="app-title">My App</div>
            <span class="status-badge">ACTIVE</span>
        </div>
    </div>
    <p class="app-description">
        Brief description of your app's purpose and features.
    </p>
    <div class="app-links">
        <a href="/myapp/" class="btn btn-primary">Open App →</a>
        <a href="/api/myapp/docs" class="btn btn-secondary">API Docs</a>
    </div>
</div>
```

**3. Add to logs dropdown** (in log viewer select):
```html
<option value="myapp">MyApp</option>
```

**4. Add container class mapping** (in JavaScript containerClasses object):
```javascript
'myapp': 'myapp-webhook'
```

---

## Step 7: Start Development

```bash
# Start services
make up APP=myapp

# Check logs
make logs APP=myapp

# Run migrations (React template requires this manually)
make upgrade APP=myapp
```

**URLs:**
- Frontend: `https://local.gramkit.dev/myapp`
- API: `https://local.gramkit.dev/api/myapp`
- API Docs: `https://local.gramkit.dev/api/myapp/docs`

---

## Step 8: Remove Demo and Profile Content

**This is an essential step before deploying your app.**

The templates include demo pages (showcasing TanStack Query patterns) and a generic profile page. Most apps will have their own profile implementation, so both should be removed.

### Frontend (Vue template)
```bash
# Delete demo page and components
rm frontend/src/app/presentation/screens/Demo.vue
rm -rf frontend/src/app/presentation/components/demo/

# Delete profile page and components
rm frontend/src/app/presentation/screens/Profile.vue
rm -rf frontend/src/app/presentation/components/profile/

# Remove from router (frontend/src/app/router/router.ts)
# Delete the demo and profile route entries
```

### Frontend (React template)
```bash
# Delete demo page and components
rm -rf app/[locale]/(app)/demo/
rm -rf components/demo/

# Delete profile page and components
rm -rf app/[locale]/(app)/profile/
rm -rf components/profile/
```

### Update Navigation (React template)
Edit `frontend/config/navigation.ts` to remove the profile tab:
```typescript
export const tabs = [
  {
    id: 'home',
    label: 'Home',
    path: '/',
    icon: 'home',
  },
  // Remove the profile tab entry
] as const;
```

### Choose Mobile Layout (React template)

The template supports two mobile navigation layouts:

| Layout | Best For | Description |
|--------|----------|-------------|
| `bottom-tabs` (default) | Consumer apps with 2-5 sections | iOS-style bottom navigation bar |
| `hamburger` | Admin/dashboard apps with many tabs | Minimal header (logo + ☰), everything in slide-out menu |

**To change the layout**, edit `frontend/config/layout.ts`:

```tsx
export const layoutConfig = {
  // Change to 'hamburger' for admin/dashboard apps
  mobileLayout: 'bottom-tabs' as MobileLayout,
} as const;
```

This is the single source of truth - AppNav reads from this config.

**Hamburger layout on mobile:**
```
┌─────────────────────────────┐
│ [Logo]                  [☰] │  ← minimal header
└─────────────────────────────┘
         tap ☰ opens:
┌────────────────┐
│ Navigation     │
│ ───────────────│
│ > Demo         │
│   Profile      │
│ ───────────────│
│ Language  [🌐] │
│ Theme     [🌙] │
│ ───────────────│
│ [Profile/Login]│
└────────────────┘
```

**Note:** Shells handle padding automatically based on the layout.

**Example:** an app with 10+ admin tabs uses the hamburger.

### Backend (both templates)
```bash
# Delete demo router and scripts
rm backend/src/app/webhook/routers/demo.py
rm backend/src/app/scripts/demo_user_stats.py
```

Update these files to remove demo references:
- `backend/src/app/webhook/routers/__init__.py` - remove `demo` from imports and `__all__`
- `backend/src/app/webhook/app.py` - remove `routers.demo.router` from routers list
- `backend/src/app/tests/conftest.py` - remove demo counter import and reset fixture

### i18n (both templates)
Edit `backend/src/app/i18n/locales/{en,ru}.json` and `frontend/` i18n files to remove demo-related translations.

### Restart and Regenerate Types
After removing demo endpoints, restart backend and regenerate frontend types:
```bash
# Restart backend to pick up router changes
docker compose -f docker-compose.local.yml restart webhook

# Regenerate frontend types
make schema APP=myapp
```

---

## Step 8.5: Customize Homepage & Auth Flow (React template)

The React template includes a flexible auth system. Here's how it works and how to customize it.

### Auth Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Auth Flow Overview                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AppInitProvider (providers/AppInitProvider.tsx)                │
│  └─ Calls /process_start on mount                               │
│  └─ Stores user state (null = guest, object = authenticated)    │
│  └─ Exposes reinitialize() to refresh after login/logout        │
│                                                                  │
│  useAuthRedirect (hooks/useAuthRedirect.ts)                     │
│  └─ Watches user state from AppInitProvider                     │
│  └─ Redirects authenticated users based on config               │
│  └─ Returns { isGuest, isLoading, user }                        │
│                                                                  │
│  useLogout (hooks/useLogout.ts)                                 │
│  └─ Clears query cache                                          │
│  └─ Calls reinitialize() to update user state                   │
│  └─ Redirects to home                                           │
│                                                                  │
│  useEmailLogin (hooks/useEmailAuth.ts)                          │
│  └─ Handles login API call                                      │
│  └─ Calls reinitialize() on success                             │
│  └─ useAuthRedirect then handles redirect                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `providers/AppInitProvider.tsx` | Central auth state, user data |
| `hooks/useAuth.ts` | Auth state hook (isAuthenticated, isGuest, roles) |
| `hooks/useLogout.ts` | Logout with state cleanup |
| `hooks/useEmailAuth.ts` | Email login/signup hooks |
| `components/shared/profile-dropdown.tsx` | Header profile/login button |
| `app/[locale]/(auth)/login/page.tsx` | Unified email-first login page |

### Customizing Homepage Behavior

By default, the template homepage (`/`) shows demo content for all users. To customize:

**Option A: Login form for guests, redirect authenticated users (like template-react)**

```tsx
// app/[locale]/(app)/page.tsx
import { useAuthRedirect } from '@/hooks/useAuthRedirect';

export default function HomePage() {
  // Configure where to redirect authenticated users
  const { isGuest, isLoading } = useAuthRedirect({
    adminRoute: '/admin',      // admin/owner users go here
    userRoute: '/dashboard',   // regular users go here
  });

  if (isLoading || !isGuest) {
    return <LoadingSpinner />;
  }

  // Show login form for guests
  return <LoginForm />;
}
```

**Option B: Same content for all users (default template behavior)**

```tsx
// app/[locale]/(app)/page.tsx
export default function HomePage() {
  // No auth redirect - page works for everyone
  return <YourContent />;
}
```

**Option C: Different content based on auth state**

```tsx
// app/[locale]/(app)/page.tsx
import { useAppInit } from '@/providers';

export default function HomePage() {
  const { user } = useAppInit();
  const isGuest = !user || user.user_type === 'GUEST';

  if (isGuest) {
    return <WelcomeContent />;
  }

  return <AuthenticatedDashboard user={user} />;
}
```

### Customizing useAuthRedirect

The hook is in `hooks/useAuthRedirect.ts`. To change default redirect routes:

```tsx
// hooks/useAuthRedirect.ts
const DEFAULT_CONFIG: Required<AuthRedirectConfig> = {
  adminRoute: '/admin/dashboard',  // Change this
  userRoute: '/my-dashboard',      // Change this
};
```

Or configure per-page:

```tsx
// Only this page uses custom routes
const { isGuest } = useAuthRedirect({
  adminRoute: '/reports',
  userRoute: '/home',
});
```

### Guest Detection

Use the exported helper for consistent guest checking:

```tsx
import { isGuestUser } from '@/hooks/useAuthRedirect';

// In any component
const { user } = useAppInit();
if (isGuestUser(user)) {
  // Show login prompt
}
```

Note: In components where you need TypeScript type narrowing (like ProfileDropdown), use the inline check instead:

```tsx
// This narrows user to non-null after the check
if (!user || user.user_type === 'GUEST') {
  return <LoginButton />;
}
// TypeScript knows user is not null here
return <UserAvatar name={user.display_name} />;
```

### ProfileDropdown Behavior

The header ProfileDropdown (`components/shared/profile-dropdown.tsx`) shows:
- **Guest**: Login button that links to `/login`
- **Authenticated**: Avatar dropdown with profile link and logout

The default behavior links to the `/login` page, which is the recommended approach.

### Login Page

The template uses a unified email-first login page at `app/[locale]/(auth)/login/page.tsx`.

**Login flow:**
1. User enters email
2. System checks if email exists → Login (password) or Signup (verification code)
3. Telegram login available as secondary option

**Features:**
- Email-first unified flow (no separate login/signup tabs)
- Password show/hide toggle
- Telegram deeplink login
- Password reset flow
- Proper keyboard handling on mobile

### After Login Flow

1. User submits credentials
2. `useEmailLogin.submit()` calls API
3. On success, `reinitialize()` is called
4. `AppInitProvider` fetches fresh user data
5. `useAuthRedirect` detects authenticated user
6. User is redirected based on role config

---

## Step 8.6: Customize Theme Colors

Both templates use **Tailwind CSS v4** with **shadcn** components (shadcn/ui for React, shadcn-vue for Vue). The theme is defined using CSS variables, following the shadcn theming convention.

### Before You Start

**Gather your design references first.** To customize the theme effectively, provide:

- [ ] **Brand colors** - Primary color hex/rgb/lch values
- [ ] **Color palette** - From Figma, design system, or existing app
- [ ] **Dark mode colors** - If different from auto-generated
- [ ] **Typography** - Font family names (Google Fonts, custom, etc.)
- [ ] **Inspiration** - Screenshots, URLs, or color schemes to match

**Example references to provide:**
```
Primary: #6b4984 (purple)
Secondary: #8d3e42 (burgundy)
Background (dark): lch(5% 1% 248deg)
Font: "Plus Jakarta Sans" for body, "Tenor Sans" for headers
Inspiration: [screenshot or URL]
```

### Theme File Location

| Template | Theme File | Fallback Colors |
|----------|------------|-----------------|
| Vue | `frontend/src/style.css` | `frontend/src/app/utils/theme-colors.ts` |
| React | `frontend/app/globals.css` | `frontend/lib/theme-colors.ts` |

### shadcn Color Variables

Both templates use standard shadcn color tokens. Update both `:root` (light) and `.dark` sections:

| Variable | Purpose | Used By |
|----------|---------|---------|
| `--background` | Page background | `bg-background` |
| `--foreground` | Main text | `text-foreground` |
| `--primary` | Buttons, links | `bg-primary`, `text-primary` |
| `--primary-foreground` | Text on primary | Button text |
| `--secondary` | Secondary actions | `bg-secondary` |
| `--muted` | Subtle backgrounds | `bg-muted` |
| `--muted-foreground` | Secondary text | `text-muted-foreground` |
| `--card` | Card backgrounds | `bg-card` |
| `--border` | Borders | `border` |
| `--ring` | Focus rings | `ring` |
| `--destructive` | Errors/danger | `bg-destructive` |

### OKLCH Color Format (Tailwind v4)

Tailwind v4 uses OKLCH: `oklch(lightness chroma hue)`

| Parameter | Range | Description |
|-----------|-------|-------------|
| Lightness | 0-1 | 0 = black, 1 = white |
| Chroma | 0-0.4 | 0 = gray, higher = saturated |
| Hue | 0-360° | Color wheel position |

**Common hues:**
- Red: ~25°
- Orange: ~70°
- Yellow: ~100°
- Green: ~145°
- Cyan: ~195°
- Blue: ~250°
- Purple: ~310°
- Pink: ~350°

### Converting Colors

**Hex to OKLCH:**
- Use [oklch.com](https://oklch.com/) converter
- Or browser DevTools color picker

**LCH to OKLCH:**
- Lightness: LCH % roughly maps to OKLCH (LCH 5% ≈ OKLCH 0.13)
- Chroma: Divide by ~100 (LCH 1% ≈ OKLCH 0.01)
- Hue: Same value

**Example conversions:**
```css
/* Hex #6b4984 (purple) → */
--primary: oklch(0.45 0.12 310);

/* LCH lch(5% 1% 248deg) (very dark blue) → */
--background: oklch(0.13 0.01 248);
```

### Example: Dark Theme Customization

```css
.dark {
  /* Very dark background with blue-purple tint */
  --background: oklch(0.13 0.01 248);
  --foreground: oklch(1.0 0 0);  /* Pure white text */

  /* Purple primary */
  --primary: oklch(0.50 0.12 310);
  --primary-foreground: oklch(1.0 0 0);

  /* Slightly lighter cards */
  --card: oklch(0.17 0.012 248);
  --card-foreground: oklch(1.0 0 0);

  /* Borders visible but subtle */
  --border: oklch(0.25 0.015 248);
}
```

### Update Telegram Header Colors

Update the theme-colors file to match your background colors:

**Vue:** `frontend/src/app/utils/theme-colors.ts`
**React:** `frontend/lib/theme-colors.ts`

```typescript
export const DEFAULT_THEME_COLORS = {
  light: '#f6f1f9',  // Match your light --background
  dark: '#0d0e12',   // Match your dark --background (hex approximation)
} as const;
```

### Custom Fonts (Optional)

Add Google Fonts import at top of your theme file:

**Vue** (`style.css`):
```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Tenor+Sans&display=swap');
```

**React** (`globals.css`):
```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Tenor+Sans&display=swap');
```

Update font variables in both `:root` and `.dark`:
```css
:root {
  --font-sans: 'Plus Jakarta Sans', Inter, sans-serif;
  --font-serif: 'Tenor Sans', Georgia, serif;
}
```

### Quick Customization Checklist

- [ ] Gather color references from designer/stakeholder
- [ ] Convert colors to OKLCH format
- [ ] Update `:root` (light mode) colors
- [ ] Update `.dark` (dark mode) colors
- [ ] Update `theme-colors.ts` fallbacks (for Telegram header)
- [ ] Add custom fonts if needed
- [ ] Test both light and dark modes
- [ ] Verify Telegram Mini App header matches theme

---

## Step 9: Add Your Features

### Key Directories
1. **Models** - `backend/src/app/infrastructure/database/models/`
2. **Repositories** - `backend/src/app/infrastructure/database/repo/`
3. **Services** - `backend/src/app/services/`
4. **Endpoints** - `backend/src/app/webhook/routers/`
5. **Frontend (Vue)** - `frontend/src/app/`
6. **Frontend (React)** - `app/`, `components/`

### Customize Content
- Update welcome screen text
- Update bot messages in `tgbot/handlers/`
- Replace favicon files in `frontend/public/` with your own (use [favicon.io](https://favicon.io/) to generate)

### After Model Changes
```bash
make migration APP=myapp msg="add my feature"
make upgrade APP=myapp
make schema APP=myapp  # Regenerate frontend types
```

---

## What's Included from Core

### Backend
- User authentication (Telegram Mini App + Email)
- Payment processing (Telegram Stars + YooKassa)
- Subscription management with cancellation
- Balance/credits system
- Groups and invitations
- Background jobs (ARQ worker)

### Frontend
- Auth flow with start params
- Payment UI components
- Subscription management screens
- Paywall component
- Theme management (light/dark)
- i18n (en, ru)
- Mock users for development

---

## Port Allocation Reference

| App | Frontend | Backend | Database | Redis |
|-----|----------|---------|----------|-------|
| template-vue | 5174 | 8002 | 5454 | 6390 |
| template-react | 3001 | 8003 | 5455 | 6391 |
| **Next available** | **3004** | **8005** | **5457** | **6393** |

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
lsof -i :5177

# Change port in docker-compose.local.yml
```

### Database Connection Failed
1. Check `DB__NAME` in `.env` matches `POSTGRES_DB` in docker-compose
2. Check `DB__HOST` matches container name (e.g., `myapp-pg`)
3. Ensure database container is running: `docker ps | grep myapp-pg`

### Container Name Conflict
```bash
# Error: Name already in use
# Solution: Ensure unique container names in docker-compose.local.yml
docker rm -f conflicting-container-name
```

### Nginx 502 Bad Gateway
1. Check container is running: `docker ps | grep myapp`
2. Verify nginx config: `docker exec nginx nginx -t`
3. Reload nginx: `docker exec nginx nginx -s reload`

### Frontend API Calls Fail (CORS/404)
1. Check `WEB__API_ROOT_PATH=/api/myapp` in backend .env
2. Check `VITE_API_HOST` points to correct path
3. Verify nginx location block is correct

### Frontend "Network Error" on Localhost (React)
**Symptoms:** API calls fail with "Network error. Please check your connection" when accessing via localhost.

**Cause:** `config/kubb-config.ts` has hardcoded localhost port from template (8003).

**Solution:** Update the port in `config/kubb-config.ts` to match your app's backend port:
```typescript
// Line ~55
return 'http://localhost:8004';  // Change to your backend port
```

### Frontend "Network Error" via Domain (React)
**Symptoms:** API calls fail with "Network error. Please check your connection" when accessing via domain (e.g., `local.gramkit.dev/myapp`), but localhost works fine.

**Cause:** `config/kubb-config.ts` has hardcoded nginx fallback path from template (`/api/template-react` instead of `/api/myapp`).

**Solution:** Update the nginx fallback path in `config/kubb-config.ts`:
```typescript
// Line ~66
return '/api/myapp';  // Change from '/api/template-react'
```

This fallback is used when:
1. Not on localhost
2. No `NEXT_PUBLIC_API_URL` env var is set

### Hot Reload Not Working
- Don't restart containers for code changes
- Check volume mounts in docker-compose.local.yml
- Wait 2-3 seconds for rebuild

### Frontend Build Fails with ERR_PNPM_OUTDATED_LOCKFILE
```bash
# Error: Cannot install with "frozen-lockfile" because pnpm-lock.yaml is not up to date
# Solution: Run pnpm install from monorepo root to update lockfile
pnpm install
```

### Frontend Container Exits with "next: not found" (React)
Check `apps/myapp/frontend/Dockerfile.local` - paths may still reference `template-react`:
```dockerfile
# Wrong:
COPY apps/template-react/frontend ./apps/template-react/frontend
WORKDIR /workspace/apps/template-react/frontend

# Correct:
COPY apps/myapp/frontend ./apps/myapp/frontend
WORKDIR /workspace/apps/myapp/frontend
```

### Tests Fail with "relation does not exist" or fixture conflicts

**Symptoms:**
- Tests fail with `ProgrammingError: relation "objects" does not exist`
- Tests fail with `extension "vector" is not available`
- Core tests fail when run from your app but pass when run standalone
- 41+ errors in `test_base_repo.py` when running full suite

**Cause:** Either:
1. Your app uses pgvector but you're using core's default `postgres:16-alpine` fixtures
2. You redefined core's fixtures in `src/app/tests/conftest.py` causing conflicts

**Solution:** See the fixtures table in `.claude/rules/testing.md`.

**Quick fix:**
- **Most apps:** Keep `src/app/tests/conftest.py` minimal (like template-react). Don't redefine `postgres_container`, `db_engine`, `db_session`.
- **pgvector apps:** Create `backend/conftest.py` (root level) to override fixtures. Keep `src/app/tests/conftest.py` minimal and import `db_session` from core.

### Session Cookie Expired (403 on Admin Pages)
If Playwright tests get 403 errors on admin-only pages, the session cookie may have expired from Redis.

**Symptoms:**
- Admin pages load UI but API calls return 403
- Works in browser but fails in Playwright
- Backend logs show "Session user authenticated" but role check fails

**Solution - Create a new admin session:**
```bash
# 1. Find an admin/owner user ID
docker exec myapp-db psql -U postgres -d myapp \
  -c "SELECT id, username, role FROM users WHERE role IN ('admin', 'owner');"

# 2. Create session in Redis (expires in 7 days)
docker exec myapp-redis redis-cli -p 6391 -a password \
  SETEX "myapp:session:test-admin-session" 604800 \
  '{"user_id":"<USER_UUID_HERE>"}'

# 3. Use the new cookie in Playwright tests
```

**Playwright cookie setup:**
```javascript
await page.context().addCookies([{
  name: 'myapp_session',
  value: 'test-admin-session',
  domain: 'local.gramkit.dev',
  path: '/'
}]);
```

---

## Related Docs

- `docs/guides/APP_ARCHITECTURE.md` - How apps connect to core
- `docs/guides/CORE_STRUCTURE.md` - What core provides
- `docs/architecture/CORE_APP_SPLIT_GUIDE.md` - Core vs app decisions
- `CLAUDE.md` - All make commands
