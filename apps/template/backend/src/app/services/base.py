"""Tarot application base service with app-specific types."""

from typing import TYPE_CHECKING

from aiogram import Bot

from app.infrastructure.database.repo.requests import RequestsRepo

if TYPE_CHECKING:
    from app.services.requests import RequestsService


class BaseService:
    """
    Tarot application base service.

    Provides common dependencies for all tarot services with app-specific types.
    """

    def __init__(
        self,
        repo: RequestsRepo,
        producer,
        services: RequestsService,
        bot: Bot | None,
    ):
        self.repo: RequestsRepo = repo
        self.producer = producer
        self.services: RequestsService = services
        self.bot = bot
