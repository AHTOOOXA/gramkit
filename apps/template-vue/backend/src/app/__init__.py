"""Template backend application.

This package provides the starter app backend with:
- App-specific models
- App-specific repositories extending CoreRequestsRepo
- App-specific services extending CoreRequestsService
- Entry points (webhook, bot, worker)
"""

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService

__all__ = [
    "RequestsRepo",
    "RequestsService",
]
