# Design: Easy CRUD Solution

## Problem Statement

Creating admin CRUD interfaces requires significant boilerplate:
- **Service layer**: ~30 lines per entity (get_all, get_by_id, create, update, delete)
- **Router layer**: ~50 lines per entity (5 REST endpoints with auth, rate limiting, logging)
- **Schemas**: ~30 lines per entity (Base, Create, Update, Response classes)

For template's 9 models, this means ~1000 lines of repetitive code.

## Goals

1. **Minimize boilerplate** - Define CRUD with ~10-15 lines per entity
2. **Preserve architecture** - Use existing `RequestsRepo` → `RequestsService` flow
3. **Built-in cross-cutting concerns** - Auth, rate limiting, logging out of the box
4. **Zero new dependencies** - Build on existing patterns
5. **Easy customization** - Override any method when needed
6. **Type-safe** - Full typing support with generics

## Non-Goals

- Replacing existing custom endpoints (reports, plans with complex logic)
- Auto-generating schemas (keep explicit Pydantic schemas)
- Frontend code generation (separate concern)

---

## RBAC Integration

The solution provides flexible role-based access control at multiple levels:

### Permission Levels

| Level | How | Use Case |
|-------|-----|----------|
| **Global default** | `auth_dependency=AdminUser` | All ops require admin |
| **Per-operation** | `auth_create=OwnerUser` | Delete requires owner, others admin |
| **Per-entity type** | Different routers with different auth | Settings: owner-only, Details: user-readable |
| **Row-level** | Override service methods | Users see only their own records |

### RBAC Priority (highest to lowest)

```
auth_list/auth_get/auth_create/auth_update/auth_delete  (per-operation)
    ↓ fallback
auth_dependency  (global for this router)
    ↓ fallback
AdminUser  (hardcoded default)
```

### Available Auth Dependencies

From `core/auth/rbac.py`:
- `AdminUser` - Requires `admin` or `owner` role
- `OwnerUser` - Requires `owner` role only
- `require_role(UserRole.X, ...)` - Custom role combinations
- `Depends(get_user)` - Any authenticated user

### Row-Level Permissions Pattern

For "users can only access their own records", override service methods:

```python
class MyRecordService(BaseService, CRUDMixin[Record, ...]):
    async def crud_list_for_user(self, user_id: UUID) -> Sequence[Record]:
        return await self.repo.records.get_by_user_id(user_id)

    async def crud_get_for_user(self, id: int, user_id: UUID) -> Record | None:
        record = await self.repo.records.get_by_id(id)
        return record if record and record.user_id == user_id else None
```

Then either:
1. Create a separate router with custom endpoints, or
2. Use the CRUD router for admin access + separate user-scoped router

---

## Solution Overview

Two components in `core/`:

```
core/backend/src/core/
├── services/
│   └── crud_mixin.py      # CRUDMixin for services
└── infrastructure/
    └── fastapi/
        └── crud_router.py  # create_crud_router() factory
```

### Architecture Flow

```
Request → Router (generated) → Service (with mixin) → Repository → DB
              ↓                      ↓
         [auth, rate limit,    [full access to
          logging built-in]     repo, bot, redis, etc.]
```

---

## Detailed Design

### 1. CRUDMixin (`core/services/crud_mixin.py`)

A mixin class that adds standard CRUD operations to any service.

```python
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from core.infrastructure.database.repo.base import BaseRepo

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDMixin(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """
    Mixin providing standard CRUD operations for services.

    Requires:
        - self.repo: Repository aggregator with named repositories
        - _crud_repo_attr: Name of the repository attribute (e.g., "steps")

    Usage:
        class StepService(BaseService, CRUDMixin[Step, StepCreate, StepUpdate]):
            _crud_repo_attr = "steps"

            # Optionally override any method for custom behavior:
            async def crud_list(self) -> Sequence[Step]:
                return await self.repo.steps.get_all_ordered_by_name()

    All methods use the repository's existing methods, preserving
    transaction management and other patterns.
    """

    _crud_repo_attr: str  # Must be set by subclass
    repo: Any  # Injected by BaseService

    def _get_repo(self) -> BaseRepo[ModelT]:
        """Get the typed repository for this entity."""
        return getattr(self.repo, self._crud_repo_attr)

    async def crud_list(self) -> Sequence[ModelT]:
        """Get all entities. Override for custom ordering/filtering."""
        return await self._get_repo().get_all()

    async def crud_get(self, id: int | str) -> ModelT | None:
        """Get single entity by ID."""
        return await self._get_repo().get_by_id(id)

    async def crud_create(self, data: CreateSchemaT) -> ModelT:
        """Create new entity from schema."""
        return await self._get_repo().create(data.model_dump())

    async def crud_update(self, id: int | str, data: UpdateSchemaT) -> ModelT | None:
        """Update entity. Returns None if not found."""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            # No fields to update, just return existing
            return await self.crud_get(id)
        return await self._get_repo().update(id, update_data)

    async def crud_delete(self, id: int | str) -> bool:
        """Delete entity. Returns True if deleted, False if not found."""
        return await self._get_repo().delete(id)
```

