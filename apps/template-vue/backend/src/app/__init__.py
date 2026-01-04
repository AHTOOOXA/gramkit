"""Tarot backend application.

This package provides the tarot application backend with:
- Tarot-specific models (readings, chat, trainer, etc.)
- Tarot-specific repositories extending CoreRequestsRepo
- Tarot-specific services extending CoreRequestsService
- Entry points (webhook, bot, worker)
"""

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService

__all__ = [
    "RequestsRepo",
    "RequestsService",
]
