# API Client Configuration

This document explains how the Kubb-generated API client is configured for different environments.

## Overview

The frontend applications use **relative paths by default** for API requests, which works seamlessly in both local development and production environments without requiring any configuration.

## Architecture

### Generated Code (Kubb)

Kubb generates type-safe API client code from OpenAPI specs:
- **Types:** `src/gen/models/` - TypeScript interfaces
- **Client:** `src/gen/client/` - API client functions
- **Hooks:** `src/gen/hooks/` - TanStack Query hooks (Vue/React)

### Base URL Configuration

The API client is configured via `src/lib/api-client.ts`:

```typescript
import { setConfig } from '@kubb/plugin-client/clients/axios';

export function configureApiClient() {
  const apiBaseUrl = import.meta.env.VITE_API_HOST || '/api/template';

  setConfig({
    baseURL: apiBaseUrl,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}
```

## Environment-Specific Configuration

### Local Development

**No configuration needed!** Uses relative paths.

**Vue Template (apps/template):**
- Frontend: `https://local.gramkit.dev/template/`
- API: `https://local.gramkit.dev/api/template/`
- Config: `baseURL: '/api/template'` (relative)

**React Template (apps/template-react):**
- Frontend: `https://local.gramkit.dev/template-react/`
- API: `https://local.gramkit.dev/api/template-react/`
- Config: `baseURL: '/api/template-react'` (relative)

### Production (Path-Based Routing)

**Recommended setup.** No configuration needed!

```
https://yourdomain.com/
├── /template/          # Vue frontend
├── /template-react/    # React frontend
├── /api/template/      # Vue backend API
└── /api/template-react/# React backend API
```

**Nginx configuration:**
```nginx
location /api/template {
    proxy_pass http://template-backend:8000;
}

location /api/template-react {
    proxy_pass http://template-react-backend:8000;
}
```

**Frontend config:** Uses relative paths (default)
- `baseURL: '/api/template'`
- `baseURL: '/api/template-react'`

### Production (Subdomain-Based)

**Alternative setup.** Requires environment variable.

```
https://yourdomain.com/      # Frontends
https://api.yourdomain.com/  # All backends
```

**Nginx configuration:**
```nginx
# api.yourdomain.com
server {
    server_name api.yourdomain.com;

    location /template {
        proxy_pass http://template-backend:8000;
    }

    location /template-react {
        proxy_pass http://template-react-backend:8000;
    }
}
```

**Frontend config (apps/template/.env and apps/template-react/.env):**
```bash
# Vue Template
VITE_API_HOST=https://api.yourdomain.com/template

# React Template
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/template-react
```

## How It Works

### 1. Initialization

**Vue Template (`apps/template/frontend/src/main.ts`):**
```typescript
import { configureApiClient } from '@gen/client-config';

// Configure BEFORE any API calls
configureApiClient();
// Uses VITE_API_HOST from apps/template/.env
```

**React Template (`apps/template-react/frontend/app/providers.tsx`):**
```typescript
import { configureApiClient } from '@/src/gen/client-config';

// Configure IMMEDIATELY at module load
configureApiClient();
// Uses NEXT_PUBLIC_API_URL from apps/template-react/.env
```

### 2. API Requests

All generated hooks automatically use the configured baseURL:

```typescript
// Generated hook (Vue)
import { useGetCurrentUserUsersMeGet } from '@gen/hooks';

const { data: user } = useGetCurrentUserUsersMeGet();
// Requests: [baseURL]/users/me
// Local: https://local.gramkit.dev/api/template/users/me
// Prod: https://yourdomain.com/api/template/users/me
```

```typescript
// Generated hook (React)
import { useGetCurrentUserUsersMeGet } from '@/src/gen/hooks';

const { data: user } = useGetCurrentUserUsersMeGet();
// Requests: [baseURL]/users/me
// Local: https://local.gramkit.dev/api/template-react/users/me
// Prod: https://yourdomain.com/api/template-react/users/me
```

### 3. Backend Root Path

The backend FastAPI apps are configured with `root_path` to handle path prefixes:

**apps/template/backend/src/app/webhook/app.py:**
```python
app = create_api(
    # ...
    root_path=tgbot_config.api_root_path,  # "/api/template" in production
)
```

**In .env:**
```bash
# Local dev (nginx handles routing)
API_ROOT_PATH=/api/template

# Production subdomain
API_ROOT_PATH=/template
```

## Configuration Summary

| Environment | Frontend URL | API URL | baseURL Config | Backend root_path |
|------------|--------------|---------|----------------|-------------------|
| **Local Dev** | `https://local.gramkit.dev/template/` | `https://local.gramkit.dev/api/template/` | `/api/template` (default) | `/api/template` |
| **Prod (Path)** | `https://yourdomain.com/template/` | `https://yourdomain.com/api/template/` | `/api/template` (default) | `/api/template` |
| **Prod (Subdomain)** | `https://yourdomain.com/template/` | `https://api.yourdomain.com/template/` | `https://api.yourdomain.com/template` (.env) | `/template` |

## Best Practices

✅ **DO:**
- Use relative paths (default) for most deployments
- Keep API and frontend on same domain (path-based routing)
- Configure backend `root_path` to match your deployment

❌ **DON'T:**
- Hardcode full URLs in frontend code
- Set `VITE_API_BASE_URL` unless using subdomain deployment
- Mix subdomain and path-based routing

## Troubleshooting

### 405 Method Not Allowed

**Symptom:** `PATCH https://local.gramkit.dev/users/me 405`

**Cause:** Missing API prefix in URL

**Fix:** Ensure `configureApiClient()` is called before any API requests

### CORS Errors

**Symptom:** `No 'Access-Control-Allow-Origin' header`

**Cause:** API and frontend on different origins (subdomain setup)

**Fix:** Configure backend CORS settings or use path-based routing

### 404 Not Found

**Symptom:** `GET /api/template/users/me 404`

**Cause:** Backend `root_path` misconfigured

**Fix:** Ensure backend `.env` has correct `API_ROOT_PATH`

## Files

**Configuration (Environment Variables):**
- `apps/template/.env` - Vue template environment variables (VITE_API_HOST)
- `apps/template/.env.example` - Vue template example configuration
- `apps/template-react/.env` - React template environment variables (NEXT_PUBLIC_API_URL)
- `apps/template-react/.env.example` - React template example configuration

**Vue Template (Frontend):**
- `apps/template/frontend/src/lib/api-client.ts` - API client configuration
- `apps/template/frontend/src/main.ts` - Initialization (calls configureApiClient)

**React Template (Frontend):**
- `apps/template-react/frontend/src/lib/api-client.ts` - API client configuration
- `apps/template-react/frontend/app/providers.tsx` - Initialization (calls configureApiClient)

**Backend:**
- `apps/template/backend/.env` - Backend configuration (API_ROOT_PATH)
- `apps/template-react/backend/.env` - Backend configuration (API_ROOT_PATH)

**Nginx:**
- `nginx/nginx.conf` - Reverse proxy configuration
