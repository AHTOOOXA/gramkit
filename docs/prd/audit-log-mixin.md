# Audit Log Mixin for SQLAlchemy Models

> **Status: DEFERRED**
>
> Not needed at MVP/indie scale. Revisit when:
> - Admin panel with manual data edits exists
> - Customer/regulator requests audit trail
> - Real debugging incident where this would have helped
>
> Current alternatives cover 80% of needs:
> - Payments: Stripe has complete audit history
> - User actions: PostHog event tracking
> - Debugging: Sentry + structured logging with request IDs

## Goal

Implement a lightweight audit logging system that automatically tracks INSERT, UPDATE, and DELETE operations on designated SQLAlchemy models. The system will capture who changed what, when, and the before/after values in a centralized `audit_logs` table.

## Why

- **Compliance**: Many regulations (GDPR, SOC 2) require tracking data modifications for accountability
- **Debugging**: Quickly trace when and how data changed, invaluable for production issues
- **Accountability**: Know which user or system process modified sensitive data
- **Recovery**: Ability to see historical values without implementing full versioning

## Scope

### In Scope

- Core models: `User`, `Payment`, `Subscription`, `Balance`
- App-specific models opted-in via mixin (e.g., `Reading`, `ChatMessage`)
- Actions tracked: INSERT, UPDATE, DELETE
- Fields captured: table name, record ID, action type, old/new values (JSON), user ID, timestamp

### Out of Scope

- Full version history with revert capability (use SQLAlchemy-Continuum if needed)
- Audit of read operations (SELECT queries)
- Bulk operation tracking (only ORM-level operations)
- Real-time audit streaming/webhooks
- Audit log rotation/archival (separate ops concern)

### Excluded Fields (by default)

- `password_hash`, `password`, any field containing "secret" or "token"
- `created_at`, `updated_at` (timestamps already tracked on model)
- Large binary/JSON fields can be excluded via configuration

## Implementation

### Approach: Mixin + Session Event Listeners

Use SQLAlchemy's `before_flush` event to intercept changes before they hit the database. This approach:
- Runs in the same transaction (atomic with data changes)
- Has access to old/new values via `inspect()` and `get_history()`
- Works with async sessions when listening on sync session maker

```python
# core/infrastructure/database/models/audit.py

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import JSON, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import get_history

from .base import Base, TableNameMixin

class AuditAction(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class AuditLog(Base, TableNameMixin):
    """Stores audit trail for tracked model changes."""

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # String to support UUID/int
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, native_enum=False), nullable=False)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=func.now())

    # Optional context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 length
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)


class AuditableMixin:
    """Mixin to mark a model as auditable.

    Usage:
        class Payment(Base, AuditableMixin, TableNameMixin):
            __audit_exclude__ = ['provider_metadata']  # Optional: exclude fields
            ...
    """
    __auditable__ = True
    __audit_exclude__: list[str] = []  # Override in model to exclude specific fields
```

### Event Listener Registration

```python
# core/infrastructure/database/audit_listener.py

import contextvars
from sqlalchemy import event
from sqlalchemy.orm import Session

# Context var to pass user_id from request to audit
audit_context: contextvars.ContextVar[dict] = contextvars.ContextVar('audit_context', default={})

def get_audit_context() -> dict:
    """Get current audit context (user_id, ip, etc.)"""
    return audit_context.get()

def set_audit_context(user_id: UUID | None = None, ip_address: str | None = None):
    """Set audit context for current request/task."""
    audit_context.set({
        'user_id': user_id,
        'ip_address': ip_address,
    })

EXCLUDED_FIELDS = {'created_at', 'updated_at', 'password_hash', 'password'}

def register_audit_listeners(session_factory):
    """Register audit listeners on session factory."""

    @event.listens_for(session_factory, "before_flush")
    def before_flush(session: Session, flush_context, instances):
        ctx = get_audit_context()

        for obj in session.new:
            if getattr(obj, '__auditable__', False):
                _create_audit_log(session, obj, AuditAction.INSERT, ctx)

        for obj in session.dirty:
            if getattr(obj, '__auditable__', False) and session.is_modified(obj):
                _create_audit_log(session, obj, AuditAction.UPDATE, ctx)

        for obj in session.deleted:
            if getattr(obj, '__auditable__', False):
                _create_audit_log(session, obj, AuditAction.DELETE, ctx)

def _create_audit_log(session: Session, obj, action: AuditAction, ctx: dict):
    """Create audit log entry for a model change."""
    mapper = inspect(obj.__class__)
    table_name = obj.__tablename__
    record_id = str(getattr(obj, 'id', None))

    model_excludes = set(getattr(obj, '__audit_exclude__', []))
    excludes = EXCLUDED_FIELDS | model_excludes

    old_values = {}
    new_values = {}

    for column in mapper.columns:
        if column.key in excludes:
            continue

        if action == AuditAction.INSERT:
            value = getattr(obj, column.key)
            if value is not None:
                new_values[column.key] = _serialize(value)

        elif action == AuditAction.UPDATE:
            history = get_history(obj, column.key)
            if history.has_changes():
                if history.deleted:
                    old_values[column.key] = _serialize(history.deleted[0])
                if history.added:
                    new_values[column.key] = _serialize(history.added[0])

        elif action == AuditAction.DELETE:
            value = getattr(obj, column.key)
            if value is not None:
                old_values[column.key] = _serialize(value)

    # Don't log if no meaningful changes (for UPDATE)
    if action == AuditAction.UPDATE and not old_values and not new_values:
        return

    audit_log = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=old_values or None,
        new_values=new_values or None,
        user_id=ctx.get('user_id'),
        ip_address=ctx.get('ip_address'),
    )
    session.add(audit_log)

def _serialize(value):
    """Serialize value for JSON storage."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value
```

