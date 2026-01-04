# gramkit - Core Backend

Reusable backend infrastructure for web applications with Telegram Mini App support.

## Overview

This package provides core functionality that can be shared across multiple web applications:

- **User Management**: Authentication, profiles, user types (Guest/Registered), streaks
- **Payment Processing**: YooKassa and Telegram Stars integration
- **Subscription System**: Plans, status tracking, renewal, cancellation
- **Social Features**: Groups, invites, friendships
- **Notifications**: User engagement and reminder system
- **Balance System**: Credits and resource management

## Architecture

The core package follows a **3-layer architecture** with **lazy loading aggregators**:

### Repository Layer (Data Access)

```python
from core.infrastructure.database.repo.requests import CoreRequestsRepo

# Lazy loading pattern - repositories instantiated only when accessed
repo = CoreRequestsRepo(session)
user = await repo.users.get_by_id(user_id)
payments = await repo.payments.get_by_user_id(user_id)
```

Available repositories:
- `users` - UserRepo
- `balance` - BalanceRepo
- `groups` - GroupRepo
- `members` - GroupMemberRepo
- `invites` - InviteRepo
- `payments` - PaymentRepo
- `payment_events` - PaymentEventRepo
- `subscriptions` - SubscriptionRepo

### Service Layer (Business Logic)

```python
from core.services.requests import CoreRequestsService

# Lazy loading pattern - services instantiated only when accessed
services = CoreRequestsService(repo, producer, bot, redis, arq)
user = await services.users.get_or_create_user(user_data)
await services.payments.process_payment(payment_data)
```

Available services:
- `users` - UserService
- `groups` - GroupService
- `invites` - InvitesService
- `payments` - PaymentsService
- `subscriptions` - SubscriptionsService
- `notifications` - NotificationsService

### Model Layer

Core SQLAlchemy models for database tables:
- `User` - User accounts and profiles
- `Balance` - User credits and balances
- `Payment` / `PaymentEvent` - Payment transactions
- `Subscription` - Subscription management
- `GroupInvite` - Group invitation codes
- `Friendship` - User friendships
- `Group` / `GroupMember` - Group management

## Extending Core for Apps

Apps can extend the core aggregators using **two patterns**: **inheritance** (simple) or **composition** (recommended).

### Pattern 1: Inheritance (Simple)

The inheritance pattern is straightforward - extend the core classes directly:

```python
# apps/myapp/backend/src/infrastructure/database/repo/requests.py
from functools import cached_property
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from app.infrastructure.database.repo.orders import OrdersRepo
from app.infrastructure.database.repo.products import ProductsRepo

class MyAppRequestsRepo(CoreRequestsRepo):
    """App repository aggregator extending core."""

    @cached_property
    def orders(self) -> OrdersRepo:
        return OrdersRepo(self.session)

    @cached_property
    def products(self) -> ProductsRepo:
        return ProductsRepo(self.session)

# Now you have both core and app-specific repos:
repo = MyAppRequestsRepo(session)
user = await repo.users.get_by_id(user_id)  # Core
order = await repo.orders.get_by_id(order_id)  # App-specific
```

```python
# apps/myapp/backend/src/services/requests.py
from functools import cached_property
from core.services.requests import CoreRequestsService
from app.services.orders import OrdersService
from app.services.products import ProductsService

class MyAppRequestsService(CoreRequestsService):
    """App service aggregator extending core."""

    @cached_property
    def orders(self) -> OrdersService:
        return OrdersService(self.repo, self.producer, self, self.bot)

    @cached_property
    def products(self) -> ProductsService:
        return ProductsService(self.repo, self.producer, self, self.bot)

# Now you have both core and app-specific services:
services = MyAppRequestsService(repo, producer, bot, redis, arq)
await services.users.update_user_streak(user_id)  # Core
order = await services.orders.create_order(data)  # App-specific
```

**Benefits:** Simple, automatic inheritance of all core functionality

**Trade-offs:** Tight coupling, harder to test in isolation, app versioned with core

### Pattern 2: Composition (Recommended)

The composition pattern provides loose coupling and explicit API surface:

