from typing import TYPE_CHECKING

from aiogram import Bot

from core.infrastructure.database.repo.requests import CoreRequestsRepo

if TYPE_CHECKING:
    from core.services.requests import CoreRequestsService


class BaseService:
    """
    A class representing a base service for handling database operations.

    Attributes:
        session (AsyncSession): The database session used by the service.

    """

    def __init__(
        self,
        repo: CoreRequestsRepo,
        producer,
        services: CoreRequestsService,
        bot: Bot,
    ):
        self.repo: CoreRequestsRepo = repo
        self.producer = producer
        self.services: CoreRequestsService = services
        self.bot: Bot = bot
