# Test Architecture: Pure Inheritance Design

**Status:** Approved (Design Document)
**Design:** 3 (Pure Inheritance)
**Score:** 4.00/5.00

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `core/testing/fixtures/` | ✅ Implemented | database, mocks, auth, users, bot, worker |
| `core/testing/base/` | ⚠️ Not implemented | Base test classes not yet created |
| `core/testing/contracts/` | ⚠️ Not implemented | Contract tests not yet extracted |
| App test inheritance | ⚠️ Not implemented | Apps use fixtures directly, not inheritance |

**Current state:** Fixtures are implemented and used by apps. The base test class inheritance pattern described in this document has not been implemented yet. Apps write their own tests using shared fixtures.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Design Principles](#design-principles)
4. [Architecture Overview](#architecture-overview)
5. [Directory Structure](#directory-structure)
6. [Core Components](#core-components)
   - [Database Fixtures](#1-database-fixtures)
   - [Mock Fixtures](#2-mock-fixtures)
   - [Auth Helpers](#3-auth-helpers)
   - [Base Test Classes](#4-base-test-classes)
7. [App Implementation](#app-implementation)
   - [App conftest.py](#app-conftestpy)
   - [Contract Tests](#contract-tests)
   - [Integration Tests](#integration-tests)
   - [App-Specific Tests](#app-specific-tests)
8. [Test Execution Flow](#test-execution-flow)
9. [Fixture Dependency Graph](#fixture-dependency-graph)
10. [Common Patterns](#common-patterns)
11. [Migration Guide](#migration-guide)
12. [Troubleshooting](#troubleshooting)
13. [FAQ](#faq)

---

## Executive Summary

This document specifies the **Pure Inheritance** test architecture for the TMA Platform monorepo.

**Core Principle:**
> Core provides **base test classes** and **fixtures**. Apps **inherit** test classes and **provide** app-specific fixtures.

**Key Benefits:**
- Single pattern (inheritance) for all shared tests
- Full customization via method overriding
- Excellent IDE support (abstract methods)
- Clear test ownership and traceability
- No "magic" imports or implicit test discovery

**Test Distribution:**
| Location | What | Mechanism |
|----------|------|-----------|
| `core/testing/fixtures/` | Database, mocks, auth | Import |
| `core/testing/base/` | All shared test classes | Inheritance |
| `apps/{app}/tests/` | App test implementations | Classes inherit from base |

---

## Problem Statement

### What Went Wrong

The previous 30 commits attempted to extract tests to core but created:

1. **Model conflicts** - Core tests imported app models indirectly, causing SQLAlchemy mapper conflicts
2. **Fragile mocks** - 100+ lines of mock setup that broke on any change
3. **Lost coverage** - 644-line comprehensive tests reduced to shallow endpoint checks
4. **No composition testing** - `RequestsRepo._core` and `RequestsService._core` delegation never tested

### Root Cause

```
core/tests/integration/test_payments.py
  ↓ imports
core/services/payments.py
  ↓ imports (via config)
app/infrastructure/database/models/user.py (has 'balance' relationship)
  ↓ conflicts with
core/infrastructure/database/models/user.py (no 'balance' relationship)
```

### The Solution

**Core defines test CLASSES that require fixtures but don't provide them.**

Apps inherit these classes and run them with their REAL fixtures:
- REAL `RequestsRepo` (tests composition)
- REAL `RequestsService` (tests delegation)
- REAL database (tests queries, constraints)

---

## Design Principles

### 1. Single Inheritance Pattern

All shared tests use class inheritance. No pytest_plugins, no magic imports.

```python
# Core defines
class BasePaymentFlowTests(ABC): ...

# App inherits
class TestTarotPayments(BasePaymentFlowTests): ...
```

### 2. Fixtures Shared, Tests Inherited

```
┌─────────────────────────────────────────┐
│              CORE PROVIDES              │
├─────────────────────────────────────────┤
│  fixtures/     → Import directly        │
│  base/         → Inherit from           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│              APP PROVIDES               │
├─────────────────────────────────────────┤
│  conftest.py   → App-specific fixtures  │
│  tests/        → Classes inheriting     │
└─────────────────────────────────────────┘
```

### 3. Abstract Methods Define Contract

Base classes use `@abstractmethod` to define required fixtures:

```python
class BasePaymentFlowTests(ABC):
    @pytest.fixture
    @abstractmethod
    def default_product_id(self) -> str:
        """App MUST provide this."""
        ...
```

IDE shows unimplemented methods. Tests fail clearly if fixture missing.

### 4. Apps Can Override Anything

Any test method can be overridden:

```python
class TestTarotPayments(BasePaymentFlowTests):
    # Skip a test
    @pytest.mark.skip(reason="Not applicable to tarot")
    async def test_something(self): ...

    # Customize a test
    async def test_webhook_idempotency(self, ...):
        # Custom implementation
        ...
```

### 5. Explicit Over Implicit

Every test class is visible in app code. No hidden tests from pytest_plugins.

```
apps/template/tests/
├── contract/
│   └── test_auth.py          # class TestTarotAuth(BaseAuthTests)
├── integration/
│   └── test_payments.py      # class TestTarotPayments(BasePaymentFlowTests)
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              CORE LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  core/testing/                                                           │
│  ├── fixtures/                    Reusable pytest fixtures               │
│  │   ├── database.py              PostgreSQL testcontainer               │
│  │   ├── mocks.py                 Bot, Redis, YooKassa, ARQ mocks        │
│  │   ├── auth.py                  Telegram initData generator            │
│  │   └── redis.py                 In-memory Redis mock                   │
│  │                                                                       │
│  └── base/                        Abstract base test classes             │
│      ├── health.py                BaseHealthTests                        │
│      ├── auth.py                  BaseAuthTests, BaseDeeplinkAuthTests   │
│      ├── payments.py              BasePaymentEndpointTests               │
│      │                            BasePaymentFlowTests                   │
│      ├── subscriptions.py         BaseSubscriptionEndpointTests          │
│      │                            BaseSubscriptionLifecycleTests         │
│      └── stars.py                 BaseTelegramStarsTests                 │
│                                                                          │
│  core/tests/                      Core's OWN tests (fast, isolated)      │
│  ├── business/                    Pure logic (no DB)                     │
│  │   ├── test_streak.py                                                  │
│  │   └── test_password.py                                                │
│  └── smoke/                                                              │
│      └── test_imports.py                                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ inherits / imports
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              APP LAYER                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  apps/{app}/tests/                                                       │
│  ├── conftest.py                  App fixtures (repo, services, client)  │
│  │                                                                       │
│  ├── contract/                    HTTP interface tests                   │
│  │   ├── api/                                                            │
│  │   │   ├── test_health.py       class TestHealth(BaseHealthTests)      │
│  │   │   ├── test_auth.py         class TestAuth(BaseAuthTests)          │
│  │   │   ├── test_payments.py     class TestPayments(BasePaymentTests)   │
│  │   │   └── test_readings.py     App-specific (no base class)           │
│  │   ├── bot/                                                            │
│  │   │   └── test_commands.py                                            │
│  │   └── worker/                                                         │
│  │       └── test_jobs.py                                                │
│  │                                                                       │
│  ├── integration/                 Full flow tests                        │
│  │   ├── test_payment_flows.py    class TestFlows(BasePaymentFlowTests)  │
│  │   ├── test_subscriptions.py    class TestSubs(BaseSubLifecycleTests)  │
│  │   └── test_stars.py            class TestStars(BaseTelegramStarsTests)│
│  │                                                                       │
│  ├── business/                    App-specific business logic            │
│  │   └── test_concurrency.py                                             │
│  │                                                                       │
│  └── regression/                  Bug fix tests                          │
│      └── test_specific_bugs.py                                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

### Core Structure

```
core/backend/src/core/
├── testing/                              # SHARED TEST INFRASTRUCTURE
│   ├── __init__.py
│   │
│   ├── fixtures/                         # Reusable fixtures (apps import)
│   │   ├── __init__.py                   # Exports all fixtures
│   │   ├── database.py                   # postgres_container, db_engine, db_session
│   │   ├── mocks.py                      # mock_bot, mock_yookassa, mock_arq, mock_posthog
│   │   ├── auth.py                       # generate_telegram_init_data
│   │   └── redis.py                      # mock_redis (in-memory implementation)
│   │
│   └── base/                             # Abstract base test classes
│       ├── __init__.py                   # Exports all base classes
│       │
│       ├── health.py                     # BaseHealthTests
│       │                                 #   - test_health_returns_200
│       │                                 #   - test_health_returns_json
│       │
│       ├── auth.py                       # BaseAuthTests
│       │                                 #   - test_logout_returns_200
│       │                                 #   - test_logout_clears_session
│       │                                 # BaseDeeplinkAuthTests
│       │                                 #   - test_start_returns_token
│       │                                 #   - test_poll_requires_token
│       │                                 #   - test_poll_invalid_token_410
│       │
│       ├── payments.py                   # BasePaymentEndpointTests (contract)
│       │                                 #   - test_create_payment_requires_auth
│       │                                 #   - test_create_payment_validates_product
│       │                                 #   - test_create_payment_returns_url
│       │                                 # BasePaymentFlowTests (integration)
│       │                                 #   - test_webhook_idempotency
│       │                                 #   - test_payment_creates_subscription
│       │                                 #   - test_failed_payment_no_subscription
│       │                                 #   - test_payment_links_to_subscription
│       │
│       ├── subscriptions.py              # BaseSubscriptionEndpointTests (contract)
│       │                                 #   - test_get_subscription_requires_auth
│       │                                 #   - test_get_subscription_returns_status
│       │                                 # BaseSubscriptionLifecycleTests (integration)
│       │                                 #   - test_subscription_expires
│       │                                 #   - test_subscription_renewal
│       │                                 #   - test_subscription_cancellation
│       │
│       └── stars.py                      # BaseTelegramStarsTests
│                                         #   - test_stars_invoice_creation
│                                         #   - test_stars_payment_success
│                                         #   - test_stars_refund
│
└── tests/                                # CORE'S OWN TESTS (no app dependencies)
    ├── conftest.py                       # Minimal setup
    ├── business/
    │   ├── test_streak.py                # Streak calculation logic
    │   └── test_password.py              # Password hashing/validation
    └── smoke/
        └── test_imports.py               # Verify core imports work
```

### App Structure (template-react example)

```
apps/template-react/backend/src/app/
└── tests/
    ├── conftest.py                       # APP FIXTURES
    │                                     #   - postgres_container (from core)
    │                                     #   - db_engine (from core)
    │                                     #   - db_session (from core)
    │                                     #   - mock_bot (from core)
    │                                     #   - mock_redis (from core)
    │                                     #   - repo (app-specific)
    │                                     #   - services (app-specific)
    │                                     #   - test_user (app-specific)
    │                                     #   - client (app-specific)
    │                                     #   - authenticated_client (app-specific)
    │
    ├── contract/                         # HTTP CONTRACT TESTS
    │   └── api/
    │       ├── test_health.py            # class TestHealth(BaseHealthTests): pass
    │       ├── test_auth.py              # class TestAuth(BaseAuthTests): pass
    │       ├── test_deeplink.py          # class TestDeeplink(BaseDeeplinkAuthTests): pass
    │       ├── test_payments.py          # class TestPayments(BasePaymentEndpointTests): pass
    │       ├── test_subscriptions.py     # class TestSubs(BaseSubscriptionEndpointTests): pass
    │       └── test_user.py              # App-specific user endpoints
    │
    ├── integration/                      # DEEP FLOW TESTS
    │   ├── test_payment_flows.py         # class TestPaymentFlows(BasePaymentFlowTests):
    │   │                                 #     @pytest.fixture
    │   │                                 #     def default_product_id(self): return "MONTH_SUB_V3"
    │   ├── test_subscriptions.py         # class TestSubLifecycle(BaseSubscriptionLifecycleTests): ...
    │   └── test_stars.py                 # class TestStars(BaseTelegramStarsTests): ...
    │
    ├── business/                         # APP-SPECIFIC BUSINESS LOGIC
    │   └── test_balance_operations.py
    │
    └── regression/                       # BUG FIX TESTS
        └── test_specific_bugs.py
```

---

## Core Components

### 1. Database Fixtures

```python
# core/backend/src/core/testing/fixtures/database.py
"""
Database fixtures for testing.

Provides PostgreSQL testcontainer with transaction-based isolation.
Each test gets a fresh session that auto-rollbacks.

Usage in app conftest.py:
    from core.testing.fixtures.database import (
        postgres_container,
        db_engine,
        db_session,
    )
"""
import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from core.infrastructure.database.models import Base


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Single PostgreSQL container for entire test session.

    Lifecycle:
    1. Container starts once at session begin (~2s)
    2. Shared across ALL tests in session
    3. Destroyed at session end

    Performance: Avoids container startup per test.
    """
    with PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="function")
def db_engine(postgres_container: PostgresContainer) -> Generator[AsyncEngine, None, None]:
    """
    Fresh database engine per test.

    Lifecycle:
    1. Creates async engine from container URL
    2. Creates ALL tables (fresh schema)
    3. Yields engine to test
    4. Disposes engine after test

    Isolation: Each test gets fresh tables.
    Performance: ~150ms overhead per test.
    """
    # Convert psycopg2 URL to asyncpg
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg")

    engine = create_async_engine(async_url, echo=False, pool_pre_ping=True)

    # Create tables synchronously (pytest fixtures can't be async at module level)
    async def create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(create_tables())

    yield engine

    # Cleanup
    asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Fresh session per test with auto-rollback.

    Lifecycle:
    1. Creates session from engine
    2. Begins transaction
    3. Yields session to test
    4. Rolls back transaction (auto-cleanup)

    Isolation: All test changes are rolled back.
    Performance: Instant cleanup via rollback.

    Usage:
        async def test_something(db_session):
            user = User(name="test")
            db_session.add(user)
            await db_session.flush()  # Use flush(), not commit()
            # Transaction rolls back automatically after test
    """
    async_session_factory = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        async with session.begin():
            yield session
            # Transaction rolls back on context exit (no commit called)
```

### 2. Mock Fixtures

```python
# core/backend/src/core/testing/fixtures/mocks.py
"""
Mock fixtures for external services.

All mocks use AsyncMock for async methods to avoid
"MagicMock can't be awaited" errors.

Usage in app conftest.py:
    from core.testing.fixtures.mocks import (
        mock_bot,
        mock_yookassa,
        mock_arq,
        mock_posthog,
    )
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_bot() -> MagicMock:
    """
    Mock Telegram Bot API.

    Mocks all async methods that the app calls:
    - send_message
    - send_photo
    - create_invoice_link
    - answer_callback_query
    - answer_pre_checkout_query

    Returns MagicMock with AsyncMock methods.
    """
    bot = MagicMock()

    # Message sending
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=12345))
    bot.send_photo = AsyncMock(return_value=MagicMock(message_id=12346))
    bot.edit_message_text = AsyncMock(return_value=True)
    bot.delete_message = AsyncMock(return_value=True)

    # Payments
    bot.create_invoice_link = AsyncMock(return_value="https://t.me/invoice/test_123")
    bot.answer_pre_checkout_query = AsyncMock(return_value=True)

    # Callbacks
    bot.answer_callback_query = AsyncMock(return_value=True)

    # User info
    bot.get_chat = AsyncMock(return_value=MagicMock(
        id=123456789,
        username="testuser",
        first_name="Test",
    ))

    return bot


@pytest.fixture
def mock_yookassa(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Mock YooKassa payment provider.

    Patches yookassa.Payment.create to return mock payment objects.
    Each call returns a unique payment ID.

    Usage:
        def test_payment(mock_yookassa):
            # YooKassa is automatically mocked
            payment = await services.payments.create_yookassa_payment(...)
            assert "yookassa_test_" in payment.provider_payment_id
    """
    payment_counter = [0]

    def mock_create(**kwargs: dict) -> MagicMock:
        payment_counter[0] += 1
        payment_id = f"yookassa_test_{payment_counter[0]}"

        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.status = "pending"
        mock_payment.paid = False
        mock_payment.amount = MagicMock(
            value=kwargs.get("amount", {}).get("value", "299.00"),
            currency=kwargs.get("amount", {}).get("currency", "RUB"),
        )
        mock_payment.confirmation = MagicMock(
            type="redirect",
            confirmation_url=f"https://yookassa.ru/pay/{payment_id}",
        )
        mock_payment.metadata = kwargs.get("metadata", {})

        return mock_payment

    def mock_find_one(payment_id: str) -> MagicMock:
        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.status = "succeeded"
        mock_payment.paid = True
        return mock_payment

    monkeypatch.setattr("yookassa.Payment.create", mock_create)
    monkeypatch.setattr("yookassa.Payment.find_one", mock_find_one)

    return mock_create


@pytest.fixture
def mock_arq() -> AsyncMock:
    """
    Mock ARQ background job queue.

    Returns AsyncMock that captures enqueued jobs for assertions.

    Usage:
        def test_job_enqueued(mock_arq):
            await services.notifications.send_async(user_id, message)
            mock_arq.enqueue_job.assert_called_once_with(
                "send_notification",
                user_id,
                message,
            )
    """
    arq = AsyncMock()
    arq.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test_job_123"))
    return arq


@pytest.fixture
def mock_posthog(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """
    Mock PostHog analytics.

    Captures all analytics events for assertions.

    Usage:
        def test_event_tracked(mock_posthog):
            await services.analytics.track("button_clicked", {"button": "subscribe"})
            assert mock_posthog[0]["event"] == "button_clicked"
    """
    captured_events: list[dict] = []

    def mock_capture(
        distinct_id: str,
        event: str,
        properties: dict | None = None,
    ) -> None:
        captured_events.append({
            "distinct_id": distinct_id,
            "event": event,
            "properties": properties or {},
        })

    monkeypatch.setattr("posthog.capture", mock_capture)

    return captured_events
```

### 3. Auth Helpers

```python
# core/backend/src/core/testing/fixtures/auth.py
"""
Authentication helpers for testing.

Generates valid Telegram initData with proper HMAC signatures
that pass TelegramAuthenticator validation.

Usage:
    from core.testing.fixtures.auth import generate_telegram_init_data

    init_data = generate_telegram_init_data(
        user_id=123456789,
        username="testuser",
        bot_token=settings.bot.token,
    )
    client.headers["initData"] = init_data
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode


def generate_telegram_init_data(
    user_id: int,
    username: str,
    first_name: str = "Test",
    last_name: str | None = None,
    language_code: str = "en",
    is_premium: bool = False,
    bot_token: str = "test_token",
    auth_date: int | None = None,
    start_param: str | None = None,
) -> str:
    """
    Generate valid Telegram Mini App initData with HMAC signature.

    Creates properly signed initData that passes TelegramAuthenticator
    validation in both development and test environments.

    Args:
        user_id: Telegram user ID (must match test_user.telegram_id)
        username: Telegram username
        first_name: User's first name
        last_name: User's last name (optional)
        language_code: ISO 639-1 language code
        is_premium: Telegram Premium status
        bot_token: Bot token for HMAC signing (from settings.bot.token)
        auth_date: Unix timestamp (defaults to current time)
        start_param: Deep link start parameter (optional)

    Returns:
        URL-encoded initData string with valid hash signature.

    Example:
        >>> init_data = generate_telegram_init_data(
        ...     user_id=123456789,
        ...     username="john_doe",
        ...     bot_token="123:ABC",
        ... )
        >>> # Returns: "user=%7B%22id%22%3A123456789...&hash=abc123..."
    """
    if auth_date is None:
        auth_date = int(time.time())

    # Build user object
    user_data: dict = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "language_code": language_code,
    }
    if last_name:
        user_data["last_name"] = last_name
    if is_premium:
        user_data["is_premium"] = True

    # Build data dict (will be sorted alphabetically for signing)
    data: dict[str, str] = {
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(auth_date),
        "query_id": f"test_query_{user_id}_{auth_date}",
    }

    if start_param:
        data["start_param"] = start_param

    # Create data_check_string (alphabetically sorted, newline-separated)
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items())
    )

    # Generate HMAC-SHA256 hash
    # Step 1: Create secret key from bot token
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # Step 2: Sign the data_check_string
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Add hash to data
    data["hash"] = hash_value

    return urlencode(data)


def generate_expired_init_data(
    user_id: int,
    username: str,
    bot_token: str = "test_token",
    hours_ago: int = 25,
) -> str:
    """
    Generate expired initData for testing auth expiration.

    Args:
        user_id: Telegram user ID
        username: Telegram username
        bot_token: Bot token for signing
        hours_ago: How many hours in the past (default 25, expires at 24)

    Returns:
        Valid but expired initData string.
    """
    expired_time = int(time.time()) - (hours_ago * 3600)
    return generate_telegram_init_data(
        user_id=user_id,
        username=username,
        bot_token=bot_token,
        auth_date=expired_time,
    )
```

### 4. Base Test Classes

#### Health Tests

```python
# core/backend/src/core/testing/base/health.py
"""
Base test class for health endpoints.

All apps should have a /health endpoint that returns status.
"""
import pytest
from httpx import AsyncClient


class BaseHealthTests:
    """
    Health endpoint contract tests.

    Required fixtures (from app conftest.py):
    - client: AsyncClient configured for the app

    Tests:
    - test_health_returns_200: Endpoint responds
    - test_health_returns_json: Response has correct format
    """

    @pytest.mark.contract
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        """GET /health returns 200 OK."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.contract
    async def test_health_returns_json(self, client: AsyncClient) -> None:
        """GET /health returns JSON with status field."""
        response = await client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ("ok", "healthy")
```

#### Auth Tests

```python
# core/backend/src/core/testing/base/auth.py
"""
Base test classes for authentication endpoints.
"""
import pytest
from httpx import AsyncClient


class BaseAuthTests:
    """
    Auth endpoint contract tests.

    Required fixtures:
    - client: AsyncClient
    - authenticated_client: AsyncClient with valid auth
    """

    @pytest.mark.contract
    async def test_logout_returns_200(self, client: AsyncClient) -> None:
        """POST /auth/logout returns 200."""
        response = await client.post("/auth/logout")
        assert response.status_code == 200

    @pytest.mark.contract
    async def test_logout_response_format(self, client: AsyncClient) -> None:
        """Logout response contains message field."""
        response = await client.post("/auth/logout")
        data = response.json()
        assert "message" in data

    @pytest.mark.contract
    async def test_me_requires_auth(self, client: AsyncClient) -> None:
        """GET /auth/me without auth returns 401."""
        response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.contract
    async def test_me_returns_user(self, authenticated_client: AsyncClient) -> None:
        """GET /auth/me with auth returns user data."""
        response = await authenticated_client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "telegram_id" in data


class BaseDeeplinkAuthTests:
    """
    Telegram deeplink authentication contract tests.

    Required fixtures:
    - client: AsyncClient
    - mock_redis: In-memory Redis mock
    """

    @pytest.mark.contract
    async def test_start_returns_token(self, client: AsyncClient) -> None:
        """POST /auth/login/telegram/deeplink/start returns token."""
        response = await client.post("/auth/login/telegram/deeplink/start")

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "bot_url" in data
        assert "expires_in" in data
        assert len(data["token"]) >= 20

    @pytest.mark.contract
    async def test_poll_requires_token(self, client: AsyncClient) -> None:
        """GET /auth/login/telegram/deeplink/poll requires token param."""
        response = await client.get("/auth/login/telegram/deeplink/poll")
        assert response.status_code == 422

    @pytest.mark.contract
    async def test_poll_invalid_token_returns_410(self, client: AsyncClient) -> None:
        """Invalid/expired token returns 410 Gone."""
        response = await client.get(
            "/auth/login/telegram/deeplink/poll",
            params={"token": "invalid_nonexistent_token"},
        )
        assert response.status_code == 410
```

#### Payment Tests

```python
# core/backend/src/core/testing/base/payments.py
"""
Base test classes for payment functionality.

Includes both contract tests (HTTP interface) and integration tests (full flows).
"""
from abc import ABC, abstractmethod
from typing import Any

import pytest
from httpx import AsyncClient

from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus


class BasePaymentEndpointTests:
    """
    Payment endpoint contract tests (shallow).

    Required fixtures:
    - client: AsyncClient
    - authenticated_client: AsyncClient with valid auth
    """

    @pytest.mark.contract
    async def test_create_payment_requires_auth(self, client: AsyncClient) -> None:
        """POST /payments requires authentication."""
        response = await client.post("/payments", json={
            "product_id": "MONTH_SUB_V3",
            "provider": "YOOKASSA",
        })
        assert response.status_code == 401

    @pytest.mark.contract
    async def test_create_payment_validates_product(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Invalid product_id returns 400."""
        response = await authenticated_client.post("/payments", json={
            "product_id": "INVALID_PRODUCT",
            "provider": "YOOKASSA",
        })
        assert response.status_code == 400

    @pytest.mark.contract
    async def test_create_payment_returns_url(
        self,
        authenticated_client: AsyncClient,
        mock_yookassa: Any,
    ) -> None:
        """Valid payment request returns payment URL."""
        response = await authenticated_client.post("/payments", json={
            "product_id": "MONTH_SUB_V3",
            "provider": "YOOKASSA",
        })
        assert response.status_code == 200
        data = response.json()
        assert "payment_url" in data
        assert data["payment_url"].startswith("http")

    @pytest.mark.contract
    async def test_payment_history_requires_auth(self, client: AsyncClient) -> None:
        """GET /payments requires authentication."""
        response = await client.get("/payments")
        assert response.status_code == 401

    @pytest.mark.contract
    async def test_payment_history_returns_list(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """GET /payments returns list of payments."""
        response = await authenticated_client.get("/payments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class BasePaymentFlowTests(ABC):
    """
    Payment flow integration tests (deep).

    Tests REAL payment flows through the full stack:
    Payment creation → Webhook → Subscription → Database

    Required fixtures (app MUST provide):
    - services: App's RequestsService (REAL, not mocked)
    - repo: App's RequestsRepo (REAL, not mocked)
    - test_user: User created in database
    - mock_yookassa: Mocked YooKassa provider

    Abstract fixtures (app MUST implement):
    - default_product_id: App's subscription product ID
    """

    # =========================================================================
    # ABSTRACT FIXTURES - Apps MUST implement
    # =========================================================================

    @pytest.fixture
    @abstractmethod
    def default_product_id(self) -> str:
        """
        App's default subscription product ID.

        Example implementation:
            @pytest.fixture
            def default_product_id(self) -> str:
                return "MONTH_SUB_V3"
        """
        ...

    # =========================================================================
    # INTEGRATION TESTS
    # =========================================================================

    @pytest.mark.integration
    async def test_webhook_idempotency(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
        mock_yookassa: Any,
    ) -> None:
        """
        Same webhook sent twice should be idempotent.

        Business Rule:
            One payment = one subscription, even with webhook retries.

        Bug Prevention:
            Network retries could create duplicate subscriptions without
            proper idempotency handling.

        Test Flow:
            1. Create payment record
            2. Process webhook (simulating payment success)
            3. Process SAME webhook again (simulating network retry)
            4. Verify only ONE subscription exists
        """
        # Arrange: Create payment
        payment = await repo.payments.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "provider_id": PaymentProvider.YOOKASSA,
            "provider_payment_id": f"test_idempotent_{test_user.telegram_id}",
            "amount": 299.00,
            "currency": "RUB",
            "status": PaymentStatus.CREATED,
        })
        await repo.session.flush()

        webhook_payload = self._build_yookassa_webhook(payment, "payment.succeeded")

        # Act: Process webhook twice (simulating network retry)
        await services.payments.process_callback(
            webhook_payload,
            provider_id=PaymentProvider.YOOKASSA,
        )
        count_after_first = len(
            await repo.subscriptions.get_by_user_id(test_user.id)
        )

        await services.payments.process_callback(
            webhook_payload,
            provider_id=PaymentProvider.YOOKASSA,
        )
        count_after_second = len(
            await repo.subscriptions.get_by_user_id(test_user.id)
        )

        # Assert: Idempotent - same subscription count
        assert count_after_second == count_after_first == 1

    @pytest.mark.integration
    async def test_payment_creates_subscription(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
        mock_yookassa: Any,
    ) -> None:
        """
        Successful payment creates active subscription.

        Test Flow:
            1. Create payment record
            2. Process success webhook
            3. Verify subscription exists and is active
            4. Verify payment is linked to subscription
        """
        # Arrange
        payment = await repo.payments.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "provider_id": PaymentProvider.YOOKASSA,
            "provider_payment_id": f"test_creates_sub_{test_user.telegram_id}",
            "amount": 299.00,
            "currency": "RUB",
            "status": PaymentStatus.CREATED,
        })
        await repo.session.flush()

        webhook_payload = self._build_yookassa_webhook(payment, "payment.succeeded")

        # Act
        await services.payments.process_callback(
            webhook_payload,
            provider_id=PaymentProvider.YOOKASSA,
        )

        # Assert: Subscription created
        subscription = await repo.subscriptions.get_active_by_user_id(test_user.id)
        assert subscription is not None
        assert subscription.product_id == default_product_id

        # Assert: Payment linked to subscription
        updated_payment = await repo.payments.get_by_id(payment.id)
        assert updated_payment.subscription_id == subscription.id
        assert updated_payment.status == PaymentStatus.SUCCEEDED

    @pytest.mark.integration
    async def test_failed_payment_no_subscription(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
        mock_yookassa: Any,
    ) -> None:
        """
        Failed/canceled payment should NOT create subscription.

        Test Flow:
            1. Create payment record
            2. Process canceled webhook
            3. Verify NO subscription exists
            4. Verify payment status is FAILED
        """
        # Arrange
        payment = await repo.payments.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "provider_id": PaymentProvider.YOOKASSA,
            "provider_payment_id": f"test_fails_{test_user.telegram_id}",
            "amount": 299.00,
            "currency": "RUB",
            "status": PaymentStatus.CREATED,
        })
        await repo.session.flush()

        webhook_payload = self._build_yookassa_webhook(payment, "payment.canceled")

        # Act
        await services.payments.process_callback(
            webhook_payload,
            provider_id=PaymentProvider.YOOKASSA,
        )

        # Assert: NO subscription
        subscription = await repo.subscriptions.get_active_by_user_id(test_user.id)
        assert subscription is None

        # Assert: Payment marked as failed
        updated_payment = await repo.payments.get_by_id(payment.id)
        assert updated_payment.status == PaymentStatus.FAILED

    @pytest.mark.integration
    async def test_payment_links_to_subscription(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
        mock_yookassa: Any,
    ) -> None:
        """
        Payment record should link to created subscription.

        This enables:
            - Payment history with subscription details
            - Refund processing
            - Subscription renewal tracking
        """
        # Arrange
        payment = await repo.payments.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "provider_id": PaymentProvider.YOOKASSA,
            "provider_payment_id": f"test_links_{test_user.telegram_id}",
            "amount": 299.00,
            "currency": "RUB",
            "status": PaymentStatus.CREATED,
        })
        await repo.session.flush()

        webhook_payload = self._build_yookassa_webhook(payment, "payment.succeeded")

        # Act
        await services.payments.process_callback(
            webhook_payload,
            provider_id=PaymentProvider.YOOKASSA,
        )

        # Assert
        updated_payment = await repo.payments.get_by_id(payment.id)
        assert updated_payment.subscription_id is not None

        subscription = await repo.subscriptions.get_by_id(
            updated_payment.subscription_id
        )
        assert subscription is not None
        assert subscription.user_id == test_user.id

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _build_yookassa_webhook(
        self,
        payment: Any,
        event: str,
    ) -> dict:
        """
        Build YooKassa webhook payload.

        Args:
            payment: Payment model instance
            event: Webhook event type (payment.succeeded, payment.canceled)

        Returns:
            Dict matching YooKassa webhook format.
        """
        status = "succeeded" if "succeeded" in event else "canceled"
        return {
            "type": "notification",
            "event": event,
            "object": {
                "id": payment.provider_payment_id,
                "status": status,
                "paid": status == "succeeded",
                "amount": {
                    "value": str(payment.amount),
                    "currency": payment.currency,
                },
                "metadata": {
                    "app_payment_id": str(payment.id),
                },
                "payment_method": {
                    "type": "bank_card",
                    "id": "pm_test_123",
                    "saved": False,
                },
            },
        }
```

#### Subscription Tests

```python
# core/backend/src/core/testing/base/subscriptions.py
"""
Base test classes for subscription functionality.
"""
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from core.infrastructure.database.models.enums import SubscriptionStatus


class BaseSubscriptionEndpointTests:
    """
    Subscription endpoint contract tests (shallow).

    Required fixtures:
    - client: AsyncClient
    - authenticated_client: AsyncClient with valid auth
    """

    @pytest.mark.contract
    async def test_get_subscription_requires_auth(self, client: AsyncClient) -> None:
        """GET /subscriptions/current requires authentication."""
        response = await client.get("/subscriptions/current")
        assert response.status_code == 401

    @pytest.mark.contract
    async def test_get_subscription_returns_status(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """GET /subscriptions/current returns subscription status."""
        response = await authenticated_client.get("/subscriptions/current")
        assert response.status_code == 200
        data = response.json()
        # Either has subscription or null
        assert "subscription" in data or data is None

    @pytest.mark.contract
    async def test_subscription_products_public(self, client: AsyncClient) -> None:
        """GET /subscriptions/products is public."""
        response = await client.get("/subscriptions/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class BaseSubscriptionLifecycleTests(ABC):
    """
    Subscription lifecycle integration tests (deep).

    Tests subscription state transitions:
    - Creation from payment
    - Expiration
    - Renewal
    - Cancellation

    Required fixtures:
    - services: App's RequestsService
    - repo: App's RequestsRepo
    - test_user: User in database
    """

    @pytest.fixture
    @abstractmethod
    def default_product_id(self) -> str:
        """App's default subscription product ID."""
        ...

    @pytest.mark.integration
    async def test_subscription_expires_after_end_date(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
    ) -> None:
        """
        Subscription should be marked expired after end_date.

        Business Rule:
            Subscriptions are valid until end_date, then expire.
        """
        # Arrange: Create expired subscription
        expired_date = datetime.now(UTC) - timedelta(days=1)
        subscription = await repo.subscriptions.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "status": SubscriptionStatus.ACTIVE,
            "start_date": expired_date - timedelta(days=30),
            "end_date": expired_date,
        })
        await repo.session.flush()

        # Act: Check subscription status
        active_sub = await repo.subscriptions.get_active_by_user_id(test_user.id)

        # Assert: No active subscription (expired)
        assert active_sub is None

    @pytest.mark.integration
    async def test_subscription_renewal_extends_end_date(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
    ) -> None:
        """
        Renewing subscription should extend end_date.

        Business Rule:
            Renewal adds duration to current end_date (or now if expired).
        """
        # Arrange: Create active subscription
        now = datetime.now(UTC)
        original_end = now + timedelta(days=5)

        subscription = await repo.subscriptions.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "status": SubscriptionStatus.ACTIVE,
            "start_date": now - timedelta(days=25),
            "end_date": original_end,
        })
        await repo.session.flush()

        # Act: Renew subscription (simulating second payment)
        await services.subscriptions.extend_subscription(
            user_id=test_user.id,
            product_id=default_product_id,
            days=30,
        )

        # Assert: End date extended
        updated_sub = await repo.subscriptions.get_by_id(subscription.id)
        expected_end = original_end + timedelta(days=30)
        assert updated_sub.end_date >= expected_end - timedelta(seconds=1)
        assert updated_sub.end_date <= expected_end + timedelta(seconds=1)

    @pytest.mark.integration
    async def test_subscription_cancellation(
        self,
        services: Any,
        repo: Any,
        test_user: Any,
        default_product_id: str,
    ) -> None:
        """
        Cancelled subscription should remain active until end_date.

        Business Rule:
            Cancellation stops auto-renewal but doesn't revoke access.
        """
        # Arrange: Create active subscription
        now = datetime.now(UTC)
        subscription = await repo.subscriptions.create({
            "user_id": test_user.id,
            "product_id": default_product_id,
            "status": SubscriptionStatus.ACTIVE,
            "start_date": now,
            "end_date": now + timedelta(days=30),
            "auto_renew": True,
        })
        await repo.session.flush()

        # Act: Cancel subscription
        await services.subscriptions.cancel_subscription(
            user_id=test_user.id,
            subscription_id=subscription.id,
        )

        # Assert: Status changed, but still accessible until end_date
        updated_sub = await repo.subscriptions.get_by_id(subscription.id)
        assert updated_sub.status == SubscriptionStatus.CANCELLED
        assert updated_sub.auto_renew is False

        # Still counts as "active" until end_date
        active_sub = await repo.subscriptions.get_active_by_user_id(test_user.id)
        assert active_sub is not None
```

---

## App Implementation

### App conftest.py

```python
# apps/template-react/backend/src/app/tests/conftest.py
"""
Template-React test configuration.

Provides all fixtures needed for both contract and integration tests.
Tests inherit from core base classes and use these fixtures.
"""
import os
import random
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# ============================================================================
# ENVIRONMENT SETUP (must be before app imports)
# ============================================================================
os.environ["WEB__API_ROOT_PATH"] = ""
os.environ["BOT__TOKEN"] = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789"

# ============================================================================
# CORE FIXTURES (imported from core/testing)
# ============================================================================
from core.testing.fixtures.database import (
    db_engine,
    db_session,
    postgres_container,
)
from core.testing.fixtures.mocks import (
    mock_arq,
    mock_bot,
    mock_posthog,
    mock_yookassa,
)
from core.testing.fixtures.auth import generate_telegram_init_data
from core.testing.fixtures.redis import mock_redis

# ============================================================================
# APP IMPORTS
# ============================================================================
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService


# ============================================================================
# APP-SPECIFIC FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def repo(db_session: AsyncSession) -> RequestsRepo:
    """
    REAL RequestsRepo with REAL database session.

    This tests the actual composition:
    - RequestsRepo._core = CoreRequestsRepo(session)
    - All delegated repos (users, payments, subscriptions) work
    - App-specific repos (balance) work
    """
    return RequestsRepo(db_session)


@pytest_asyncio.fixture
async def services(
    repo: RequestsRepo,
    mock_bot: Any,
    mock_redis: Any,
    mock_arq: Any,
) -> RequestsService:
    """
    REAL RequestsService with REAL repo, mocked externals.

    This tests the actual composition:
    - RequestsService._core = CoreRequestsService(repo._core, products)
    - All delegated services work
    - External dependencies are mocked
    """
    return RequestsService(
        repo=repo,
        bot=mock_bot,
        redis=mock_redis,
        arq=mock_arq,
        producer=None,
    )


@pytest_asyncio.fixture
async def test_user(repo: RequestsRepo) -> Any:
    """
    Create REAL test user in database.

    Uses random telegram_id for parallel test safety.
    Each test gets a unique user that doesn't conflict.
    """
    user = await repo.users.get_or_create_user({
        "telegram_id": random.randint(100_000_000, 999_999_999),
        "username": f"test_{uuid4().hex[:8]}",
        "display_name": "Test User",
        "tg_first_name": "Test",
        "tg_username": f"test_{uuid4().hex[:8]}",
        "tg_language_code": "en",
    })
    await repo.session.flush()
    return user


@pytest.fixture
def default_product_id() -> str:
    """
    Default subscription product for tests.

    Used by integration tests that need a product_id.
    Override in test class if different product needed.
    """
    return "MONTH_SUB_V3"


# ============================================================================
# HTTP CLIENT FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def client(
    db_engine: AsyncEngine,
    mock_bot: Any,
    mock_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncClient:
    """
    HTTP client with REAL database, mocked externals.

    Creates FastAPI test client with:
    - Real database (from testcontainer)
    - Real RequestsRepo/RequestsService (tests composition)
    - Mocked external services (Redis, Bot, etc.)
    """
    from fastapi import Depends

    import app.webhook.auth as auth_module
    from app.webhook.app import app
    from app.webhook.dependencies.service import get_services
    from app.webhook.dependencies.bot import get_bot
    from app.webhook.dependencies.redis import get_redis_client
    from app.infrastructure.database.setup import create_session_pool
    from core.infrastructure.fastapi import dependencies as core_deps
    from core.infrastructure.auth.telegram import (
        TelegramAuthenticator,
        generate_secret_key,
    )
    from core.infrastructure.config import settings

    # Mock global Redis in auth module
    monkeypatch.setattr(auth_module, "session_redis", mock_redis)

    # Configure Telegram auth
    telegram_secret = generate_secret_key(settings.bot.token)
    app.state.telegram_auth = TelegramAuthenticator(secret=telegram_secret)

    # Create session pool from test engine
    test_session_pool = create_session_pool(db_engine)

    async def override_redis():
        yield mock_redis

    async def override_bot():
        yield mock_bot

    async def override_services():
        """REAL RequestsService with test database."""
        async with test_session_pool() as session:
            async with session.begin():
                repo = RequestsRepo(session)
                yield RequestsService(
                    repo=repo,
                    redis=mock_redis,
                    bot=mock_bot,
                    arq=None,
                    producer=None,
                )

    # Apply dependency overrides
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_bot] = override_bot
    app.dependency_overrides[get_services] = override_services
    app.dependency_overrides[core_deps.get_services] = override_services

    try:
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                yield c
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient,
    test_user: Any,
) -> AsyncClient:
    """
    HTTP client with valid Telegram authentication.

    Generates proper initData with HMAC signature that passes
    TelegramAuthenticator validation.
    """
    from core.infrastructure.config import settings

    init_data = generate_telegram_init_data(
        user_id=test_user.telegram_id,
        username=test_user.username or f"test_{uuid4().hex[:8]}",
        first_name=test_user.tg_first_name or "Test",
        bot_token=settings.bot.token,
    )

    # Add auth header
    client.headers["initData"] = init_data

    return client


# ============================================================================
# TEST ISOLATION FIXTURES
# ============================================================================

@pytest_asyncio.fixture(autouse=True)
async def reset_demo_counters() -> None:
    """Reset demo counters between tests for isolation."""
    from app.webhook.routers.demo import _counters

    _counters.clear()
    yield
    _counters.clear()
```

### Contract Tests

```python
# apps/template-react/backend/src/app/tests/contract/api/test_health.py
"""
Health endpoint contract tests.

Inherits all tests from BaseHealthTests.
Uses client fixture from conftest.py.
"""
from core.testing.base.health import BaseHealthTests


class TestHealth(BaseHealthTests):
    """
    Template-React health tests.

    Inherited tests:
    - test_health_returns_200
    - test_health_returns_json

    No customization needed - just inherit.
    """

    pass
```

```python
# apps/template-react/backend/src/app/tests/contract/api/test_auth.py
"""
Auth endpoint contract tests.
"""
from core.testing.base.auth import BaseAuthTests, BaseDeeplinkAuthTests


class TestAuth(BaseAuthTests):
    """
    Template-React auth tests.

    Inherited tests:
    - test_logout_returns_200
    - test_logout_response_format
    - test_me_requires_auth
    - test_me_returns_user
    """

    pass


class TestDeeplinkAuth(BaseDeeplinkAuthTests):
    """
    Template-React deeplink auth tests.

    Inherited tests:
    - test_start_returns_token
    - test_poll_requires_token
    - test_poll_invalid_token_returns_410
    """

    pass
```

```python
# apps/template-react/backend/src/app/tests/contract/api/test_payments.py
"""
Payment endpoint contract tests.
"""
from core.testing.base.payments import BasePaymentEndpointTests


class TestPaymentEndpoints(BasePaymentEndpointTests):
    """
    Template-React payment endpoint tests.

    Inherited tests:
    - test_create_payment_requires_auth
    - test_create_payment_validates_product
    - test_create_payment_returns_url
    - test_payment_history_requires_auth
    - test_payment_history_returns_list
    """

    pass
```

```python
# apps/template-react/backend/src/app/tests/contract/api/test_subscriptions.py
"""
Subscription endpoint contract tests.
"""
from core.testing.base.subscriptions import BaseSubscriptionEndpointTests


class TestSubscriptionEndpoints(BaseSubscriptionEndpointTests):
    """
    Template-React subscription endpoint tests.

    Inherited tests:
    - test_get_subscription_requires_auth
    - test_get_subscription_returns_status
    - test_subscription_products_public
    """

    pass
```

### Integration Tests

```python
# apps/template-react/backend/src/app/tests/integration/test_payment_flows.py
"""
Payment flow integration tests.

Tests full payment flows: payment → webhook → subscription → database.
"""
import pytest

from core.testing.base.payments import BasePaymentFlowTests


class TestPaymentFlows(BasePaymentFlowTests):
    """
    Template-React payment flow tests.

    Inherited tests:
    - test_webhook_idempotency
    - test_payment_creates_subscription
    - test_failed_payment_no_subscription
    - test_payment_links_to_subscription

    Fixtures from conftest.py:
    - services: REAL RequestsService
    - repo: REAL RequestsRepo
    - test_user: REAL user in database
    - mock_yookassa: Mocked YooKassa
    """

    @pytest.fixture
    def default_product_id(self) -> str:
        """Template-React's default subscription product."""
        return "MONTH_SUB_V3"

    # No app-specific tests needed for template-react
    # (it has no special payment logic beyond core)
```

```python
# apps/template-react/backend/src/app/tests/integration/test_subscriptions.py
"""
Subscription lifecycle integration tests.
"""
import pytest

from core.testing.base.subscriptions import BaseSubscriptionLifecycleTests


class TestSubscriptionLifecycle(BaseSubscriptionLifecycleTests):
    """
    Template-React subscription lifecycle tests.

    Inherited tests:
    - test_subscription_expires_after_end_date
    - test_subscription_renewal_extends_end_date
    - test_subscription_cancellation
    """

    @pytest.fixture
    def default_product_id(self) -> str:
        return "MONTH_SUB_V3"
```

### App-Specific Tests

```python
# apps/template-react/backend/src/app/tests/contract/api/test_user.py
"""
User endpoint tests - app-specific (no base class).

Template-React specific user endpoints that don't exist in core.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestUserEndpoints:
    """User-specific endpoint tests."""

    async def test_get_profile_requires_auth(self, client: AsyncClient) -> None:
        """GET /users/profile requires authentication."""
        response = await client.get("/users/profile")
        assert response.status_code == 401

    async def test_get_profile_returns_user_data(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """GET /users/profile returns full user profile."""
        response = await authenticated_client.get("/users/profile")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "balance" in data

    async def test_update_profile(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """PATCH /users/profile updates user data."""
        response = await authenticated_client.patch("/users/profile", json={
            "display_name": "New Name",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "New Name"
```

---

## Test Execution Flow

```
make test APP=template-react
│
├── pytest discovers apps/template-react/tests/
│
├── conftest.py loads:
│   ├── Core fixtures (postgres_container, db_engine, db_session, mocks)
│   └── App fixtures (repo, services, test_user, client, authenticated_client)
│
├── CONTRACT TESTS (tests/contract/)
│   │
│   ├── test_health.py
│   │   └── class TestHealth(BaseHealthTests)
│   │       ├── test_health_returns_200(client)
│   │       │   └── client fixture → REAL app with test DB
│   │       └── test_health_returns_json(client)
│   │
│   ├── test_auth.py
│   │   ├── class TestAuth(BaseAuthTests)
│   │   │   ├── test_logout_returns_200(client)
│   │   │   ├── test_me_requires_auth(client)
│   │   │   └── test_me_returns_user(authenticated_client)
│   │   └── class TestDeeplinkAuth(BaseDeeplinkAuthTests)
│   │       └── ...
│   │
│   └── test_payments.py
│       └── class TestPaymentEndpoints(BasePaymentEndpointTests)
│           └── ...
│
├── INTEGRATION TESTS (tests/integration/)
│   │
│   ├── test_payment_flows.py
│   │   └── class TestPaymentFlows(BasePaymentFlowTests)
│   │       ├── test_webhook_idempotency(services, repo, test_user, mock_yookassa)
│   │       │   ├── services fixture → REAL RequestsService
│   │       │   ├── repo fixture → REAL RequestsRepo
│   │       │   ├── test_user fixture → REAL user in DB
│   │       │   └── Tests REAL composition pattern
│   │       ├── test_payment_creates_subscription(...)
│   │       └── test_failed_payment_no_subscription(...)
│   │
│   └── test_subscriptions.py
│       └── class TestSubscriptionLifecycle(BaseSubscriptionLifecycleTests)
│           └── ...
│
└── APP-SPECIFIC TESTS (tests/contract/api/test_user.py)
    └── class TestUserEndpoints
        └── test_get_profile_requires_auth(client)
```

---

## Fixture Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SESSION SCOPE                                    │
│                                                                         │
│    ┌─────────────────────┐                                              │
│    │  postgres_container │  Single container for all tests (~2s start) │
│    └──────────┬──────────┘                                              │
│               │                                                         │
└───────────────┼─────────────────────────────────────────────────────────┘
                │
┌───────────────┼─────────────────────────────────────────────────────────┐
│               │           FUNCTION SCOPE                                │
│               ▼                                                         │
│    ┌──────────────────┐                                                 │
│    │    db_engine     │  Fresh engine per test (~150ms)                │
│    └────────┬─────────┘                                                 │
│             │                                                           │
│             ▼                                                           │
│    ┌──────────────────┐                                                 │
│    │   db_session     │  Auto-rollback transaction                     │
│    └────────┬─────────┘                                                 │
│             │                                                           │
│    ┌────────┴──────────────────────────────────────────┐               │
│    │                                                    │               │
│    ▼                                                    ▼               │
│ ┌──────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐                  │
│ │ repo │  │ mock_bot │  │mock_redis│  │ mock_arq    │                  │
│ └──┬───┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘                  │
│    │           │             │               │                          │
│    └───────────┴─────────────┴───────────────┘                          │
│                        │                                                │
│                        ▼                                                │
│              ┌──────────────────┐                                       │
│              │     services     │  REAL RequestsService                │
│              └────────┬─────────┘                                       │
│                       │                                                 │
│         ┌─────────────┼─────────────┐                                   │
│         │             │             │                                   │
│         ▼             ▼             ▼                                   │
│    ┌──────────┐ ┌──────────┐ ┌─────────────────┐                       │
│    │test_user │ │  client  │ │default_product_id│                      │
│    └────┬─────┘ └────┬─────┘ └─────────────────┘                       │
│         │            │                                                  │
│         └─────┬──────┘                                                  │
│               │                                                         │
│               ▼                                                         │
│    ┌─────────────────────┐                                              │
│    │authenticated_client │                                              │
│    └─────────────────────┘                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Common Patterns

### Pattern 1: Skip a Test for Specific App

```python
class TestTarotPayments(BasePaymentFlowTests):
    @pytest.mark.skip(reason="Tarot uses different webhook format")
    async def test_webhook_idempotency(self, **kwargs):
        pass

    # Or skip conditionally
    @pytest.mark.skipif(
        condition=True,
        reason="Feature not implemented yet",
    )
    async def test_some_feature(self, **kwargs):
        pass
```

### Pattern 2: Override a Test with Custom Logic

```python
class TestTarotPayments(BasePaymentFlowTests):
    @pytest.mark.integration
    async def test_payment_creates_subscription(
        self,
        services,
        repo,
        test_user,
        default_product_id,
        mock_yookassa,
    ):
        """Override with tarot-specific assertions."""
        # Call parent implementation
        await super().test_payment_creates_subscription(
            services, repo, test_user, default_product_id, mock_yookassa
        )

        # Add tarot-specific check
        balance = await repo.balance.get_by_user_id(test_user.id)
        assert balance.wildcard_reading_count > 0, "Should grant reading credits"
```

### Pattern 3: Add App-Specific Tests to Inherited Class

```python
class TestTarotPayments(BasePaymentFlowTests):
    @pytest.fixture
    def default_product_id(self):
        return "MONTH_SUB_V3"

    # Inherited tests run automatically

    # Add tarot-specific tests
    @pytest.mark.integration
    async def test_subscription_grants_reading_credits(
        self,
        services,
        repo,
        test_user,
        default_product_id,
        mock_yookassa,
    ):
        """Tarot-specific: Subscription grants reading credits."""
        # ... implementation
```

### Pattern 4: Different Fixture Value per Test Class

```python
# Test with monthly subscription
class TestMonthlyPayments(BasePaymentFlowTests):
    @pytest.fixture
    def default_product_id(self):
        return "MONTH_SUB_V3"


# Test with yearly subscription
class TestYearlyPayments(BasePaymentFlowTests):
    @pytest.fixture
    def default_product_id(self):
        return "YEAR_SUB_V3"
```

### Pattern 5: Parameterized Tests Across Products

```python
class TestAllProducts(BasePaymentFlowTests):
    @pytest.fixture(params=["WEEK_SUB_V3", "MONTH_SUB_V3", "YEAR_SUB_V3"])
    def default_product_id(self, request):
        return request.param

    # All inherited tests run 3 times (once per product)
```

### Pattern 6: Specialty User Fixtures

```python
# In conftest.py
@pytest_asyncio.fixture
async def broke_user(repo, test_user):
    """User with zero balance."""
    await repo.balance.upsert({
        "user_id": test_user.id,
        "wildcard_reading_count": 0,
    })
    await repo.session.flush()
    return test_user


@pytest_asyncio.fixture
async def premium_user(repo, test_user):
    """User with active subscription."""
    from datetime import UTC, datetime, timedelta
    await repo.subscriptions.create({
        "user_id": test_user.id,
        "product_id": "MONTH_SUB_V3",
        "status": SubscriptionStatus.ACTIVE,
        "start_date": datetime.now(UTC),
        "end_date": datetime.now(UTC) + timedelta(days=30),
    })
    await repo.session.flush()
    return test_user


# In test file
class TestPaywall:
    async def test_paywall_blocks_broke_user(self, client, broke_user):
        ...

    async def test_paywall_allows_premium_user(self, client, premium_user):
        ...
```

---

## Migration Guide

### Phase 1: Set Up Core Testing Infrastructure

```bash
# Create directory structure
mkdir -p core/backend/src/core/testing/fixtures
mkdir -p core/backend/src/core/testing/base

# Create __init__.py files
touch core/backend/src/core/testing/__init__.py
touch core/backend/src/core/testing/fixtures/__init__.py
touch core/backend/src/core/testing/base/__init__.py
```

**Files to create:**
- `core/testing/fixtures/database.py`
- `core/testing/fixtures/mocks.py`
- `core/testing/fixtures/auth.py`
- `core/testing/fixtures/redis.py`
- `core/testing/base/health.py`
- `core/testing/base/auth.py`
- `core/testing/base/payments.py`
- `core/testing/base/subscriptions.py`

### Phase 2: Update App Test Structure

```bash
# For each app, create structure
mkdir -p apps/template-react/backend/src/app/tests/contract/api
mkdir -p apps/template-react/backend/src/app/tests/integration
mkdir -p apps/template-react/backend/src/app/tests/business
mkdir -p apps/template-react/backend/src/app/tests/regression
```

### Phase 3: Migrate App conftest.py

1. Remove `pytest_plugins` (if using Design 5/Hybrid approach)
2. Import core fixtures
3. Create app-specific fixtures (repo, services, test_user, client)
4. Add authenticated_client fixture

### Phase 4: Create App Test Files

For each base class, create an app test file:

```python
# apps/template-react/tests/contract/api/test_health.py
from core.testing.base.health import BaseHealthTests

class TestHealth(BaseHealthTests):
    pass
```

### Phase 5: Run and Verify

```bash
# Run all tests for app
make test APP=template-react

# Run specific test file
make test-file APP=template-react file=src/app/tests/contract/api/test_health.py

# Run with verbose output
cd apps/template-react/backend && uv run pytest src/app/tests/ -v
```

### Phase 6: Clean Up Old Files

```bash
# Remove old test_core_routes.py files
rm apps/*/backend/src/app/tests/contracts/api/test_core_routes.py

# Remove core/testing/contracts/ directory (if existed from Design 5)
rm -rf core/backend/src/core/testing/contracts/
```

---

## Troubleshooting

### Problem: "MagicMock can't be awaited"

**Cause:** Using `MagicMock` for async methods instead of `AsyncMock`.

**Solution:**
```python
# Wrong
mock_bot = MagicMock()
mock_bot.send_message = MagicMock()  # Can't be awaited!

# Right
mock_bot = MagicMock()
mock_bot.send_message = AsyncMock()  # Can be awaited
```

### Problem: Model Conflicts (SQLAlchemy Mapper)

**Cause:** Core tests importing app models indirectly.

**Solution:** Keep core tests isolated. Core's own tests should only test pure logic without database.

### Problem: Fixture Not Found

**Cause:** Test class doesn't have access to conftest.py fixtures.

**Solution:** Ensure conftest.py is in the right directory and fixtures are importable:
```
apps/template-react/backend/src/app/tests/
├── conftest.py          # Fixtures defined here
├── contract/
│   └── api/
│       └── test_health.py  # Can access conftest.py fixtures
```

### Problem: Test Database Not Isolated

**Cause:** Tests sharing state, not using transaction rollback.

**Solution:** Ensure db_session fixture uses `session.begin()` context:
```python
async with session.begin():
    yield session
    # Auto-rollback on exit
```

### Problem: Authenticated Client Not Working

**Cause:** initData signature invalid.

**Solution:** Use correct bot token for signing:
```python
from core.infrastructure.config import settings

init_data = generate_telegram_init_data(
    user_id=test_user.telegram_id,
    username=test_user.username,
    bot_token=settings.bot.token,  # Must match app's token
)
```

### Problem: Tests Pass Locally, Fail in CI

**Cause:** Timing issues with testcontainer startup.

**Solution:** Add wait for container readiness:
```python
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        postgres.start()
        # Wait for ready
        import time
        time.sleep(1)
        yield postgres
```

---

## FAQ

### Q: Why inheritance over pytest_plugins?

**A:** Single pattern is easier to understand and maintain. pytest_plugins adds "magic" that makes debugging harder.

### Q: Can I skip inherited tests?

**A:** Yes, override the method with `@pytest.mark.skip`:
```python
@pytest.mark.skip(reason="Not applicable")
async def test_something(self, **kwargs):
    pass
```

### Q: How do I add app-specific tests?

**A:** Add methods to your inherited class:
```python
class TestAppPayments(BasePaymentFlowTests):
    # Inherited tests run automatically

    # Add your own
    async def test_app_specific_thing(self, services):
        ...
```

### Q: What if I need different fixtures per test?

**A:** Override fixtures in the test class:
```python
class TestSpecialCase(BasePaymentFlowTests):
    @pytest.fixture
    def default_product_id(self):
        return "SPECIAL_PRODUCT"
```

### Q: How do I run only contract tests?

**A:**
```bash
cd apps/template-react/backend
uv run pytest src/app/tests/ -v -m "contract"
```

### Q: How do I run only integration tests?

**A:**
```bash
cd apps/template-react/backend
uv run pytest src/app/tests/integration/ -v -m "integration"
```

### Q: Should core have its own HTTP tests?

**A:** No. Core's own tests (`core/tests/`) should be fast, isolated tests for pure logic (streak calculation, password hashing). HTTP tests live in apps.

### Q: How do I test webhook handling?

**A:** Integration tests call service methods directly:
```python
async def test_webhook(self, services, repo, test_user):
    payment = await repo.payments.create({...})
    webhook = self._build_yookassa_webhook(payment, "payment.succeeded")
    await services.payments.process_callback(webhook, PaymentProvider.YOOKASSA)
    # Assert results
```

### Q: How do I test bot handlers?

**A:** Create base classes for bot tests with message/update factories:
```python
class BaseBotTests:
    @pytest.fixture
    def update_factory(self, test_user):
        def create_update(text):
            return Update(message=Message(text=text, from_user=...))
        return create_update
```

---

## Summary

### What Core Provides

| Component | Location | Purpose |
|-----------|----------|---------|
| `postgres_container` | `core/testing/fixtures/database.py` | Shared PostgreSQL testcontainer |
| `db_engine` | `core/testing/fixtures/database.py` | Fresh engine per test |
| `db_session` | `core/testing/fixtures/database.py` | Auto-rollback session |
| `mock_*` | `core/testing/fixtures/mocks.py` | External service mocks |
| `generate_telegram_init_data` | `core/testing/fixtures/auth.py` | Valid Telegram auth |
| `Base*Tests` | `core/testing/base/*.py` | Abstract test classes |

### What Apps Provide

| Component | Purpose |
|-----------|---------|
| `repo` | REAL RequestsRepo (tests composition) |
| `services` | REAL RequestsService (tests composition) |
| `test_user` | REAL user in database |
| `client` | HTTP client with dependency overrides |
| `authenticated_client` | Client with Telegram auth |
| `default_product_id` | App's subscription product |
| `Test*` classes | Inherit from base, add app-specific |

### Why This Design Works

1. **Single pattern** - All shared tests use inheritance
2. **Tests real composition** - `RequestsRepo._core` delegation verified
3. **Apps control fixtures** - Different auth, products, dependencies
4. **Full customization** - Override any test method
5. **Explicit structure** - Every test class visible in app code
6. **IDE support** - Abstract methods, clear inheritance
7. **Parallel safe** - Unique user IDs, transaction rollback

---

## Appendix: Essential Patterns

Three patterns discovered during previous implementation work.

### 1. Pytest Workers: Use `-n 2`

`-n auto` creates ~10 workers, each spawning a PostgreSQL testcontainer.

**Benchmarks:**
- `-n auto`: 27.36s (10 containers)
- `-n 2`: 9.55s (2 containers)

```makefile
test:
	cd apps/$(APP)/backend && uv run pytest src/app/tests -v -n 2 $(PYTEST_ARGS)
```

### 2. Set Bot Token Before Imports

Aiogram validates token format on import. Set fake token before any app imports:

```python
# At TOP of conftest.py, BEFORE any app imports
import os
os.environ["BOT__TOKEN"] = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
```

### 3. LifespanManager for HTTP Client

FastAPI startup events (like setting `app.state.telegram_auth`) only run with proper lifecycle management:

```python
from asgi_lifespan import LifespanManager

@pytest_asyncio.fixture
async def client(...):
    async with LifespanManager(app):  # Runs startup/shutdown events
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c
```

---

## Implementation Checklist

When implementing from commit `aac10fa9`:

- [ ] Set `-n 2` in Makefile test commands
- [ ] Set `BOT__TOKEN` env var at top of each app's conftest.py
- [ ] Use `LifespanManager` in client fixtures