```python
# apps/myapp/backend/src/infrastructure/database/repo/requests.py
from functools import cached_property
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from app.infrastructure.database.repo.orders import OrdersRepo
from app.infrastructure.database.repo.products import ProductsRepo

class MyAppRequestsRepo:
    """App repository aggregator using composition."""

    def __init__(self, session):
        self.session = session
        self._core = CoreRequestsRepo(session)

    # Delegate core repos explicitly
    @cached_property
    def users(self):
        """User repository (from core)"""
        return self._core.users

    @cached_property
    def balance(self):
        """Balance repository (from core)"""
        return self._core.balance

    @cached_property
    def payments(self):
        """Payment repository (from core)"""
        return self._core.payments

    @cached_property
    def subscriptions(self):
        """Subscription repository (from core)"""
        return self._core.subscriptions

    # Add domain-specific repos
    @cached_property
    def orders(self) -> OrdersRepo:
        """Orders repository (app-specific)"""
        return OrdersRepo(self.session)

    @cached_property
    def products(self) -> ProductsRepo:
        """Products repository (app-specific)"""
        return ProductsRepo(self.session)
```

```python
# apps/myapp/backend/src/services/requests.py
from functools import cached_property
from core.services.requests import CoreRequestsService
from app.services.orders import OrdersService
from app.services.products import ProductsService

class MyAppRequestsService:
    """App service aggregator using composition."""

    def __init__(self, repo, producer, bot, redis, arq, yookassa_config, tgbot_config, products):
        self.repo = repo
        self._core = CoreRequestsService(
            repo=repo._core,
            producer=producer,
            bot=bot,
            redis=redis,
            arq=arq,
            yookassa_config=yookassa_config,
            tgbot_config=tgbot_config,
            products=products,
        )

    # Delegate core services explicitly
    @cached_property
    def users(self):
        """User service (from core)"""
        return self._core.users

    @cached_property
    def payments(self):
        """Payment service (from core)"""
        return self._core.payments

    @cached_property
    def subscriptions(self):
        """Subscription service (from core)"""
        return self._core.subscriptions

    # Add domain-specific services
    @cached_property
    def orders(self) -> OrdersService:
        """Orders service (app-specific)"""
        return OrdersService(self.repo, self.producer, self, self.bot)

    @cached_property
    def products(self) -> ProductsService:
        """Products service (app-specific)"""
        return ProductsService(self.repo, self.producer, self, self.bot)

# Usage remains the same:
services = MyAppRequestsService(repo, producer, bot, redis, arq, ...)
await services.users.update_user_streak(user_id)  # Core
order = await services.orders.create_order(data)  # App-specific
```

**Benefits:**
- Loose coupling - app and core versions independent
- Explicit API surface - clear which core features are used
- Easy to test in isolation
- Better for long-term maintainability

**Trade-offs:**
- More boilerplate (delegation properties)
- Requires explicit property delegation

### Choosing Between Patterns

**Use Inheritance** when:
- Starting a new app quickly
- Core and app evolve together
- Simple, direct access to all core features

**Use Composition** when:
- Building for long-term maintainability
- Need independent versioning of core and app
- Want explicit control over API surface
- Testing in isolation is important

## Key Features

### Lazy Loading Pattern

Both `CoreRequestsRepo` and `CoreRequestsService` use `@property` decorators for lazy loading:

```python
@property
def users(self) -> UserRepo:
    return UserRepo(self.session)
```

Benefits:
- Services/repos only instantiated when accessed
- Reduces memory footprint
- Faster initialization
- Clear dependency boundaries

### Transaction Management

Repositories use `flush()` instead of `commit()` - transactions are managed at the interface layer:

```python
# Repository operation (uses flush)
user = await repo.users.create(user_data)
payment = await repo.payments.create(payment_data)
# Transaction commits at dependency injection layer
```

### Pessimistic Locking

For race-prone operations, use `get_by_id_with_lock()`:

```python
# Exclusive lock (default) - prevents all access
balance = await repo.balance.get_by_id_with_lock(user_id)
balance.credits -= 1
await repo.balance.update(balance.id, {"credits": balance.credits})

# Shared lock - allows other reads
balance = await repo.balance.get_by_id_with_lock(user_id, read=True)
```

## Dependencies

Core package dependencies (from `core/backend/pyproject.toml`):

```toml
[project]
dependencies = [
    "sqlalchemy>=2.0",
    "aiogram>=3.0",
    "pydantic>=2.0",
    "arq",
    # ... other core dependencies
]
```

Apps add their own dependencies in `apps/*/backend/pyproject.toml`.

## Testing

Core infrastructure should be thoroughly tested to ensure reliability across all apps.

```bash
# Run core tests (when implemented)
cd core/backend
uv run pytest tests/
```

## Migration Guide

See `/docs/monorepo/BACKEND_MIGRATION_GUIDE.md` for complete migration instructions.

## License

MIT