**Key Design Decisions:**

1. **Generic over Model + Schemas** - Provides type hints for IDE support
2. **String-based repo lookup** - Works with existing `RequestsRepo` composition pattern
3. **Uses existing BaseRepo methods** - No new DB access patterns
4. **All methods overridable** - Custom ordering, filtering, validation
5. **Preserves service access** - Still have `self.repo`, `self.bot`, `self.producer`, etc.

---

### 2. CRUD Router Factory (`core/infrastructure/fastapi/crud_router.py`)

A factory function that generates a complete CRUD router with auth, rate limiting, and logging.

```python
from __future__ import annotations

from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel

from core.auth.rbac import AdminUser
from core.infrastructure.fastapi.rate_limiter import HARD_LIMIT, SOFT_LIMIT, limiter
from core.infrastructure.logging import get_logger

ResponseSchemaT = TypeVar("ResponseSchemaT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


def create_crud_router(
    *,
    # Router config
    prefix: str,
    tags: list[str],
    # Schemas
    response_schema: type[ResponseSchemaT],
    create_schema: type[CreateSchemaT],
    update_schema: type[UpdateSchemaT],
    # Service config
    get_services: Callable,  # Dependency that returns RequestsService
    service_attr: str,  # Attribute name on services (e.g., "step_crud")
    # Method names (defaults work with CRUDMixin)
    list_method: str = "crud_list",
    get_method: str = "crud_get",
    create_method: str = "crud_create",
    update_method: str = "crud_update",
    delete_method: str = "crud_delete",
    # Customization
    entity_name: str,  # For logging and error messages (e.g., "Step")
    id_type: type = int,  # ID type for path parameter
    id_param_name: str = "id",  # Name of ID path parameter
    # RBAC Configuration (defaults to AdminUser for all)
    # Option 1: Single auth for all endpoints
    auth_dependency: Any = None,
    # Option 2: Per-operation auth (overrides auth_dependency)
    auth_list: Any = None,      # Auth for GET /items
    auth_get: Any = None,       # Auth for GET /items/{id}
    auth_create: Any = None,    # Auth for POST /items
    auth_update: Any = None,    # Auth for PUT /items/{id}
    auth_delete: Any = None,    # Auth for DELETE /items/{id}
    # Optional: disable specific endpoints
    enable_list: bool = True,
    enable_get: bool = True,
    enable_create: bool = True,
    enable_update: bool = True,
    enable_delete: bool = True,
) -> APIRouter:
    """
    Generate a complete CRUD router with auth, rate limiting, and logging.

    Example:
        # In app/webhook/routers/admin_steps.py
        from core.infrastructure.fastapi.crud_router import create_crud_router
        from app.schemas.master_data import StepSchema, StepCreate, StepUpdate
        from app.webhook.dependencies.service import get_services

        router = create_crud_router(
            prefix="/admin/steps",
            tags=["admin", "steps"],
            response_schema=StepSchema,
            create_schema=StepCreate,
            update_schema=StepUpdate,
            get_services=get_services,
            service_attr="step_crud",
            entity_name="Step",
        )

    Generated endpoints:
        GET    /admin/steps          - List all (SOFT_LIMIT)
        GET    /admin/steps/{id}     - Get one (SOFT_LIMIT)
        POST   /admin/steps          - Create (HARD_LIMIT)
        PUT    /admin/steps/{id}     - Update (HARD_LIMIT)
        DELETE /admin/steps/{id}     - Delete (HARD_LIMIT)

    All endpoints include:
        - AdminUser authentication (configurable)
        - Rate limiting (soft for reads, hard for writes)
        - Audit logging for mutations
        - Proper HTTP status codes and error messages
    """
    router = APIRouter(prefix=prefix, tags=tags)
    logger = get_logger(f"admin.{entity_name.lower()}")

    # RBAC resolution: per-operation auth > global auth > AdminUser default
    default_auth = auth_dependency if auth_dependency else AdminUser
    ListAuth = auth_list if auth_list else default_auth
    GetAuth = auth_get if auth_get else default_auth
    CreateAuth = auth_create if auth_create else default_auth
    UpdateAuth = auth_update if auth_update else default_auth
    DeleteAuth = auth_delete if auth_delete else default_auth

    # Type alias for ID path parameter
    IdParam = Annotated[id_type, Path(alias=id_param_name)]

    if enable_list:
        @router.get("", response_model=list[response_schema])
        @limiter.limit(SOFT_LIMIT)
        async def list_entities(
            request: Request,
            user: ListAuth,
            services=Depends(get_services),
        ) -> list[response_schema]:
            f"""List all {entity_name} entities."""
            service = getattr(services, service_attr)
            items = await getattr(service, list_method)()
            return [response_schema.model_validate(item) for item in items]

    if enable_get:
        @router.get(f"/{{{id_param_name}}}", response_model=response_schema)
        @limiter.limit(SOFT_LIMIT)
        async def get_entity(
            request: Request,
            entity_id: IdParam,
            user: GetAuth,
            services=Depends(get_services),
        ) -> response_schema:
            f"""Get {entity_name} by ID."""
            service = getattr(services, service_attr)
            item = await getattr(service, get_method)(entity_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            return response_schema.model_validate(item)

    if enable_create:
        @router.post("", response_model=response_schema, status_code=201)
        @limiter.limit(HARD_LIMIT)
        async def create_entity(
            request: Request,
            data: create_schema,
            user: CreateAuth,
            services=Depends(get_services),
        ) -> response_schema:
            f"""Create new {entity_name}."""
            service = getattr(services, service_attr)
            item = await getattr(service, create_method)(data)
            logger.info(f"{entity_name} created: id={item.id} by user={user.id}")
            return response_schema.model_validate(item)

    if enable_update:
        @router.put(f"/{{{id_param_name}}}", response_model=response_schema)
        @limiter.limit(HARD_LIMIT)
        async def update_entity(
            request: Request,
            entity_id: IdParam,
            data: update_schema,
            user: UpdateAuth,
            services=Depends(get_services),
        ) -> response_schema:
            f"""Update {entity_name} by ID."""
            service = getattr(services, service_attr)
            item = await getattr(service, update_method)(entity_id, data)
            if not item:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            logger.info(f"{entity_name} updated: id={item.id} by user={user.id}")
            return response_schema.model_validate(item)

    if enable_delete:
        @router.delete(f"/{{{id_param_name}}}", status_code=204)
        @limiter.limit(HARD_LIMIT)
        async def delete_entity(
            request: Request,
            entity_id: IdParam,
            user: DeleteAuth,
            services=Depends(get_services),
        ) -> None:
            f"""Delete {entity_name} by ID."""
            service = getattr(services, service_attr)
            success = await getattr(service, delete_method)(entity_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            logger.info(f"{entity_name} deleted: id={entity_id} by user={user.id}")

    return router
```

