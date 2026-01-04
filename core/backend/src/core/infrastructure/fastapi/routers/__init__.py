"""Core FastAPI routers.

This package contains reusable API routers that can be used across apps.

Directory structure:
    routers/
        __init__.py             # This file
        health.py               # Health check routes
        auth_telegram.py        # Telegram authentication (code + deep link)
        auth_email.py           # Email authentication (signup, login, link, reset)
        auth_telegram_link.py   # Telegram account linking for web users
        payments.py             # Payment routes
        webhooks.py             # Payment webhook routes
        subscriptions.py        # Subscription routes
        users.py                # User routes

Usage in apps:
    from core.infrastructure.fastapi.routers import (
        auth_telegram,
        auth_email,
        auth_telegram_link,
        payments,
    )

    app = create_api(
        routers=[
            auth_telegram.router,
            auth_email.router,
            auth_telegram_link.router,
            payments.router,
        ],
    )
"""

from core.infrastructure.fastapi.routers import (
    auth_email,
    auth_telegram,
    auth_telegram_link,
    health,
    payments,
    subscriptions,
    users,
    webhooks,
)

__all__ = [
    "auth_email",
    "auth_telegram",
    "auth_telegram_link",
    "health",
    "payments",
    "subscriptions",
    "users",
    "webhooks",
]
