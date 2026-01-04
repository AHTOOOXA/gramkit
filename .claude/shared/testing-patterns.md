# Testing Patterns

**Quick reference for writing tests in this monorepo.**

## Test Type Decision Tree

```
Need to test...
├─ API endpoint? → CONTRACT TEST (@pytest.mark.contract)
│  └─ Use: authenticated_client or unauthenticated_client
│
├─ Bot command/handler? → CONTRACT TEST (@pytest.mark.contract)
│  └─ Use: test_bot fixture with message/callback mocks
│
├─ Complex algorithm/calculation? → BUSINESS LOGIC TEST (@pytest.mark.business_logic)
│  └─ Use: services fixture to call methods directly
│
├─ Race condition/concurrency? → BUSINESS LOGIC TEST (@pytest.mark.business_logic)
│  └─ Use: asyncio.gather() + services fixture
│
└─ Production bug fix? → REGRESSION TEST (@pytest.mark.regression + @pytest.mark.issue(N))
```

## Test Distribution (80/15/5 Rule)

| Type | % | Marker | Focus |
|------|---|--------|-------|
| **Contract** | 80% | `@pytest.mark.contract` | API, bot, worker interfaces |
| **Business Logic** | 15% | `@pytest.mark.business_logic` | Algorithms, calculations |
| **Regression** | 5% | `@pytest.mark.regression` | Bug fixes |

---

## Running Tests

```bash
# ALWAYS use make commands with APP parameter
make test APP=tarot                    # Full suite (parallel -n 2)
make test-quick APP=tarot              # Incremental (testmon + parallel) - fast dev iteration
make test-file file=path/to/test APP=tarot  # Specific file

# By marker (inside backend directory)
cd apps/template/backend
uv run pytest -m contract              # Contract tests only
uv run pytest -m business_logic        # Business logic only
uv run pytest -k test_name             # By name pattern

# Snapshots (sequential - no parallel)
make test-snapshots APP=tarot          # Validate snapshots
make test-snapshots-update APP=tarot   # Update snapshots
```

## Test Packages

| Package | Purpose | Used In |
|---------|---------|---------|
| **pytest-xdist** | Parallel execution (`-n 2`) | `make test`, CI |
| **pytest-testmon** | Incremental tests (only changed code) | `make test-quick`, pre-commit push |
| **inline-snapshot** | Inline snapshot assertions | Snapshot tests (needs `-n0`) |
| **testcontainers** | Real PostgreSQL in tests | All DB tests |

**Note:** testmon + xdist work together (since testmon 1.4+). Snapshots require sequential execution.

---

## Test Structure: AAA Pattern

```python
@pytest.mark.contract
async def test_user_registration(authenticated_client: AsyncClient):
    # ARRANGE: Set up test data
    user_data = {"username": "test_user", "language": "en"}

    # ACT: Execute operation
    response = await authenticated_client.post("/user", json=user_data)

    # ASSERT: Verify results
    assert response.status_code == 200
    assert response.json()["username"] == "test_user"
```

---

## Key Fixtures

| Fixture | Type | Use For |
|---------|------|---------|
| `authenticated_client` | `AsyncClient` | API tests requiring auth |
| `unauthenticated_client` | `AsyncClient` | Webhooks, public endpoints |
| `services` | `RequestsService` | Business logic tests |
| `repo` | `RequestsRepo` | Repository tests |
| `test_user` | `UserSchema` | Pre-created user (3 credits) |
| `db_session` | `AsyncSession` | Direct database access |
| `mock_llm_provider` | `respx.MockRouter` | Mock AI API calls |
| `mock_yookassa` | `respx.MockRouter` | Mock payment API |

---

## Contract Tests (80%)

**Purpose:** Verify public interfaces work correctly

**Key Principles:**
- ✅ Test through HTTP/bot interface (not services directly)
- ✅ Use real database (PostgreSQL testcontainer)
- ✅ Mock external services (LLM, payments)
- ✅ Focus on "does it work?" not "how does it work?"

### API Contract Test

```python
@pytest.mark.contract
async def test_create_reading(authenticated_client: AsyncClient):
    """Test reading creation via POST /readings endpoint."""
    # Arrange
    reading_data = {
        "spread_type": "three_card",
        "question": "What should I focus on?"
    }

    # Act
    response = await authenticated_client.post("/readings", json=reading_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["spread_type"] == "three_card"
    assert len(data["cards"]) == 3
```

### Bot Contract Test

```python
@pytest.mark.contract
async def test_start_command(test_bot, services: RequestsService):
    """Test /start command handler."""
    from aiogram.types import Message
    from unittest.mock import AsyncMock

    message = AsyncMock(spec=Message)
    message.from_user.id = 12345
    message.text = "/start"

    await start_command(message, services)

    message.answer.assert_called_once()
    assert "Welcome" in message.answer.call_args[0][0]
```

---

## Business Logic Tests (15%)

**Purpose:** Verify critical algorithms and internal logic

**When to Write:**
- Complex calculations (payment pricing, scoring)
- Race conditions (concurrent balance withdrawals)
- State machines (payment status transitions)
- Edge cases (timezone boundaries, negative values)

