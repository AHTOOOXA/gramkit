"""Core service aggregator using lazy loading pattern."""

from functools import cached_property
from typing import Any

from aiogram import Bot
from arq import ArqRedis

from core.domain.products import ProductCatalog
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.auth import AuthService
from core.services.groups import GroupService
from core.services.invites import InvitesService
from core.services.messages import MessageService
from core.services.payments import PaymentsService
from core.services.sessions import SessionService
from core.services.start import StartService
from core.services.subscriptions import SubscriptionsService
from core.services.users import UserService
from core.services.worker import WorkerService


class CoreRequestsService:
    """Core service aggregator using lazy loading pattern.

    Apps should use composition pattern to extend core services:

    Example:
        ```python
        from core.services.requests import CoreRequestsService

        class AppRequestsService:
            def __init__(self, repo, producer, bot, redis, arq):
                self.repo = repo
                self._core = CoreRequestsService(
                    repo=repo._core,
                    producer=producer,
                    bot=bot,
                    redis=redis,
                    arq=arq,
                    products=products,
                )

            @cached_property
            def users(self):
                '''User service (from core)'''
                return self._core.users

            @cached_property
            def my_app_service(self):
                '''App-specific service'''
                return MyAppService(self.repo, self.producer, self, self.bot)
        ```

    This pattern provides:
    - Clear separation between core and app services
    - Explicit delegation via self._core
    - Easy extension with app-specific services
    - No inheritance coupling

    Each property uses @cached_property to instantiate services only when first accessed.
    """

    def __init__(
        self,
        repo: CoreRequestsRepo,
        producer=None,
        bot: Bot = None,
        redis=None,
        arq: ArqRedis = None,
        products: ProductCatalog = None,
    ):
        self.repo = repo
        self.producer = producer
        self.bot = bot
        self.redis = redis
        self.arq = arq
        self.products = products

    @cached_property
    def users(self) -> UserService:
        """User service for user management and authentication."""
        return UserService(self.repo, self.producer, self, self.bot)

    @cached_property
    def groups(self) -> GroupService:
        """Group service for managing user groups."""
        return GroupService(self.repo, self.producer, self, self.bot)

    @cached_property
    def invites(self) -> InvitesService:
        """Invite service for managing group invitations."""
        return InvitesService(self.repo, self.producer, self, self.bot)

    @cached_property
    def payments(self) -> PaymentsService:
        """Payment service for payment processing."""
        return PaymentsService(self.repo, self.producer, self, self.bot, self.products)

    @cached_property
    def subscriptions(self) -> SubscriptionsService:
        """Subscription service for subscription management."""
        return SubscriptionsService(self.repo, self.producer, self, self.bot, self.products)

    @cached_property
    def worker(self) -> WorkerService:
        """Worker service for background job management."""
        return WorkerService(self.arq, self.repo, self.producer, self, self.bot)

    @cached_property
    def auth(self) -> AuthService:
        """Auth service for authentication (code-based, deep link, and email)."""
        return AuthService(self.repo, self.producer, self, self.bot)

    @cached_property
    def telegram_auth(self) -> AuthService:
        """Alias for auth service (deprecated, use .auth instead)."""
        return self.auth

    @cached_property
    def start(self) -> StartService:
        """Start service for handling bot startup and initialization."""
        return StartService(self.repo, self.producer, self, self.bot)

    @cached_property
    def messages(self) -> MessageService:
        """Message service for handling messaging functionality."""
        return MessageService(self.repo, self.producer, self, self.bot)

    @cached_property
    def sessions(self) -> SessionService:
        """Session service for managing user sessions in Redis (business logic)."""
        return SessionService(redis=self.redis)

    def get_all_services(self) -> dict[str, Any]:
        """Get all core services as dict (useful for debugging/introspection).

        Returns:
            Dictionary mapping service names to service instances.
        """
        return {
            "users": self.users,
            "groups": self.groups,
            "invites": self.invites,
            "payments": self.payments,
            "subscriptions": self.subscriptions,
            "worker": self.worker,
            "auth": self.auth,
            "start": self.start,
            "messages": self.messages,
            "sessions": self.sessions,
        }
