"""ARQ worker application factory."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Protocol

from aiogram import Bot
from arq.connections import RedisSettings

from core.infrastructure.config import settings
from core.infrastructure.database.setup import create_engine, create_session_pool
from core.infrastructure.dependencies import Dependencies
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class BotConfig(Protocol):
    """Protocol for bot configuration."""

    token: str


class DBConfig(Protocol):
    """Protocol for database configuration.

    Provides async SQLAlchemy connection URL via `url` property.

    Note: pool_size and pool_recycle are currently hardcoded in
    core/infrastructure/database/setup.py (pool_size=20, pool_recycle=1800).
    """

    url: str


class RedisConfig(Protocol):
    """Protocol for Redis configuration."""

    host: str
    port: int
    password: str


class WorkerContext:
    """
    Helper for accessing worker context with granular transaction control.

    Provides clean patterns for transaction management in worker jobs:
    - with_transaction(): Single operation in a transaction
    - with_repo(): Direct repo access (read-only, no transaction)
    - Direct access to bot, redis, arq, producer for external API calls

    Example:
        @inject_context
        async def my_job(ctx: WorkerContext):
            # Transaction for DB operations
            async with ctx.with_transaction() as services:
                await services.users.create_user(...)

            # External API call (no transaction)
            await ctx.bot.send_message(...)
    """

    def __init__(self, ctx_dict: dict):
        self.ctx_dict = ctx_dict
        self.session_pool = ctx_dict["session_pool"]
        self.bot = ctx_dict["bot"]
        self.repo_class = ctx_dict["repo_class"]
        self.service_factory = ctx_dict["service_factory"]

        # Optional dependencies
        self.redis = ctx_dict.get("redis")
        self.arq = ctx_dict.get("arq")
        self.producer = ctx_dict.get("producer")

    @asynccontextmanager
    async def with_transaction(self):
        """
        Context manager that provides services within a transaction.

        Use for operations that should be atomic. Transaction commits
        when the context exits successfully, rolls back on exception.

        Usage:
            async with ctx.with_transaction() as services:
                await services.users.create_user(data)
                await services.balance.update_balance(user_id, balance)
                # Transaction commits here
        """
        async with self.session_pool() as session:
            async with session.begin():
                repo = self.repo_class(session)
                services = self.service_factory(repo=repo, bot=self.bot)
                yield services

    @asynccontextmanager
    async def with_repo(self):
        """
        Context manager that provides repo without transaction.

        Use for read-only queries that don't need transaction protection.

        Usage:
            async with ctx.with_repo() as repo:
                users = await repo.users.get_all()
        """
        async with self.session_pool() as session:
            yield self.repo_class(session)


def inject_context(func):
    """
    Decorator that injects WorkerContext for granular transaction control.

    Jobs receive a WorkerContext instance with helper methods for
    transaction management and direct access to infrastructure.

    Usage:
        @inject_context
        async def my_job(ctx: WorkerContext, arg1, arg2):
            # Use transaction for DB operations
            async with ctx.with_transaction() as services:
                await services.users.do_something()

            # Use bot directly for external API
            await ctx.bot.send_message(...)
    """

    @wraps(func)
    async def wrapper(ctx_dict, *args, **kwargs):
        ctx = WorkerContext(ctx_dict)
        return await func(ctx, *args, **kwargs)

    return wrapper


def create_worker_settings(
    bot_config: BotConfig,
    db_config: DBConfig,
    redis_config: RedisConfig,
    repo_class: type,
    service_class: type,
    job_functions: list[Callable],
    dependencies: Dependencies,
    cron_jobs: list | None = None,
    max_jobs: int = 10,
    job_timeout: int = 600,
):
    """
    Create ARQ WorkerSettings with standard infrastructure.

    Sets up automatically:
    - Redis connection pool for ARQ
    - Database session pool with auto-cleanup
    - Bot instance with auto-cleanup
    - Service factory with auto-wiring from Dependencies
    - WorkerContext helper for jobs
    - Job function registration
    - Startup/shutdown lifecycle

    Args:
        bot_config: Bot configuration (token)
        db_config: Database configuration
        redis_config: Redis configuration for ARQ
        repo_class: Repository aggregator class
        service_class: Service aggregator class
        job_functions: List of async functions to register as jobs
        dependencies: Dependency container with configs/pre-created deps
        cron_jobs: List of cron job definitions (optional)
        max_jobs: Maximum concurrent jobs (default: 10)
        job_timeout: Job timeout in seconds (default: 600)

    Returns:
        WorkerSettings class for ARQ

    Example:
        from core.infrastructure.arq import create_worker_settings
        from core.infrastructure.dependencies import Dependencies
        from core.infrastructure.config import settings
        from app.services.requests import RequestsService
        from app.infrastructure.database.repo.requests import RequestsRepo
        from app.worker import jobs

        # Dependencies auto-created from configs
        WorkerSettings = create_worker_settings(
            bot_config=tgbot_config,
            db_config=db_config,
            redis_config=redis_config,
            repo_class=RequestsRepo,
            service_class=RequestsService,
            job_functions=[
                jobs.send_daily_notification,
                jobs.cleanup_old_sessions,
            ],
            dependencies=Dependencies(
                redis_config=redis_config,
                rabbit_config=rabbit_config,
            ),
        )

    Job functions use @inject_context:
        from core.infrastructure.arq import inject_context

        @inject_context
        async def my_job(ctx: WorkerContext):
            async with ctx.with_transaction() as services:
                await services.users.do_something()
    """

    async def startup(ctx):
        """Initialize worker context."""
        logger.info("Worker started")

        # Initialize long-lived clients
        ctx["bot"] = Bot(token=bot_config.token)

        # Create dependencies (arq, redis, producer)
        ctx["arq"] = await dependencies.get_arq()
        ctx["redis"] = dependencies.get_redis()
        ctx["producer"] = dependencies.get_producer()

        # Database
        engine = create_engine(db_config)
        session_pool = create_session_pool(engine)
        ctx["engine"] = engine
        ctx["session_pool"] = session_pool

        # Store classes and explicit factory for WorkerContext (type-safe)
        ctx["repo_class"] = repo_class

        # Create explicit service factory (no magic, full type safety)
        def service_factory(repo, bot):
            return service_class(
                repo=repo,
                bot=bot,
                arq=ctx["arq"],
                redis=ctx["redis"],
                producer=ctx["producer"],
            )

        ctx["service_factory"] = service_factory

    async def shutdown(ctx):
        """Cleanup worker context."""
        logger.info("Worker shutdown")

        if "bot" in ctx:
            await ctx["bot"].session.close()

        # Close dependencies
        await dependencies.close()

        if "session_pool" in ctx:
            await ctx["session_pool"].close()

        if "engine" in ctx:
            await ctx["engine"].dispose()

    # Capture parameters for class definition
    _cron_jobs = cron_jobs or []
    _max_jobs = max_jobs
    _job_timeout = job_timeout
    _functions = job_functions

    class WorkerSettings:
        """ARQ worker settings."""

        redis_settings = RedisSettings(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
        )
        functions = _functions
        cron_jobs = _cron_jobs
        max_jobs = _max_jobs
        job_timeout = _job_timeout
        on_startup = startup
        on_shutdown = shutdown
        handle_signals = False

    return WorkerSettings
