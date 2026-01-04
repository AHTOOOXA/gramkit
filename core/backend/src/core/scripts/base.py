from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar

from aiogram import Bot
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.logging import get_logger
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient

# Generic types for repository and service layers
TRepo = TypeVar("TRepo")
TService = TypeVar("TService")


class BaseScript(ABC, Generic[TRepo, TService]):  # noqa: UP046
    """Base class for all executable scripts with full infrastructure access

    This is a generic base class that can be parameterized with app-specific
    RequestsRepo and RequestsService types.

    Usage:
        class MyScript(BaseScript[RequestsRepo, RequestsService]):
            async def run(self):
                async with self.with_services() as services:
                    # Use services here
                    ...
    """

    def __init__(
        self,
        ctx: dict[str, Any],
        repo_factory: type[TRepo],
        service_factory: type[TService],
    ):
        """Initialize script with infrastructure context and factories

        Args:
            ctx: Infrastructure context dict with bot, redis, producer, arq, session_pool
            repo_factory: Factory class for creating RequestsRepo instances
            service_factory: Factory class for creating RequestsService instances
        """
        self.ctx = ctx
        self.logger = get_logger(self.__class__.__name__)

        self.bot: Bot = ctx["bot"]
        self.redis: RedisClient = ctx["redis"]
        self.producer: RabbitMQProducer = ctx["producer"]
        self.arq: ArqRedis = ctx["arq"]
        self.session_pool: async_sessionmaker[AsyncSession] = ctx["session_pool"]

        self._repo_factory = repo_factory
        self._service_factory = service_factory

    async def get_services(self) -> TService:
        """Get RequestsService with all dependencies injected"""
        async with self.session_pool() as session:
            repo = self._repo_factory(session)
            return self._service_factory(
                repo=repo,
                producer=self.producer,
                bot=self.bot,
                redis=self.redis,
                arq=self.arq,
            )

    @asynccontextmanager
    async def with_session(self):
        """Context manager for database session"""
        async with self.session_pool() as session:
            yield session

    @asynccontextmanager
    async def with_repo(self):
        """Context manager for RequestsRepo"""
        async with self.session_pool() as session:
            yield self._repo_factory(session)

    @asynccontextmanager
    async def with_services(self):
        """Context manager for RequestsService"""
        async with self.session_pool() as session:
            repo = self._repo_factory(session)
            yield self._service_factory(
                repo=repo,
                producer=self.producer,
                bot=self.bot,
                redis=self.redis,
                arq=self.arq,
            )

    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main script execution logic"""
        pass

    async def setup(self):
        """Optional setup logic before script execution"""
        pass

    async def teardown(self):
        """Optional cleanup logic after script execution"""
        pass

    async def execute(self, *args, **kwargs):
        """Execute the script with setup and teardown"""
        try:
            await self.setup()
            self.logger.info(f"Starting script: {self.__class__.__name__}")
            result = await self.run(*args, **kwargs)
            self.logger.info(f"Script completed: {self.__class__.__name__}")
            return result
        except Exception as e:
            self.logger.error(f"Script failed: {self.__class__.__name__}", exc_info=e)
            raise
        finally:
            await self.teardown()
