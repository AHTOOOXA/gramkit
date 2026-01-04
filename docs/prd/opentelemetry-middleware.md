# PRD: OpenTelemetry Middleware

> **Status: CANCELED**
>
> After analysis, Sentry covers all our observability needs (errors, tracing, logs, metrics, uptime, replay).
> No need for separate OpenTelemetry setup at MVP/indie scale.
> See [Issue #102](https://github.com/AHTOOOXA/tarot/issues/102) for Sentry enhancements instead.

## Goal

Add distributed tracing and observability to the FastAPI + SQLAlchemy + Redis stack using OpenTelemetry auto-instrumentation. This provides request-level visibility across HTTP handlers, database queries, and Redis operations with minimal code changes.

## Why

- **Debugging**: Trace slow requests end-to-end (HTTP -> DB -> Redis) instead of guessing
- **Performance**: Identify bottlenecks in production without reproducing locally
- **Vendor-neutral**: Export to any backend (Jaeger, Tempo, Datadog) via OTLP
- **Low effort**: Auto-instrumentation covers 90% of needs; manual spans optional

## Scope

### In Scope
- Auto-instrumentation for FastAPI, SQLAlchemy, Redis
- OTLP exporter configuration (traces only, metrics later)
- Environment variable configuration (no code config)
- Integration with existing `create_api()` factory

### Out of Scope
- Custom business logic spans (add later as needed)
- Metrics collection (phase 2)
- Logs correlation (use existing logging for now)
- Frontend tracing (separate concern)

## Implementation

### Approach: Zero-Code Instrumentation

Use `opentelemetry-distro` with environment variables. No code changes to `factory.py` needed.

**Entry point change:**
```bash
# Before
python -m app.webhook.main

# After
opentelemetry-instrument python -m app.webhook.main
```

Or via environment (preferred for Docker):
```bash
OTEL_SERVICE_NAME=tarot-api \
OTEL_TRACES_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 \
opentelemetry-instrument python -m app.webhook.main
```

### If Code Integration Needed

Only if zero-code doesn't work (e.g., async engine issues):

```python
# core/backend/src/core/infrastructure/telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_telemetry(service_name: str, otlp_endpoint: str | None = None):
    """Initialize OpenTelemetry with auto-instrumentation."""
    if not otlp_endpoint:
        return  # Disabled

    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
```

Call in `create_api()` before app creation:
```python
from core.infrastructure.telemetry import setup_telemetry
setup_telemetry(
    service_name=title,
    otlp_endpoint=settings.observability.otel_endpoint
)
```

## Configuration

### Environment Variables

Add to `ObservabilitySettings`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OBSERVABILITY__OTEL_ENABLED` | Enable OpenTelemetry | `false` |
| `OBSERVABILITY__OTEL_ENDPOINT` | OTLP collector endpoint | `""` |
| `OBSERVABILITY__OTEL_SERVICE_NAME` | Service name override | app name |

### Standard OTEL Env Vars (if using zero-code)

| Variable | Example |
|----------|---------|
| `OTEL_SERVICE_NAME` | `tarot-api` |
| `OTEL_TRACES_EXPORTER` | `otlp` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` |
| `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` | `/health,/ready` |

## Dependencies

Add to `core/backend/pyproject.toml`:

```toml
# OpenTelemetry
"opentelemetry-distro>=0.48b0",
"opentelemetry-exporter-otlp>=1.27.0",
"opentelemetry-instrumentation-fastapi>=0.48b0",
"opentelemetry-instrumentation-sqlalchemy>=0.48b0",
"opentelemetry-instrumentation-redis>=0.48b0",
```

Then run:
```bash
opentelemetry-bootstrap -a install
```

## Verification

### 1. Console Export (Development)
```bash
OTEL_TRACES_EXPORTER=console opentelemetry-instrument python -m app.webhook.main
# Make a request, see spans in stdout
```

### 2. Jaeger (Local Testing)
```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
opentelemetry-instrument python -m app.webhook.main
```
Visit `http://localhost:16686` to see traces.

### 3. Validate Instrumentation
- FastAPI: Each endpoint creates a span with HTTP method, path, status
- SQLAlchemy: Each query shows as child span with SQL operation
- Redis: Each command shows as child span (GET, SET, etc.)

## References

- [OpenTelemetry FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [OpenTelemetry SQLAlchemy Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/sqlalchemy/sqlalchemy.html)
- [OpenTelemetry Redis Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/redis/redis.html)
- [Python Zero-Code Instrumentation](https://opentelemetry.io/docs/zero-code/python/)
- [SigNoz FastAPI Guide](https://signoz.io/blog/opentelemetry-fastapi/)
- [Grafana Python OpenTelemetry Guide](https://grafana.com/blog/2024/02/20/how-to-instrument-your-python-application-using-opentelemetry/)
