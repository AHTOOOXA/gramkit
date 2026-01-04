# Test Plan: Infrastructure Fix + OSS Showcase

## Overview

| Phase | Goal | Effort |
|-------|------|--------|
| **Phase 1** | Unblock CI — make existing tests run | 45 min |
| **Phase 2** | OSS Showcase — add core tests that impress | 19 hours |

---

## Philosophy: The 80/15/5 Rule

From `.claude/shared/testing-patterns.md`:

| Type | Target % | Marker | Focus |
|------|----------|--------|-------|
| **Contract** | 80% | `@pytest.mark.contract` | Public interfaces (API, Bot, Worker) |
| **Business Logic** | 15% | `@pytest.mark.business_logic` | Algorithms, race conditions |
| **Regression** | 5% | `@pytest.mark.regression` | Bug fixes with issue # |

**Key Principle**: Contract tests through public interfaces > unit tests of internals.

---

# Phase 1: Infrastructure Fix (45 min)

## Problem

Tests exist and pass locally, but:
1. CI is disabled (`if: false`)
2. `authenticated_client` fixture is listed but **doesn't exist**
3. App import fails without Redis config

## Connection Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WHAT EXISTS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  core/testing/fixtures/           apps/template/tests/conftest.py        │
│  ├── database.py                  │                                      │
│  │   • postgres_container         │  @fixture                            │
│  │   • db_engine                  │  async def client():                 │
│  │   • db_session                 │      from app.webhook.app import app │
│  │                                │      yield AsyncClient(app)          │
│  ├── auth.py                      │                                      │
│  │   • generate_telegram_...      │  # DOES NOT IMPORT CORE FIXTURES!    │
│  │                                │                                      │
│  ├── api_client.py                └──────────────────────────────────────│
│  │   • MockSessionManager                                                │
│  │   • authenticated_client ← DOESN'T EXIST! (listed but not defined)   │
│  │                                                                       │
│  └── users.py                                                            │
│      • test_user (needs authenticated_client - BROKEN)                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Root Cause: Why Tests Are Skipped

```
app.webhook.app imports → create_api() → initializes:

1. Database engine      ← testcontainer can handle
2. Redis (via routers)  ← BLOCKS: RedisClient._config is None
3. Sentry               ← disabled by config
```

The blocker:

```python
# core/infrastructure/redis.py line 20
cls._client = Redis.from_url(cls._config.url)  # ← _config is None!
```

## 3 Problems To Fix

### Problem 1: Ghost Fixture

```python
# core/testing/fixtures/__init__.py line 18
"authenticated_client",  # ← GHOST FIXTURE - NO IMPLEMENTATION
```

### Problem 2: App Import Requires Redis

```
app.webhook.app → create_api() → routers → SessionService → RedisClient.get_client() → FAILS
```

### Problem 3: Template Conftest Isolated

```python
# apps/template/backend/src/app/tests/conftest.py
# NO IMPORTS FROM core.testing!
async def client():
    from app.webhook.app import app  # ← fails if Redis not configured
```

## Phase 1 Fixes

### Fix 1.1: Mock Redis Config (10 min)

```python
# apps/template/backend/src/app/tests/conftest.py

import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True, scope="session")
def mock_redis_config():
    """Set Redis config so app can import without real Redis."""
    from core.infrastructure.redis import RedisClient
    RedisClient._config = MagicMock(url="redis://localhost:6379")
    yield
```

### Fix 1.2: Remove Ghost Fixtures (5 min)

```python
# core/testing/fixtures/__init__.py
__all__ = [
    # Remove: "authenticated_client",
    # Remove: "test_user",
    ...
]
```

### Fix 1.3: Enable CI (10 min)

