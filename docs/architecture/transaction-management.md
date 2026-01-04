# Transaction Management

**Status:** Implemented
**Pattern:** 1 Request → 1 Session → 1 Transaction

---

## Overview

Transaction boundaries are managed at the **interface layer**, not the repository layer. This ensures:
- Atomic operations per request
- Automatic rollback on errors
- Clean session lifecycle

---

## Transaction Boundaries by Layer

### FastAPI (Webhook)

Transactions managed by `get_repo()` dependency:

```python
# core/infrastructure/fastapi/dependencies.py
async def get_repo(request: Request):
    session_pool = request.app.state.session_pool
    repo_class = request.app.state.repo_class

    async with session_pool() as session:
        async with session.begin():  # Transaction starts
            yield repo_class(session)
            # Transaction commits on success
            # Transaction rolls back on exception
```

**Usage in endpoints:**
```python
@router.post("/payments/start")
async def start_payment(
    repo: RequestsRepo = Depends(get_repo),
    services: RequestsService = Depends(get_services),
):
    # All operations within single transaction
    await services.payments.create_payment(...)
    # Commits automatically when request completes
```

---

### Telegram Bot

Transactions managed by `DatabaseMiddleware`:

```python
# core/infrastructure/telegram/middlewares/database.py
class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            async with session.begin():  # Transaction starts
                data["session"] = session
                data["repo"] = self.repo_factory(session)
                result = await handler(event, data)
                # Transaction commits on success
        return result
```

**Middleware chain order:**
1. `DatabaseMiddleware` - Creates session + repo
2. `ServiceMiddleware` - Creates services from repo
3. `AuthMiddleware` - Authenticates user
4. `I18nMiddleware` - Sets locale

---

### Worker (ARQ)

Transactions managed by `WorkerContext.with_transaction()`:

```python
# core/infrastructure/arq/factory.py
class WorkerContext:
    @asynccontextmanager
    async def with_transaction(self):
        async with self.session_pool() as session:
            async with session.begin():  # Transaction starts
                repo = self.repo_class(session)
                services = self.service_factory(repo=repo, bot=self.bot)
                yield services
                # Transaction commits on success
```

**Usage in jobs:**
```python
@inject_context
async def my_job(ctx: WorkerContext, user_id: str):
    async with ctx.with_transaction() as services:
        await services.balance.deduct(user_id, 1)
        # Commits when context exits
```

---

## Repository Layer Rules

### Use `flush()` NOT `commit()`

Repositories should flush changes but never commit:

```python
# ✅ CORRECT - flush for visibility within transaction
async def create(self, data: dict) -> Model:
    entity = self.model(**data)
    self.session.add(entity)
    await self.session.flush()  # Makes visible, doesn't commit
    return entity

# ❌ WRONG - never commit in repository
async def create(self, data: dict) -> Model:
    entity = self.model(**data)
    self.session.add(entity)
    await self.session.commit()  # Transaction boundary violation!
    return entity
```

**Why?**
- Transaction boundaries are managed at interface layer
- Multiple repository operations should be atomic
- Commit in repo breaks transaction isolation

---

## Pessimistic Locking

For race-prone operations, use `get_by_id_with_lock()`:

```python
# BaseRepo provides locking methods
async def get_by_id_with_lock(
    self,
    entity_id,
    read: bool = False,      # Shared lock (allows other reads)
    nowait: bool = False,    # Fail immediately if locked
    skip_locked: bool = False # Skip locked rows
) -> Model | None:
    stmt = select(self.model).where(self.model.id == entity_id)

    if read:
        stmt = stmt.with_for_update(read=True)
    else:
        stmt = stmt.with_for_update(nowait=nowait, skip_locked=skip_locked)

    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**Use cases:**
- Balance deductions (prevent negative balance)
- Payment processing (prevent double-spending)
- Subscription updates (prevent race conditions)

**Example:**
```python
async def deduct_credits(self, user_id: UUID, amount: int):
    # Lock row to prevent concurrent deductions
    balance = await self.repo.balance.get_by_id_with_lock(user_id)
    if balance.credits < amount:
        raise InsufficientCreditsError()
    balance.credits -= amount
    await self.session.flush()
```

---

## Error Handling

### Automatic Rollback

All transaction managers rollback on exception:

```python
async with session.begin():
    await services.payments.create(...)
    raise ValueError("Something went wrong")
    # Transaction automatically rolled back
```

### Manual Rollback

For explicit control:

```python
async with session.begin():
    try:
        await services.payments.create(...)
    except PaymentError:
        await session.rollback()
        raise
```

---

## Best Practices

### DO:
- ✅ Let interface layer manage transactions
- ✅ Use `flush()` in repositories for visibility
- ✅ Use `with_for_update()` for race-prone operations
- ✅ Keep transactions short (no external API calls within)

### DON'T:
- ❌ Call `commit()` in repository layer
- ❌ Create new sessions in service layer
- ❌ Hold transactions during external API calls
- ❌ Nest transactions (use savepoints if needed)

---

## Related Docs

- `docs/guides/APP_ARCHITECTURE.md` - Entry point patterns
- `docs/guides/CORE_STRUCTURE.md` - Repository patterns
- `.claude/shared/backend-patterns.md` - Detailed patterns