**Key Design Decisions:**

1. **Factory function, not class** - Simpler, no inheritance needed
2. **All config via kwargs** - Clear, explicit configuration
3. **Default method names match CRUDMixin** - Zero config for standard case
4. **Toggleable endpoints** - Disable any endpoint if not needed
5. **Configurable auth** - Can use different auth for different routers
6. **Proper OpenAPI docs** - Each endpoint has description

---

## Usage Examples

### Example 1: Simple Entity (Step)

**Service** (`app/services/step_crud.py`):
```python
from app.infrastructure.database.models import Step
from app.schemas.master_data import StepCreate, StepUpdate
from app.services.base import BaseService
from core.services.crud_mixin import CRUDMixin


class StepCRUDService(BaseService, CRUDMixin[Step, StepCreate, StepUpdate]):
    """CRUD service for Step entities."""

    _crud_repo_attr = "steps"

    # Override list to add custom ordering
    async def crud_list(self):
        from sqlalchemy import select
        stmt = select(Step).order_by(Step.order, Step.name)
        result = await self.repo.session.execute(stmt)
        return result.scalars().all()
```

**Router** (`app/webhook/routers/admin_steps.py`):
```python
from core.infrastructure.fastapi.crud_router import create_crud_router
from app.schemas.master_data import StepSchema, StepCreate, StepUpdate
from app.webhook.dependencies.service import get_services

router = create_crud_router(
    prefix="/admin/steps",
    tags=["admin", "steps"],
    response_schema=StepSchema,
    create_schema=StepCreate,
    update_schema=StepUpdate,
    get_services=get_services,
    service_attr="step_crud",
    entity_name="Step",
)
```