### Concurrency Test Example

```python
@pytest.mark.business_logic
async def test_concurrent_withdrawals_prevent_overdraft(services: RequestsService):
    """Pessimistic locking prevents negative balance from race conditions."""
    # Arrange: User with 1 credit
    user = await services.users.create({"username": "test"})
    await services.balance.set_credits(user.user_id, credits=1)

    # Act: Try to withdraw twice concurrently
    async def withdraw():
        try:
            await services.balance.withdraw_reading(user.user_id)
            return "success"
        except NoAvailableReadingsError:
            return "failed"

    results = await asyncio.gather(withdraw(), withdraw())

    # Assert: Exactly one succeeds
    assert results.count("success") == 1
    assert results.count("failed") == 1
    assert (await services.balance.get_by_user_id(user.user_id)).credits == 0
```

---

## Regression Tests (5%)

**Purpose:** Prevent production bugs from recurring

**Pattern:**
1. Bug reported → Create GitHub issue (#XX)
2. Write failing test that reproduces bug
3. Fix bug in production code
4. Test passes, bug documented forever

```python
@pytest.mark.regression
@pytest.mark.issue(74)
async def test_payment_webhook_final_state_protection(
    unauthenticated_client: AsyncClient,
    services: RequestsService
):
    """
    Regression test for Issue #74: Webhooks can overwrite final states.

    Date: 2025-10-24
    Impact: Medium (out-of-order webhooks could change SUCCEEDED → WAITING)
    Root Cause: Missing state machine validation
    """
    # Test setup and assertions...
```

---

## Snapshot Testing

**Use for:** Complex API responses with many fields

```python
from inline_snapshot import snapshot
from dirty_equals import IsInt, IsStr, IsPositive

@pytest.mark.contract
async def test_user_response_structure(authenticated_client):
    response = await authenticated_client.get("/user")

    assert response.json() == snapshot({
        "user_id": IsInt(IsPositive()),  # Dynamic: any positive int
        "username": "test_user",          # Static: exact match
        "created_at": IsStr(),            # Dynamic: any string
    })
```

**Update snapshots:**
```bash
make test-snapshots-update APP=tarot
```

---

## Test Naming Convention

**Pattern:** `test_<what>_<expected_behavior>`

```python
# ✅ GOOD: Clear intent
async def test_user_registration_requires_telegram_auth(): ...
async def test_concurrent_withdrawals_prevent_negative_balance(): ...
async def test_payment_webhook_updates_balance_on_success(): ...

# ❌ BAD: Vague names
async def test_user(): ...
async def test_payment_1(): ...
```

---

## Best Practices

### ✅ DO

- **Test isolation:** Each test creates own data, no shared state
- **Descriptive names:** What is being tested + expected outcome
- **One concept per test:** Don't test multiple unrelated things
- **Type matchers:** Use `IsInt`, `IsStr` for dynamic values
- **Mock externals:** LLM, payments, external APIs

### ❌ DON'T

- **Hardcode IDs:** `assert user.user_id == 1` (fails in parallel)
- **Share state:** Global variables between tests
- **Test framework:** Don't test FastAPI/Pydantic internals
- **Skip markers:** Always use `@pytest.mark.contract` etc.

---

## Common Pitfalls

### Flaky Tests

**Cause:** Hardcoded IDs, race conditions, time-dependent logic

```python
# ❌ BAD: Expects specific ID
assert user.user_id == 1  # Fails when other tests create users first!

# ✅ GOOD: Checks type, not value
assert isinstance(user.user_id, int)
assert user.user_id > 0
```

### Import Errors

```bash
# Always use make commands (PYTHONPATH set correctly)
make test APP=tarot

# Or set PYTHONPATH manually
cd apps/template/backend
PYTHONPATH=./src uv run pytest
```

---

## Test File Location

```
apps/{app}/backend/src/app/tests/
├── unit/
│   ├── repositories/     # Repository tests
│   └── services/         # Service tests
├── integration/
│   ├── webhook/          # API endpoint tests
│   ├── tgbot/            # Bot handler tests
│   └── worker/           # Worker job tests
├── conftest.py           # Fixtures
└── fixtures/             # Fixture modules
```

---

## Quick Reference

```bash
# Run tests
make test APP=tarot              # Full suite (parallel)
make test-quick APP=tarot        # Incremental (only changed code)
make test-file file=path APP=tarot  # Specific file

# Run by marker
cd apps/template/backend && uv run pytest -m contract
cd apps/template/backend && uv run pytest -m "not slow"

# Snapshots
make test-snapshots APP=tarot         # Validate
make test-snapshots-update APP=tarot  # Update

# Debug
cd apps/template/backend && uv run pytest --lf   # Last failed only
cd apps/template/backend && uv run pytest -x     # Stop on first failure
```

<!-- TODO: Consider adding:
- Fixture dependency graph showing db_session → services → test_user chain
- Autouse fixtures explanation (mock_llm_provider, mock_yookassa auto-applied)
- Custom fixture creation guide with @pytest.fixture examples
- Detailed examples for each fixture (authenticated_client, services, etc.)
