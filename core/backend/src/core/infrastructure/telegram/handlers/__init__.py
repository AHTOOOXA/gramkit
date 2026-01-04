"""Core Telegram bot handlers for reuse across apps."""

from core.infrastructure.telegram.handlers.admin import router as admin_router
from core.infrastructure.telegram.handlers.auth import router as auth_router
from core.infrastructure.telegram.handlers.payments import router as payments_router
from core.infrastructure.telegram.handlers.start import ref_command, start_command
from core.infrastructure.telegram.handlers.start import router as start_router
from core.infrastructure.telegram.handlers.telegram_link import router as telegram_link_router

__all__ = [
    "admin_router",
    "auth_router",
    "payments_router",
    "start_router",
    "telegram_link_router",
    "start_command",
    "ref_command",
]