**Register service** (`app/services/requests.py`):
```python
@cached_property
def step_crud(self) -> StepCRUDService:
    return StepCRUDService(self.repo, self.producer, self, self.bot)
```

**Total: ~20 lines** (vs ~80 lines before)

---

### Example 2: Entity with FK Select (Machine)

**Service** (`app/services/machine_crud.py`):
```python
class MachineCRUDService(BaseService, CRUDMixin[Machine, MachineCreate, MachineUpdate]):
    _crud_repo_attr = "machines"

    async def crud_list(self):
        # Include step relationship for display
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        stmt = select(Machine).options(joinedload(Machine.step)).order_by(Machine.name)
        result = await self.repo.session.execute(stmt)
        return result.scalars().all()
```

---

### Example 3: Custom Validation Before Create

```python
class DetailCRUDService(BaseService, CRUDMixin[Detail, DetailCreate, DetailUpdate]):
    _crud_repo_attr = "details"

    async def crud_create(self, data: DetailCreate) -> Detail:
        # Check for duplicate name
        existing = await self.repo.details.get_by_name(data.name)
        if existing:
            raise ValueError(f"Detail with name '{data.name}' already exists")
        return await super().crud_create(data)
```

---

### Example 4: Read-Only Entity (disable create/update/delete)

```python
router = create_crud_router(
    prefix="/admin/audit-logs",
    tags=["admin", "audit"],
    response_schema=AuditLogSchema,
    create_schema=AuditLogSchema,  # Not used
    update_schema=AuditLogSchema,  # Not used
    get_services=get_services,
    service_attr="audit_logs",
    entity_name="AuditLog",
    enable_create=False,
    enable_update=False,
    enable_delete=False,
)
```

---

### Example 5: RBAC - Different Roles per Operation

```python
from core.auth.rbac import AdminUser, OwnerUser, require_role
from core.infrastructure.database.models.enums import UserRole

# Anyone authenticated can read, only admins can write
router = create_crud_router(
    prefix="/admin/details",
    tags=["admin", "details"],
    response_schema=DetailSchema,
    create_schema=DetailCreate,
    update_schema=DetailUpdate,
    get_services=get_services,
    service_attr="detail_crud",
    entity_name="Detail",
    # Per-operation auth
    auth_list=Depends(get_user),      # Any authenticated user
    auth_get=Depends(get_user),       # Any authenticated user
    auth_create=AdminUser,            # Admin only
    auth_update=AdminUser,            # Admin only
    auth_delete=OwnerUser,            # Owner only (dangerous op)
)
```

### Example 6: RBAC - Owner-Only Entity

```python
# System settings - owners only for everything
router = create_crud_router(
    prefix="/admin/settings",
    tags=["admin", "settings"],
    response_schema=SettingSchema,
    create_schema=SettingCreate,
    update_schema=SettingUpdate,
    get_services=get_services,
    service_attr="settings_crud",
    entity_name="Setting",
    auth_dependency=OwnerUser,  # All operations require owner
)
```

### Example 7: RBAC - Row-Level Permissions (Own Records)

For row-level permissions, override the service methods:

```python
class ReportCRUDService(BaseService, CRUDMixin[Report, ReportCreate, ReportUpdate]):
    _crud_repo_attr = "reports"

    async def crud_list_for_user(self, user_id: UUID) -> Sequence[Report]:
        """List only user's own reports."""
        return await self.repo.reports.get_by_user_id(user_id)

    async def crud_get_for_user(self, id: int, user_id: UUID) -> Report | None:
        """Get report only if owned by user."""
        report = await self.repo.reports.get_by_id(id)
        if report and report.user_id == user_id:
            return report
        return None  # Not found or not owned

    async def crud_delete_for_user(self, id: int, user_id: UUID) -> bool:
        """Delete only if owned by user."""
        report = await self.crud_get_for_user(id, user_id)
        if not report:
            return False
        return await self.repo.reports.delete(id)
```

Then create a custom router or use method overrides:

```python
# Option A: Custom router with user-scoped methods
router = APIRouter(prefix="/my/reports", tags=["reports"])

@router.get("", response_model=list[ReportSchema])
async def list_my_reports(
    request: Request,
    user: Annotated[UserSchema, Depends(get_user)],
    services=Depends(get_services),
):
    reports = await services.report_crud.crud_list_for_user(user.id)
    return [ReportSchema.model_validate(r) for r in reports]
```

