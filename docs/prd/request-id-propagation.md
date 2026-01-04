# PRD: Request ID Propagation

**Status:** ✅ Implemented (2025-12-24)

**Additions beyond original scope:**
- `user_id` added to log output (not PII, safe for logs)
- Sentry user context: `id`, `username`, `email`, `tg_username`

## Goal

Implement end-to-end request tracing by propagating a unique `request_id` through every log line, enabling correlation of all operations within a single HTTP request across services and async tasks.

## Why

- **Debugging**: Quickly filter all logs for a specific request when investigating issues
- **Log Correlation**: Connect related operations (DB queries, service calls, background jobs) to their originating request
- **Distributed Tracing Foundation**: Prepares the codebase for future OpenTelemetry/Jaeger integration
- **Production Support**: Reduces mean-time-to-resolution when debugging production incidents

## Scope

### In Scope

- Request ID generation/extraction middleware for FastAPI
- ContextVar-based request context accessible anywhere in the request lifecycle
- Logging integration to auto-inject `request_id` into all log output
- Response header propagation (`X-Request-ID`)
- Frontend header injection (pass request ID from client)

### Out of Scope

- Full distributed tracing (OpenTelemetry spans, Jaeger integration)
- Background job correlation (ARQ jobs - future enhancement)
- WebSocket request ID handling
- Telegram bot message correlation

## Implementation

### 1. Request Context Module

Create `core/backend/src/core/infrastructure/request_context.py`:

```python
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

@dataclass
class RequestContext:
    request_id: str
    path: str | None = None
    method: str | None = None

# ContextVar for async-safe request-scoped storage
_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)

def get_request_context() -> RequestContext | None:
    """Get current request context (returns None outside request lifecycle)."""
    return _request_context.get()

def get_request_id() -> str | None:
    """Get current request ID (convenience function)."""
    ctx = _request_context.get()
    return ctx.request_id if ctx else None

def set_request_context(ctx: RequestContext) -> None:
    """Set request context (called by middleware)."""
    _request_context.set(ctx)

def clear_request_context() -> None:
    """Clear request context (called by middleware on request end)."""
    _request_context.set(None)

def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid4())
```

### 2. Request ID Middleware

Create `core/backend/src/core/infrastructure/fastapi/middleware/request_id.py`:

```python
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.infrastructure.request_context import (
    RequestContext,
    clear_request_context,
    set_request_context,
)

REQUEST_ID_HEADER = "X-Request-ID"

@dataclass
class RequestIdConfig:
    """Request ID middleware configuration."""
    header_name: str = REQUEST_ID_HEADER
    generate_if_missing: bool = True
    include_in_response: bool = True

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract/generate request IDs and set request context.

    - Extracts X-Request-ID from incoming request header
    - Generates UUID if not present (configurable)
    - Sets ContextVar for request-scoped access
    - Adds X-Request-ID to response header
    """

    def __init__(self, app, config: RequestIdConfig | None = None):
        super().__init__(app)
        self.config = config or RequestIdConfig()

    async def dispatch(self, request: Request, call_next):
        # Extract or generate request ID
        request_id = request.headers.get(self.config.header_name)
        if not request_id and self.config.generate_if_missing:
            request_id = str(uuid4())

        # Set request context
        ctx = RequestContext(
            request_id=request_id or "unknown",
            path=request.url.path,
            method=request.method,
        )
        set_request_context(ctx)

        try:
            response = await call_next(request)

            # Add to response headers
            if self.config.include_in_response and request_id:
                response.headers[self.config.header_name] = request_id

            return response
        finally:
            clear_request_context()
```

### 3. Logging Integration

Update `core/backend/src/core/infrastructure/logging.py`:

