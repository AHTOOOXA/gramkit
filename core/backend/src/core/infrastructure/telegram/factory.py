"""Telegram bot application factory."""

from typing import Protocol

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

from core.infrastructure.config import settings
from core.infrastructure.database.setup import create_engine, create_session_pool
from core.infrastructure.dependencies import Dependencies
from core.infrastructure.telegram.middlewares import (
    AuthMiddleware,
    DatabaseMiddleware,
    I18nMiddleware,
    ServiceMiddleware,
)


class BotConfig(Protocol):
    """Protocol for bot configuration."""

    token: str
    debug: bool


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
    url: str


async def create_tg_bot(
    config: BotConfig,
    db_config: DBConfig,
    redis_config: RedisConfig,
    repo_class: type,
    service_class: type,
    routers: list[Router],
    dependencies: Dependencies,
) -> tuple[Bot, Dispatcher, Dependencies]:
    """
    Create fully-configured Telegram bot with standard infrastructure.

    Sets up automatically:
    - Bot instance with token
    - Dispatcher with Redis storage
    - Middleware chain (Database → Service → Auth → I18n)
    - Database session pool with auto-cleanup
    - Service auto-wiring from Dependencies
    - All routers registered in order

    Args:
        config: Bot configuration (token, debug)
        db_config: Database configuration (dsn, pool settings)
        redis_config: Redis configuration for FSM storage
        repo_class: Repository aggregator class (e.g., RequestsRepo)
        service_class: Service aggregator class (e.g., RequestsService)
        routers: List of aiogram routers to register
        dependencies: Dependency container with configs/pre-created deps

    Returns:
        (Bot, Dispatcher, Dependencies): Ready bot + deps for cleanup

    Example (Simple - just pass configs):
        from core.infrastructure.telegram import create_tg_bot
        from core.infrastructure.dependencies import Dependencies
        from core.infrastructure.config import settings
        from app.services.requests import RequestsService
        from app.infrastructure.database.repo.requests import RequestsRepo
        from app.tgbot.handlers import routers_list

        # Dependencies auto-created from configs
        bot, dp, deps = create_tg_bot(
            config=tgbot_config,
            db_config=db_config,
            redis_config=redis_config,
            repo_class=RequestsRepo,
            service_class=RequestsService,
            routers=routers_list,
            dependencies=Dependencies(
                redis_config=redis_config,
                rabbit_config=rabbit_config,
            ),
        )

        # Start bot
        await dp.start_polling(bot)

        # Cleanup
        await deps.close()
    """
    # Create bot
    bot = Bot(token=config.token, default=DefaultBotProperties(parse_mode="HTML"))

    # Create dispatcher with Redis storage
    storage = RedisStorage.from_url(
        settings.redis.url,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
    )
    dp = Dispatcher(storage=storage)

    # Setup database
    engine = create_engine(db_config)
    session_pool = create_session_pool(engine)

    # Initialize dependencies (arq pool needs async creation)
    await dependencies.get_arq()

    # Create explicit service factory (type-safe, no magic)
    def service_factory(repo, bot):
        return service_class(
            repo=repo,
            bot=bot,
            arq=dependencies.get_dependency("arq"),
            redis=dependencies.get_dependency("redis"),
            producer=dependencies.get_dependency("producer"),
        )

    # Middleware chain (CRITICAL ORDER: Database → Service → Auth → I18n)
    # 1. Database - provides session + repo
    dp.update.outer_middleware(DatabaseMiddleware(session_pool, repo_factory=lambda session: repo_class(session)))

    # 2. Service - uses repo to create services (explicit dependencies)
    dp.update.outer_middleware(ServiceMiddleware(service_factory=service_factory))

    # 3. Auth - uses services.users to authenticate
    dp.update.outer_middleware(AuthMiddleware())

    # 4. I18n - uses authenticated user for locale
    dp.update.outer_middleware(I18nMiddleware())

    # Register all routers
    for router in routers:
        dp.include_router(router)

    # Store engine for cleanup
    dp["engine"] = engine

    return bot, dp, dependencies
