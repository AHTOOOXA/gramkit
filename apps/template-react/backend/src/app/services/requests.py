"""Template application service aggregator using composition pattern."""

from functools import cached_property

from aiogram import Bot
from arq import ArqRedis

from app.domain import products
from app.domain.referrals import INTERNAL_REFERRAL_CODES
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.balance import BalanceService
from app.services.notifications import NotificationsService
from core.infrastructure.config import settings
from core.services.admin import AdminService
from core.services.admin_tasks import AdminTasksService
from core.services.analytics import AnalyticsService
from core.services.audit_log import AuditLogService
from core.services.auth import AuthService
from core.services.broadcasts import BroadcastsService
from core.services.groups import GroupService
from core.services.invites import InvitesService
from core.services.marketing_links import MarketingLinksService
from core.services.messages import MessageService
from core.services.payments import PaymentsService
from core.services.requests import CoreRequestsService
from core.services.sessions import SessionService
from core.services.start import StartService
from core.services.statistics import StatisticsService
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
            # The app's own link codes (notification buttons): never stored as an acquisition source.
            internal_referal_ids=INTERNAL_REFERRAL_CODES,
            # Marketing links measure "activated" / "returned" as "opened the app" by default. To count
            # your own key action instead, pass marketing_links_config=MarketingLinksConfig(activation=...,
            # activity=..., activation_label=...) (core.services.marketing_links).
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

    @cached_property
    def audit_log(self) -> AuditLogService:
        """Admin audit log service (from core)."""
        return self._core.audit_log

    @cached_property
    def admin(self) -> AdminService:
        """Admin users service (from core)."""
        return self._core.admin

    @cached_property
    def admin_tasks(self) -> AdminTasksService:
        """Admin tasks service (from core): lists and runs registered ``@admin_task`` functions."""
        return self._core.admin_tasks

    @cached_property
    def broadcasts(self) -> BroadcastsService:
        """Broadcasts admin composer service (from core): scheduled + send-now broadcasts."""
        return self._core.broadcasts

    @cached_property
    def marketing_links(self) -> MarketingLinksService:
        """Marketing links service (from core): acquisition codes, their links, results and owner alerts."""
        return self._core.marketing_links

    @cached_property
    def statistics(self) -> StatisticsService:
        """Admin statistics (from core): Overview snapshot + daily digest; app extras via admin_metrics."""
        return self._core.statistics

    @cached_property
    def analytics(self) -> AnalyticsService:
        """Admin money analytics (from core): revenue, subscriptions, MRR on this app's product catalog."""
        return self._core.analytics

    # ==================== APP SERVICES (template-specific) ====================

    @cached_property
    def balance(self) -> BalanceService:
        """Balance service for managing user credits/limits."""
        return BalanceService(self.repo, self.producer, self, self.bot)

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