```python
import logging
import sys
from typing import Any

from core.infrastructure.request_context import get_request_id

class RequestIdFilter(logging.Filter):
    """Inject request_id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True

def setup_logging():
    log_format = (
        "\033[1;36m%(filename)s:%(lineno)d\033[0m "
        "#%(levelname)-8s "
        "\033[1;32m[%(asctime)s]\033[0m "
        "\033[1;35m[%(request_id)s]\033[0m "  # NEW: request ID
        "- \033[1;34m%(name)s\033[0m "
        "- %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        force=True,
        handlers=[handler],
    )
```

### 4. Factory Integration

Update `core/backend/src/core/infrastructure/fastapi/factory.py` to add middleware:

```python
from core.infrastructure.fastapi.middleware.request_id import RequestIdMiddleware

# In create_api(), add BEFORE other middleware (executes first):
app.add_middleware(RequestIdMiddleware)

# Middleware order (last added = first executed):
# 1. RequestIdMiddleware (first - sets context)
# 2. SecurityHeadersMiddleware
# 3. CORSMiddleware (last - wraps everything)
```

### 5. Middleware Module Export

Update `core/backend/src/core/infrastructure/fastapi/middleware/__init__.py`:

```python
from core.infrastructure.fastapi.middleware.request_id import (
    RequestIdConfig,
    RequestIdMiddleware,
    REQUEST_ID_HEADER,
)

__all__ = [
    # ... existing exports
    "RequestIdMiddleware",
    "RequestIdConfig",
    "REQUEST_ID_HEADER",
]
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `header_name` | `X-Request-ID` | HTTP header name for request ID |
| `generate_if_missing` | `true` | Auto-generate UUID if client doesn't provide |
| `include_in_response` | `true` | Echo request ID in response header |

## Frontend Integration

### Vue (TanStack Query)

```typescript
// lib/api.ts
import { v4 as uuidv4 } from 'uuid';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

api.interceptors.request.use((config) => {
  // Generate request ID for tracing
  config.headers['X-Request-ID'] = uuidv4();
  return config;
});
```

### React (Next.js)

```typescript
// lib/fetch.ts
import { v4 as uuidv4 } from 'uuid';

export async function apiFetch(url: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  headers.set('X-Request-ID', uuidv4());

  return fetch(url, { ...options, headers });
}
```

## Dependencies

**Backend:**
- No new dependencies (uses stdlib `contextvars`, `uuid`, `logging`)

**Frontend:**
- `uuid` package (likely already installed via other deps)

**Future (optional):**
- `structlog` - For structured JSON logging in production
- `opentelemetry-api` - For full distributed tracing

## Testing

1. **Unit tests**: Verify middleware sets/clears context correctly
2. **Integration tests**: Verify request ID flows through to logs
3. **Manual verification**:
   - Send request without header -> should generate ID
   - Send request with header -> should use provided ID
   - Check response includes `X-Request-ID` header
   - Grep logs by request ID -> should find all related entries

## Example Log Output

```
auth.py:45 #INFO     [2025-01-15 10:30:00] [a1b2c3d4-e5f6-7890-abcd-ef1234567890] - core.services.auth - User login attempt
users.py:102 #INFO   [2025-01-15 10:30:00] [a1b2c3d4-e5f6-7890-abcd-ef1234567890] - core.repos.users - Fetching user by email
auth.py:52 #INFO     [2025-01-15 10:30:01] [a1b2c3d4-e5f6-7890-abcd-ef1234567890] - core.services.auth - Login successful
```

All three log lines share the same request ID, enabling easy correlation.

## References

- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Python contextvars Documentation](https://docs.python.org/3/library/contextvars.html)
- [structlog Context Variables](https://www.structlog.org/en/latest/contextvars.html)
- [FastAPI Request ID Discussion](https://github.com/fastapi/fastapi/discussions/10230)
- [starlette-context Library](https://starlette-context.readthedocs.io/en/latest/context.html)
- [FastAPI request.state vs Context Variables](https://dev.to/akarshan/fastapi-requeststate-vs-context-variables-when-to-use-what-2c07)
