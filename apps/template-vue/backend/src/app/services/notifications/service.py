"""Template notification service with example notification templates.

This shows how to extend the core NotificationsService with app-specific notifications.
Replace the example notifications with your app's actual notification templates.
"""

from app.services.notifications.templates import (
    ExampleDailyNotification,
    ExampleEngagementNotification,
)
from core.services.notifications.service import NotificationsService as CoreNotificationsService


class NotificationsService(CoreNotificationsService):
    """
    Template application notification service.

    Extends core NotificationsService and provides example notification templates.

    To add your own notifications:
    1. Create notification classes in templates.py that inherit from NotificationTemplate
    2. Add them to MORNING_NOTIFICATIONS or EVENING_NOTIFICATIONS lists
    3. Optionally override get_morning_notifications_with_promotions() for dynamic notifications
    """

    # Notification timing configuration
    MORNING_HOUR = 10  # 10am local time
    EVENING_HOUR = 19  # 7pm local time

    # Example notification templates - replace with your app's notifications
    MORNING_NOTIFICATIONS = [
        ExampleDailyNotification,
    ]
    EVENING_NOTIFICATIONS = [
        ExampleEngagementNotification,
    ]

    # Optional: Override these methods to add promotional broadcasts or dynamic notifications
    # def get_morning_notifications_with_promotions(self):
    #     """Get morning notifications including promotional broadcasts"""
    #     notifications = self.MORNING_NOTIFICATIONS.copy()
    #     # Add promotional broadcast notification class with higher priority
    #     # notifications.insert(0, PromotionalBroadcastNotification)
    #     return notifications
    #
    # def get_evening_notifications_with_promotions(self):
    #     """Get evening notifications including promotional broadcasts"""
    #     notifications = self.EVENING_NOTIFICATIONS.copy()
    #     # Add promotional broadcast notification class with higher priority
    #     # notifications.insert(0, PromotionalBroadcastNotification)
    #     return notifications