### Integration with FastAPI

```python
# In middleware or dependency
from core.infrastructure.database.audit_listener import set_audit_context

@app.middleware("http")
async def audit_context_middleware(request: Request, call_next):
    user_id = getattr(request.state, 'user_id', None)  # Set by auth
    ip_address = request.client.host if request.client else None

    set_audit_context(user_id=user_id, ip_address=ip_address)

    response = await call_next(request)
    return response
```

## Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(128) NOT NULL,
    record_id VARCHAR(64) NOT NULL,
    action VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    user_id UUID,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent VARCHAR(512)
);

-- Indexes for common queries
CREATE INDEX ix_audit_logs_table_name ON audit_logs(table_name);
CREATE INDEX ix_audit_logs_record_id ON audit_logs(record_id);
CREATE INDEX ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX ix_audit_logs_timestamp ON audit_logs(timestamp);

-- Composite index for "what changed on this record"
CREATE INDEX ix_audit_logs_table_record ON audit_logs(table_name, record_id);
```

## Configuration

### Per-Model Configuration

```python
class Payment(Base, AuditableMixin, TableNameMixin):
    """Payment model with audit logging enabled."""
    __audit_exclude__ = ['provider_metadata', 'raw_webhook_data']
    # ... fields
```

### Disable Audit Globally (e.g., for migrations, bulk imports)

```python
# Temporarily disable
from core.infrastructure.database.audit_listener import audit_enabled

with audit_enabled.set(False):
    # Bulk operations here won't be audited
    session.bulk_insert_mappings(...)
```

### Environment-Based Toggle

```python
# In config
AUDIT_LOG_ENABLED: bool = True  # Set False in dev/test if noisy

# In listener registration
if config.AUDIT_LOG_ENABLED:
    register_audit_listeners(session_factory)
```

## Trade-offs

### Custom Implementation (Recommended)

**Pros:**
- Minimal footprint (~200 lines of code)
- Full control over what's logged and how
- Single `audit_logs` table, easy to query
- No external dependencies
- Works with existing async patterns

**Cons:**
- Must maintain ourselves
- No built-in revert/time-travel
- No UI for viewing audit history (would need to build)

### SQLAlchemy-Continuum

**Pros:**
- Full version history with revert capability
- Temporal relationship queries
- Active maintenance, mature library

**Cons:**
- Creates `_version` table per audited model (schema bloat)
- Heavier runtime overhead
- More complex configuration
- May conflict with async session patterns

### PostgreSQL-Audit (Trigger-based)

**Pros:**
- Database-level triggers (captures all changes, even raw SQL)
- Single activity table like our custom approach
- Very fast (no ORM overhead)

**Cons:**
- PostgreSQL-specific
- Harder to capture user context (requires session variables)
- Less control from Python code

### Bemi (External Service)

**Pros:**
- Zero code for audit capture
- Context-aware out of the box
- Time-travel queries

**Cons:**
- External dependency/service
- Cost for production use
- PostgreSQL-only

### Recommendation

Use the **custom implementation** for now. It covers 90% of audit needs with minimal complexity. If we later need full versioning with revert capability, consider migrating to SQLAlchemy-Continuum for specific high-value models only.

## References

- [SQLAlchemy Session Events Documentation](https://docs.sqlalchemy.org/en/20/orm/session_events.html) - Official docs on `before_flush` and other session events
- [SQLAlchemy ORM Events](https://docs.sqlalchemy.org/en/20/orm/events.html) - Complete event reference
- [Creating Audit Table in Flask-SQLAlchemy](https://medium.com/@singh.surbhicse/creating-audit-table-to-log-insert-update-and-delete-changes-in-flask-sqlalchemy-f2ca53f7b02f) - Practical walkthrough
- [Tracking Database Changes in Flask SQLAlchemy](https://sagarkaurav.hashnode.dev/tracking-database-changes-in-flask-sqlalchemy-for-audit-logs) - get_history() usage examples
- [SQLAlchemy-Continuum PyPI](https://pypi.org/project/SQLAlchemy-Continuum/) - Full versioning library
- [PostgreSQL-Audit Documentation](https://postgresql-audit.readthedocs.io/en/latest/sqlalchemy.html) - Trigger-based alternative
- [Bemi SQLAlchemy Integration](https://docs.bemi.io/orms/sqlalchemy/) - External audit service
- [starlette-audit GitHub](https://github.com/accent-starlette/starlette-audit) - Starlette/FastAPI focused audit library
