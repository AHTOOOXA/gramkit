"""Import all routers and add them to routers_list."""

from core.infrastructure.telegram.handlers.admin import router as core_admin_router
from core.infrastructure.telegram.handlers.auth import router as auth_router
from core.infrastructure.telegram.handlers.payments import router as payments_router
from core.infrastructure.telegram.handlers.telegram_link import router as telegram_link_router

from .admin import router as admin_router
from .start import router as start_router

routers_list = [
    # auth_router and telegram_link_router MUST be before start_router
    # to catch /start auth_{token} and /start link_{token} commands
    auth_router,
    telegram_link_router,
    start_router,
    admin_router,
    core_admin_router,  # Core admin commands (/backup)
    payments_router,
]

__all__ = [
    "routers_list",
]