```yaml
# .github/workflows/test-backend.yml

name: Backend Tests

on:
  push:
    branches: [main, dev, dev2]
    paths:
      - 'core/backend/**'
      - 'apps/template/backend/**'
      - 'apps/template-react/backend/**'
      - '.github/workflows/test-backend.yml'
  pull_request:
    branches: [main, dev, dev2]
    paths:
      - 'core/backend/**'
      - 'apps/template/backend/**'
      - 'apps/template-react/backend/**'

jobs:
  test:
    # REMOVED: if: false
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      matrix:
        app: [template, template-react]
      fail-fast: false

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        working-directory: ./apps/${{ matrix.app }}/backend
        run: uv sync --all-extras --dev

      - name: Run tests
        working-directory: ./apps/${{ matrix.app }}/backend
        env:
          ENV_FILE: .env.test
        run: uv run pytest src/app/tests/ -v --tb=short --maxfail=5

  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    strategy:
      matrix:
        app: [template, template-react]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        working-directory: ./apps/${{ matrix.app }}/backend
        run: uv sync --dev

      - name: Run ruff
        working-directory: ./apps/${{ matrix.app }}/backend
        run: uv run ruff check src/
```

## Phase 1 File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/template/backend/src/app/tests/conftest.py` | Modify | Add `mock_redis_config` |
| `apps/template-react/backend/src/app/tests/conftest.py` | Modify | Add `mock_redis_config` |
| `core/testing/fixtures/__init__.py` | Modify | Remove ghost fixtures |
| `.github/workflows/test-backend.yml` | Modify | Remove `if: false`, add matrix |

## Phase 1 Success Criteria

- [ ] `make test APP=template` passes (59 passed, 24 skipped)
- [ ] `make test APP=template-react` passes (4 passed, 4 skipped)
- [ ] CI runs on push/PR
- [ ] Both apps pass in CI matrix

---

# Phase 2: OSS Showcase Tests (19 hours)

## What Makes Tests "Showcase-Worthy"

Senior engineers look for:

1. **Tests as Documentation** — learn the framework by reading tests
2. **Proper Isolation** — each test creates own data
3. **Realistic Scenarios** — real-world usage, not contrived
4. **Good Naming** — `test_<what>_<expected_behavior>`
5. **AAA Pattern** — clear Arrange/Act/Assert
6. **Concurrency Awareness** — race condition tests where they matter

**Anti-patterns**:
- Testing framework internals
- Hardcoded IDs
- Shared state
- Mocking everything
- No markers

## Current State

| Component | Tests | Status |
|-----------|-------|--------|
| `core/backend/` | 0 | **Critical gap** |
| `apps/template/` | 83 | Good foundation |
| `apps/template-react/` | 8 | Minimal |

## Core Components to Test

| Component | Location | Priority | Notes |
|-----------|----------|----------|-------|
| TelegramAuthenticator | `infrastructure/auth/telegram.py` | P1 | HMAC validation |
| BaseRepo | `infrastructure/database/repo/base.py` | P1 | CRUD + locking |
| SessionService | `services/sessions.py` | P1 | Redis sessions |
| Webhook Validators | `infrastructure/webhooks/` | P1 | Signature validation |
| PaymentsService | `services/payments/service.py` | P2 | State machine |
| Bot Middlewares | `infrastructure/tgbot/middlewares/` | P3 | Auth chain |

## Phase 2 Test Examples

### TelegramAuthenticator (Flagship)

```python
# core/backend/src/core/tests/unit/test_telegram_auth.py

from core.infrastructure.auth.telegram import TelegramAuthenticator, generate_secret_key
from core.testing.fixtures.auth import generate_telegram_init_data
import pytest


class TestTelegramAuthenticator:
    """Tests for Telegram Mini App authentication."""

    def test_verify_token_with_valid_init_data(self):
        """Valid initData from Telegram is correctly verified."""
        # Arrange
        secret = generate_secret_key("test_bot_token")
        auth = TelegramAuthenticator(secret)
        init_data = generate_telegram_init_data(
            user_id=123456,
            username="test_user",
            bot_token="test_bot_token",
        )

        # Act
        user = auth.verify_token(init_data)

        # Assert
        assert user.id == 123456
        assert user.username == "test_user"

    def test_verify_token_rejects_tampered_data(self):
        """Tampered initData raises InvalidInitDataError."""
        secret = generate_secret_key("test_bot_token")
        auth = TelegramAuthenticator(secret)
        init_data = generate_telegram_init_data(
            user_id=123456,
            username="test_user",
            bot_token="test_bot_token",
        )
        tampered = init_data.replace("123456", "999999")

        with pytest.raises(InvalidInitDataError):
            auth.verify_token(tampered)

    def test_verify_token_rejects_wrong_bot_token(self):
        """initData signed with different bot token is rejected."""
        secret = generate_secret_key("wrong_token")
        auth = TelegramAuthenticator(secret)
        init_data = generate_telegram_init_data(
            user_id=123456,
            bot_token="correct_token",
        )

        with pytest.raises(InvalidInitDataError):
            auth.verify_token(init_data)
```

