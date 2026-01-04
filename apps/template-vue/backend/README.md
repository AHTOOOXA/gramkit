# Tarot Backend

Backend services for the web application template.

## Architecture Pattern

This application uses **composition pattern** for loose coupling with the Core package.

### Composition with Core

```python
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.requests import CoreRequestsService

class RequestsRepo:
    def __init__(self, session):
        self.session = session
        self._core = CoreRequestsRepo(session)

    # Delegate core repos via @cached_property
    @cached_property
    def users(self) -> UserRepo:
        """User repository (from core)"""
        return self._core.users

class RequestsService:
    def __init__(self, repo, producer, bot, redis, arq):
        self.repo = repo
        self._core = CoreRequestsService(...)

    # Re-instantiate core services with full context
    @cached_property
    def users(self) -> UserService:
        """User service (from core)"""
        return UserService(self.repo._core, self.producer, self, self.bot)
```

**Key Pattern:** Core services are re-instantiated (not delegated) to receive full `RequestsService` context. This allows core services to call tarot-specific services (e.g., `services.messages.queue_admin_broadcast`).

## Repositories

### Core Repos (8) - Delegated from CoreRequestsRepo

- `users` - User management
- `balance` - Balance tracking
- `groups` - Group management
- `members` - Group membership
- `invites` - Invitation system
- `payments` - Payment processing
- `payment_events` - Payment event tracking
- `subscriptions` - Subscription management

### Tarot Repos (6) - App-specific

- `readings` - Tarot reading management
- `chat_sessions` - Chat message storage
- `trainer_progress` - Learning progress tracking
- `cards` - Tarot card data (in-memory)
- `promotional_broadcasts` - Marketing broadcasts
- `user_question_answers` - User quiz answers

## Services

### Core Services (5) - Re-instantiated with full context

- `users` - User business logic
- `groups` - Group business logic
- `invites` - Invitation business logic
- `payments` - Payment business logic
- `subscriptions` - Subscription business logic

### Tarot Services (12) - App-specific

- `readings` - Tarot reading orchestration
- `chat` - Chat conversation handling
- `trainer` - Learning system
- `statistics` - Analytics and reporting
- `messages` - Message queueing and broadcasting
- `notifications` - User notifications
- `telegram_auth` - Telegram authentication
- `balance` - Balance operations (extends core)
- `start` - Bot startup and initialization
- `llm` - AI/LLM interaction
- `tarot` - Tarot card management
- `worker` - Background job management

## Testing

```bash
# Run all tests
cd apps/template/backend
uv run pytest -v

# Run contract tests only (80%)
uv run pytest -m contract -v

# Run business logic tests only (15%)
uv run pytest -m business_logic -v

# Run regression tests only (5%)
uv run pytest -m regression -v

# Run with coverage
uv run pytest --cov=app

# Run affected tests only (fast development)
uv run pytest --testmon
```

## Database Migrations

```bash
# Create new migration
make migration msg="add user table"

# Apply migrations
make upgrade

# Rollback one migration
make downgrade
```

## Development

```bash
# Add dependency
cd apps/template/backend
uv add package-name

# Add dev dependency
uv add package-name --dev

# Run linting
make lint

# Generate OpenAPI schema
make schema
```

## Architecture Benefits

**Composition Pattern:**
- Loose coupling with Core
- Easy to test (mock `self._core`)
- Independent versioning
- Explicit API surface
- Better documentation

**Re-instantiation Pattern (for services):**
- Core services can call tarot services
- Full context propagation
- Cross-service communication works
- No circular dependency issues
