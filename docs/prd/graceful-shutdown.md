# Graceful Shutdown for FastAPI Applications

**Status: ✅ Done** (implemented in a98f5d60, timeouts updated to production values)

## Goal

Implement graceful shutdown handling for FastAPI applications to ensure zero-downtime deployments, complete active request processing before termination, and proper cleanup of database/Redis connections.

## Why

- **Zero-downtime deploys**: During rolling updates, in-flight requests should complete rather than return 502 errors
- **No dropped requests**: Clients receive responses instead of connection resets
- **Clean connection cleanup**: Database and Redis connections are properly closed, preventing resource leaks and connection pool exhaustion

## Scope

### In Scope
- Uvicorn signal handling and shutdown timeout configuration
- Active request tracking middleware
- Shutdown sequence (stop accepting -> drain requests -> close connections)
- Health check integration for Kubernetes readiness
- Docker/docker-compose signal configuration
- Core infrastructure changes in `core/backend/src/core/infrastructure/fastapi/`

### Out of Scope
- WebSocket connection draining (separate concern, more complex)
- ARQ worker graceful shutdown (already handled with `handle_signals = False`)
- Telegram bot graceful shutdown (aiogram handles this)

## Current State

### Lifespan Handler (factory.py)
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Webhook application starting up...")
    await sync_owner_roles(session_pool)
    if on_startup:
        for callback in on_startup:
            await callback(session_pool)
    logger.info("Webhook application ready")

    yield  # Application runs here

    logger.info("Webhook application shutting down...")
    await engine.dispose()
    logger.info("Database connections closed")
```

**Missing:**
- No active request tracking
- No drain period before closing connections
- Redis connections not closed in lifespan
- No shutdown timeout configuration

### Docker Configuration
- Local compose files use `stop_signal: SIGINT` for dev containers
- Production compose files have no explicit signal/timeout config
- No `stop_grace_period` configured

### Health Check
```python
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}
```

**Missing:**
- No readiness vs liveness distinction
- No shutdown-aware health check

## Implementation

### 1. Active Request Tracking Middleware

```python
# core/backend/src/core/infrastructure/fastapi/middleware.py

class RequestTracker:
    def __init__(self):
        self._active_requests = 0
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    @property
    def active_count(self) -> int:
        return self._active_requests

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()

    def start_shutdown(self):
        self._shutdown_event.set()

    async def wait_for_drain(self, timeout: float = 30.0) -> bool:
        """Wait for active requests to complete. Returns True if drained."""
        start = time.monotonic()
        while self._active_requests > 0:
            if time.monotonic() - start > timeout:
                return False
            await asyncio.sleep(0.1)
        return True

class RequestTrackerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tracker: RequestTracker):
        super().__init__(app)
        self.tracker = tracker

    async def dispatch(self, request: Request, call_next):
        # Reject new requests during shutdown (except health checks)
        if self.tracker.is_shutting_down and request.url.path != "/health":
            return Response(status_code=503, content="Service shutting down")

        async with self.tracker._lock:
            self.tracker._active_requests += 1
        try:
            return await call_next(request)
        finally:
            async with self.tracker._lock:
                self.tracker._active_requests -= 1
```

### 2. Enhanced Lifespan Handler

```python
# core/backend/src/core/infrastructure/fastapi/factory.py

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    logger.info("Application starting up...")
    await sync_owner_roles(session_pool)
    if on_startup:
        for callback in on_startup:
            await callback(session_pool)
    logger.info("Application ready")

    yield

    # Shutdown sequence
    logger.info("Shutdown initiated...")

    # 1. Signal we're shutting down (health check returns 503)
    request_tracker = app.state.request_tracker
    request_tracker.start_shutdown()
    logger.info("Marked as shutting down, rejecting new requests")

    # 2. Wait for active requests to drain
    drain_timeout = settings.web.shutdown_drain_timeout  # default 30s
    drained = await request_tracker.wait_for_drain(timeout=drain_timeout)
    if drained:
        logger.info("All requests drained successfully")
    else:
        logger.warning(f"Drain timeout after {drain_timeout}s, {request_tracker.active_count} requests still active")

    # 3. Close connections
    await RedisClient.close()
    logger.info("Redis connections closed")

    await engine.dispose()
    logger.info("Database connections closed")

    logger.info("Shutdown complete")
```

### 3. Shutdown-Aware Health Check

```python
# core/backend/src/core/infrastructure/fastapi/routers/health.py

@router.get("/health")
async def health_check(request: Request):
    """
    Health check for liveness probes.
    Always returns 200 if the process is alive.
    """
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}