### BaseRepo Pessimistic Locking (Flagship)

```python
# core/backend/src/core/tests/integration/test_base_repo.py

import asyncio
import pytest
from uuid import uuid4


@pytest.mark.business_logic
class TestBaseRepoPessimisticLocking:
    """Tests for pessimistic locking in concurrent scenarios."""

    async def test_concurrent_updates_with_lock_serialize(self, db_session):
        """Pessimistic lock serializes concurrent updates."""
        # Arrange
        repo = BalanceRepo(db_session)
        balance = await repo.create({"user_id": uuid4(), "credits": 10})

        # Act - simulate concurrent deductions
        async def deduct_with_lock():
            locked = await repo.get_by_id_with_lock(balance.id)
            if locked.credits > 0:
                await repo.update(balance.id, {"credits": locked.credits - 1})
                return "success"
            return "insufficient"

        results = await asyncio.gather(*[deduct_with_lock() for _ in range(12)])

        # Assert - exactly 10 succeed, 2 fail
        assert results.count("success") == 10
        assert results.count("insufficient") == 2
```

## Phase 2 File Structure

```
core/backend/src/core/tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── auth/
│   │   └── test_telegram_authenticator.py
│   ├── services/
│   │   ├── test_session_service.py
│   │   └── test_password_service.py
│   └── webhooks/
│       ├── test_yookassa_validator.py
│       └── test_telegram_validator.py
├── integration/
│   ├── database/
│   │   └── test_base_repo.py
│   └── services/
│       └── test_payments_service.py
└── fixtures/
    └── models.py
```

## Phase 2 Effort Breakdown

| Task | Hours | Priority |
|------|-------|----------|
| Test directory structure | 0.5h | P1 |
| TelegramAuthenticator tests | 2h | P1 |
| Webhook validator tests | 1.5h | P1 |
| SessionService tests | 2h | P1 |
| BaseRepo tests | 2h | P1 |
| PaymentsService tests | 3h | P2 |
| Template integration tests | 3h | P2 |
| Bot middleware tests | 2h | P3 |
| Worker job tests | 2h | P3 |
| CI workflow (with core) | 1h | P1 |
| **Total** | **19h** | |

## Phase 2 Success Metrics

**Quantitative:**
- Core test count: 0 → 30+ tests
- CI pass rate: 100%

**Qualitative:**
- Tests readable as documentation
- New contributors learn from tests
- Tests run in < 60 seconds

---

## Implementation Order

```
Phase 1 (45 min) — Unblock CI
├── [10 min] Add mock_redis_config to template conftest
├── [10 min] Add mock_redis_config to template-react conftest
├── [5 min]  Remove ghost fixtures from core/__all__
├── [10 min] Update CI workflow
├── [5 min]  Test locally
└── [5 min]  Push and verify CI

Phase 2 (19 hours) — OSS Showcase
├── [8h] P1: Core foundation tests
├── [6h] P2: Integration tests
└── [4h] P3: Bot & worker tests
```

---

## What We're NOT Doing

- Implementing full fixture chain before Phase 2
- Adding testcontainers for Redis in Phase 1
- Unskipping infra-dependent tests in Phase 1
- Coverage requirements
- Over-engineering shared fixtures

---

## References

- [testing-patterns.md](/.claude/shared/testing-patterns.md) — Project test philosophy
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [testcontainers-python](https://testcontainers-python.readthedocs.io/)
- [Telegram Mini App Validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
