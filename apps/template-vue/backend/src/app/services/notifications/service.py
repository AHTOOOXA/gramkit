"""Template notification service: scheduled promotional broadcasts, plus example templates.

This shows how to extend the core NotificationsService with app-specific notifications.
Replace the example notifications with your app's actual notification templates.
"""

from core.services.notifications.broadcasts import EveningPromotionalBroadcast, MorningPromotionalBroadcast
from core.services.notifications.service import NotificationsService as CoreNotificationsService


class NotificationsService(CoreNotificationsService):
    """
    Template application notification service.

    Each slot (``morning_notification_job`` / ``evening_notification_job``, hourly in
    worker.py) sends the users whose local time is ``MORNING_HOUR`` / ``EVENING_HOUR``
    at most one message, by priority. The scheduled broadcasts from the admin panel
    (/admin/broadcasts) go first: core's Morning/EveningPromotionalBroadcast send the
    slot's top active broadcast to everyone in the slot (subclass them and override
    ``filter_audience`` to narrow that).

    To add your own notifications:
    1. Create notification classes in templates.py that inherit from NotificationTemplate
       (``ExampleDailyNotification`` and ``ExampleEngagementNotification`` are examples)
    2. Add them to MORNING_NOTIFICATIONS or EVENING_NOTIFICATIONS
    """

    # Notification timing configuration
    MORNING_HOUR = 10  # 10am local time
    EVENING_HOUR = 19  # 7pm local time

    # Your regular notifications, e.g. [ExampleDailyNotification] / [ExampleEngagementNotification]
    # (app.services.notifications.templates). Empty, so users only get the broadcasts you schedule.
    MORNING_NOTIFICATIONS = []
    EVENING_NOTIFICATIONS = []

    def get_morning_notifications_with_promotions(self):
        """The scheduled morning broadcast first, then the regular morning notifications."""
        return [MorningPromotionalBroadcast, *self.MORNING_NOTIFICATIONS]

    def get_evening_notifications_with_promotions(self):
        """The scheduled evening broadcast first, then the regular evening notifications."""
        return [EveningPromotionalBroadcast, *self.EVENING_NOTIFICATIONS]
