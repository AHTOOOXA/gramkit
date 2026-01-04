"""Template application service aggregator using composition pattern."""

from functools import cached_property

from aiogram import Bot
from arq import ArqRedis

from app.domain import products
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.balance import BalanceService
from app.services.notifications import NotificationsService
from app.services.statistics import StatisticsService
from core.infrastructure.config import settings
from core.services.auth import AuthService
from core.services.groups import GroupService
from core.services.invites import InvitesService
from core.services.messages import MessageService
from core.services.payments import PaymentsService
from core.services.requests import CoreRequestsService
from core.services.sessions import SessionService
from core.services.start import StartService
from core.services.subscriptions import SubscriptionsService
from core.services.telegram_link import TelegramLinkService
from core.services.users import UserService
from core.services.worker import WorkerService


class RequestsService:
    """
    Template application service aggregator.

    Uses composition pattern to delegate all services to CoreRequestsService.
    Template-specific services can be added here as needed.

    Uses lazy loading pattern (@cached_property) to instantiate services only when accessed.
    """

    def __init__(
        self,
        repo: RequestsRepo,
        producer=None,
        bot: Bot | None = None,
        redis=None,
        arq: ArqRedis | None = None,
    ):
        self.repo = repo
        self.producer = producer
        self.bot = bot
        self.redis = redis
        self.arq = arq

        # Compose core services (inject app-specific products catalog)
        # All config now comes from settings
        self._core = CoreRequestsService(
            repo=repo._core,
            producer=producer,
            bot=bot,
            redis=redis,
            arq=arq,
            products=products,
        )

    # ==================== CORE SERVICES (delegated) ====================

    @cached_property
    def users(self) -> UserService:
        """User service (from core)."""
        return self._core.users

    @cached_property
    def groups(self) -> GroupService:
        """Group service (from core)."""
        return self._core.groups

    @cached_property
    def invites(self) -> InvitesService:
        """Invite service (from core)."""
        return self._core.invites

    @cached_property
    def payments(self) -> PaymentsService:
        """Payment service (from core)."""
        return self._core.payments

    @cached_property
    def subscriptions(self) -> SubscriptionsService:
        """Subscription service (from core)."""
        return self._core.subscriptions

    @cached_property
    def worker(self) -> WorkerService:
        """Worker service (from core)."""
        return self._core.worker

    @cached_property
    def auth(self) -> AuthService:
        """Auth service (from core)."""
        return self._core.auth

    @cached_property
    def telegram_auth(self) -> AuthService:
        """Alias for auth service (deprecated, use .auth instead)."""
        return self._core.auth

    @cached_property
    def start(self) -> StartService:
        """Start service (from core)."""
        return self._core.start

    @cached_property
    def messages(self) -> MessageService:
        """Message service (from core)."""
        return self._core.messages

    @cached_property
    def sessions(self) -> SessionService:
        """Session service (from core)."""
        return self._core.sessions

    # ==================== APP SERVICES (template-specific) ====================

    @cached_property
    def balance(self) -> BalanceService:
        """Balance service for managing user credits/limits."""
        return BalanceService(self.repo, self.producer, self, self.bot)

    @cached_property
    def statistics(self) -> StatisticsService:
        """Statistics service for gathering app usage metrics."""
        return StatisticsService(self.repo, self.producer, self, self.bot)

    @cached_property
    def notifications(self) -> NotificationsService:
        """Notification service (app-specific implementation)."""
        return NotificationsService(self.repo, self.producer, self, self.bot)

    @cached_property
    def telegram_link(self) -> TelegramLinkService:
        """Telegram link service for linking Telegram accounts to existing users."""
        return TelegramLinkService(
            redis=self.redis,
            user_repo=self.repo.users,
            bot_url=settings.bot.url,
        )