@router.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check for load balancer/K8s.
    Returns 503 during shutdown to stop new traffic.
    """
    tracker: RequestTracker = request.app.state.request_tracker

    if tracker.is_shutting_down:
        return Response(
            status_code=503,
            content='{"status": "shutting_down"}',
            media_type="application/json"
        )

    return {
        "status": "ready",
        "active_requests": tracker.active_count,
        "timestamp": datetime.now(UTC).isoformat()
    }
```

### 4. Configuration

```python
# core/backend/src/core/infrastructure/config.py

class WebSettings(BaseSettings):
    # ... existing fields ...

    # Graceful shutdown
    shutdown_drain_timeout: int = 30  # seconds to wait for requests to complete
```

## Docker/Kubernetes Configuration

### Docker Compose (Production)

```yaml
# apps/{app}/docker-compose.yml

services:
  webhook:
    # ... existing config ...
    stop_signal: SIGTERM
    stop_grace_period: 35s  # drain_timeout + buffer
    command: >
      uvicorn app.webhook.app:app
        --host 0.0.0.0
        --port 3779
        --timeout-graceful-shutdown 30
```

### Kubernetes Deployment

```yaml
spec:
  terminationGracePeriodSeconds: 35
  containers:
    - name: webhook
      livenessProbe:
        httpGet:
          path: /health
          port: 3779
        initialDelaySeconds: 5
        periodSeconds: 10
      readinessProbe:
        httpGet:
          path: /ready
          port: 3779
        initialDelaySeconds: 5
        periodSeconds: 5
      lifecycle:
        preStop:
          exec:
            command: ["sleep", "5"]  # Allow LB to drain
```

### Timing Coordination

```
SIGTERM received
    |
    v
preStop hook (5s) -- LB removes pod from endpoints
    |
    v
App marks shutdown, /ready returns 503
    |
    v
Drain period (30s) -- Active requests complete
    |
    v
Close Redis/DB connections
    |
    v
Process exits
    |
Total: ~35s (matches terminationGracePeriodSeconds)
```

## Verification

### 1. Manual Testing

```bash
# Terminal 1: Start app
make up APP=template

# Terminal 2: Send long-running request
curl -X POST "https://local.gramkit.dev/api/template/slow?delay=10"

# Terminal 3: While request is running, shutdown
make down APP=template

# Expected: Terminal 2 request completes with 200, not connection reset
```

### 2. Load Test During Shutdown

```bash
# Start continuous requests
while true; do curl -s -o /dev/null -w "%{http_code}\n" \
  "https://local.gramkit.dev/api/template/health"; sleep 0.1; done

# In another terminal, restart the app
make restart APP=template

# Expected: See 200s, then 503s (shutting down), no 502s
```

### 3. Health Check Behavior

```bash
# During normal operation
curl https://local.gramkit.dev/api/template/ready
# {"status": "ready", "active_requests": 0, ...}

# During shutdown
# {"status": "shutting_down"}  with 503 status code
```

### 4. Log Verification

```
INFO  Application starting up...
INFO  Application ready
...
INFO  Shutdown initiated...
INFO  Marked as shutting down, rejecting new requests
INFO  All requests drained successfully
INFO  Redis connections closed
INFO  Database connections closed
INFO  Shutdown complete
```

## Files to Modify

| File | Changes |
|------|---------|
| `core/backend/src/core/infrastructure/fastapi/middleware.py` | Add `RequestTracker`, `RequestTrackerMiddleware` |
| `core/backend/src/core/infrastructure/fastapi/factory.py` | Enhanced lifespan, add tracker middleware |
| `core/backend/src/core/infrastructure/fastapi/routers/health.py` | Add `/ready` endpoint |
| `core/backend/src/core/infrastructure/config.py` | Add `shutdown_drain_timeout` to WebSettings |
| `apps/*/docker-compose.yml` | Add `stop_signal`, `stop_grace_period`, uvicorn timeout |

## References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) - Official lifespan documentation
- [Uvicorn Settings](https://www.uvicorn.org/settings/) - `--timeout-graceful-shutdown` option
- [Achieving Zero Downtime FastAPI Deployments](https://medium.com/@connect.hashblock/achieving-zero-downtime-fastapi-deployments-with-gunicorn-uvicorn-workers-and-health-probes-f169bdd524eb) - Health probes and graceful shutdown patterns
- [Gracefully Implementing Graceful Shutdowns](https://medium.com/@jainal/gracefully-implementing-graceful-shutdowns-5da48ea48e43) - Custom signal handlers for Kubernetes
- [Zero-Downtime Deployment in Kubernetes](https://blog.devgenius.io/zero-downtime-deployment-in-kubernetes-fe7470210b6a) - Rolling updates and readiness probes
- [How to Achieve Zero-Downtime with Kubernetes](https://www.qovery.com/blog/how-to-achieve-zero-downtime-application-with-kubernetes) - PodDisruptionBudget and preStop hooks
- [Understanding FastAPI's Lifespan Events](https://dev.turmansolutions.ai/2025/09/27/understanding-fastapis-lifespan-events-proper-initialization-and-shutdown/) - Proper initialization and cleanup patterns
