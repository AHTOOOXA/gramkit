"""Core FastAPI routers.

This package contains reusable API routers that can be used across apps.

Directory structure:
    routers/
        __init__.py             # This file
        admin.py                # Admin panel: RBAC meta, audit log, tasks, users, refunds
        admin_broadcasts.py     # Admin broadcasts; included by admin.py (never mount it directly)
        admin_marketing_links.py  # Admin marketing links; included by admin.py (never mount it directly)
        admin_statistics.py     # Admin overview + money analytics; included by admin.py (never mount it directly)
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
    admin,
    admin_broadcasts,
    admin_marketing_links,
    admin_statistics,
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
    "admin",
    "admin_broadcasts",  # included by admin.router; never mount it directly (duplicate routes)
    "admin_marketing_links",  # included by admin.router; never mount it directly (duplicate routes)
    "admin_statistics",  # included by admin.router; never mount it directly (duplicate routes)
    "auth_email",
    "auth_telegram",
    "auth_telegram_link",
    "health",
    "payments",
    "subscriptions",
    "users",
    "webhooks",
]
