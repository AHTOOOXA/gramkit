"""Core backend infrastructure for Telegram Mini Apps platform.

This package provides reusable components that can be shared across multiple TMA apps:
- User management and authentication
- Payment processing (YooKassa, Telegram Stars)
- Subscription management
- Group and invite system
- Notification services

Apps extend CoreRequestsRepo and CoreRequestsService to add domain-specific functionality.

Usage:
    from core.infrastructure.database.repo.requests import CoreRequestsRepo
    from core.services.requests import CoreRequestsService

Note: Services and repos are not auto-imported to avoid circular dependencies.
Import them explicitly where needed.
"""

__version__ = "0.1.0"
