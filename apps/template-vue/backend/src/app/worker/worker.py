"""Template ARQ worker application."""

from app.infrastructure import setup_infrastructure
from core.infrastructure.config import settings

setup_infrastructure()

from arq import cron, func

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.worker.jobs import (
    admin_broadcast_job,
    charge_expiring_subscriptions_job,
    daily_admin_statistics_job,
    expire_outdated_subscriptions_job,
    send_delayed_notification,
    test_error_job,
    user_broadcast_job,
)
from core.infrastructure.arq import create_worker_settings
from core.infrastructure.arq.jobs import (
    USER_BROADCAST_JOB_TIMEOUT,
    backup_database_job,
    evening_notification_job,
    marketing_links_alerts_job,
    morning_notification_job,
    scheduled_backup_job,
)
from core.infrastructure.dependencies import Dependencies

# Cron schedules
notification_job_cron = {"minute": 0}  # Every hour at :00 (each user's local morning/evening hour)
payment_job_cron = {"minute": (0), "hour": (0, 6, 12, 18)}
expire_outdated_subscriptions_job_cron = {"minute": (5), "hour": (0)}
daily_statistics_job_cron = {"minute": (55), "hour": (1)}  # Daily at 1:55 UTC
backup_job_cron = {"minute": 0, "hour": 2}  # Daily at 2:00 UTC
marketing_alerts_cron = {"minute": 20}  # Every hour at :20 (owner alerts; silent without RBAC__OWNER_IDS)


# Create worker with auto-managed dependencies
WorkerSettings = create_worker_settings(
    bot_config=settings.bot,
    db_config=settings.db,
    redis_config=settings.redis,
    repo_class=RequestsRepo,
    service_class=RequestsService,
    job_functions=[
        admin_broadcast_job,
        backup_database_job,
        scheduled_backup_job,
        # A whole-audience blast outlives the worker-wide job_timeout.
        func(user_broadcast_job, name="user_broadcast_job", timeout=USER_BROADCAST_JOB_TIMEOUT),
        morning_notification_job,
        evening_notification_job,
        daily_admin_statistics_job,
        charge_expiring_subscriptions_job,
        expire_outdated_subscriptions_job,
        marketing_links_alerts_job,
        send_delayed_notification,
        test_error_job,
    ],
    cron_jobs=[
        cron(morning_notification_job, **notification_job_cron),
        cron(evening_notification_job, **notification_job_cron),
        cron(charge_expiring_subscriptions_job, **payment_job_cron),
        cron(expire_outdated_subscriptions_job, **expire_outdated_subscriptions_job_cron),
        cron(daily_admin_statistics_job, **daily_statistics_job_cron),
        cron(scheduled_backup_job, **backup_job_cron),
        cron(marketing_links_alerts_job, **marketing_alerts_cron),
    ],
    dependencies=Dependencies(
        redis_config=settings.redis,
        rabbit_config=settings.rabbit,
    ),
)