### Example 8: Adding Custom Endpoints Alongside CRUD

```python
# app/webhook/routers/admin_orders.py

# Standard CRUD
router = create_crud_router(
    prefix="/admin/orders",
    ...
)

# Custom endpoint on same router
@router.post("/{id}/archive")
@limiter.limit(HARD_LIMIT)
async def archive_order(
    request: Request,
    id: int,
    user: AdminUser,
    services=Depends(get_services),
):
    """Archive an order (custom action)."""
    order = await services.order_crud.archive(id)
    if not order:
        raise HTTPException(404, "Order not found")
    return OrderSchema.model_validate(order)
```

---

## Migration Plan

### Phase 1: Add Core Infrastructure
1. Create `core/services/crud_mixin.py`
2. Create `core/infrastructure/fastapi/crud_router.py`
3. Add tests for both

### Phase 2: Migrate Simple Entities (Step, Machine, Detail)
1. Create `StepCRUDService`, `MachineCRUDService`, `DetailCRUDService`
2. Create router files using `create_crud_router()`
3. Register in `RequestsService`
4. Remove old service methods and router code
5. Run tests, verify OpenAPI docs

### Phase 3: Migrate Medium Entities (Order)
1. Create `OrderCRUDService` with custom logic
2. Add custom endpoints alongside CRUD

### Phase 4: Evaluate Complex Entities (Plan, Report)
- May keep custom implementation if CRUD doesn't fit well
- Or use CRUD for basic ops + custom endpoints for complex logic

---

## Testing Strategy

### Unit Tests for CRUDMixin
```python
class TestCRUDMixin:
    async def test_crud_list_calls_repo_get_all(self, mock_repo):
        service = TestService(mock_repo)
        await service.crud_list()
        mock_repo.items.get_all.assert_called_once()

    async def test_crud_create_converts_schema_to_dict(self, mock_repo):
        service = TestService(mock_repo)
        data = ItemCreate(name="test")
        await service.crud_create(data)
        mock_repo.items.create.assert_called_with({"name": "test"})

    async def test_crud_update_excludes_unset_fields(self, mock_repo):
        service = TestService(mock_repo)
        data = ItemUpdate(name="new")  # other fields not set
        await service.crud_update(1, data)
        mock_repo.items.update.assert_called_with(1, {"name": "new"})
```

### Integration Tests for Router
```python
class TestCRUDRouter:
    async def test_list_requires_admin(self, client):
        response = await client.get("/admin/steps")
        assert response.status_code == 401

    async def test_list_returns_all_items(self, admin_client, db_steps):
        response = await admin_client.get("/admin/steps")
        assert response.status_code == 200
        assert len(response.json()) == len(db_steps)

    async def test_create_logs_action(self, admin_client, caplog):
        response = await admin_client.post("/admin/steps", json={"name": "Test", "order": 1})
        assert response.status_code == 201
        assert "Step created" in caplog.text
```

---

## Alternatives Considered

### 1. FastCRUD Package
- **Pros**: Zero code, active maintenance
- **Cons**: Bypasses service layer, no built-in auth/rate-limit/logging, different transaction pattern
- **Decision**: Rejected - doesn't fit existing architecture

### 2. Generic Base Service Class (Inheritance)
- **Pros**: Single class instead of mixin
- **Cons**: Python single inheritance limits flexibility, harder to combine with other bases
- **Decision**: Rejected - mixin more flexible

### 3. Decorator-Based Approach
```python
@crud_service(repo_attr="steps")
class StepService(BaseService):
    pass
```
- **Pros**: Even less boilerplate
- **Cons**: Magic, harder to customize, IDE support issues
- **Decision**: Rejected - explicit mixin clearer

---

## Open Questions

1. **Pagination**: Should `crud_list` support pagination by default?
   - Current: No, simple `get_all()`
   - Could add: `crud_list(skip: int = 0, limit: int = 100)`

2. **Filtering**: Should router support query params for filtering?
   - Current: No, override `crud_list` for custom filtering
   - Could add: Generic filter params

3. **Bulk Operations**: Should we support bulk create/update/delete?
   - Current: No
   - Could add: `crud_bulk_create()`, `crud_bulk_delete()`

**Recommendation**: Start simple, add features as needed.

---

## Success Metrics

- **Lines of code reduction**: 70%+ for simple CRUD entities
- **Time to add new entity**: < 5 minutes
- **Test coverage**: 100% for core infrastructure
- **No regressions**: Existing functionality unchanged
