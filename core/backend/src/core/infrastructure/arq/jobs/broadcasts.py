"""Core user-broadcast worker job: the admin panel's "send now" and the bots' ``/broadcast``.

One job for every app (apps re-export it from ``app.worker.jobs`` and register it in
``worker.py`` as ``func(user_broadcast_job, name="user_broadcast_job",
timeout=USER_BROADCAST_JOB_TIMEOUT)``: the worker-wide ``job_timeout`` is far too short for a
whole audience). Delivery goes through the notification engine
(``NotificationsService.send_attempts`` → ``MessageService.send_content``, then
``record_attempts``): one ``notification_deliveries`` row per recipient, blocked bots skipped
and flagged, the keyboard built per user in their language.

Transactions, per chunk of ``CHUNK_SIZE`` users: the sends run outside any transaction, then
the chunk's delivery rows and the saved row's counters go in one short transaction.

Stops and re-runs. Every run has a ``run_id`` (from the payload, else the arq job id) and logs
its deliveries under a per-run message key; a re-run of the same job skips whoever the run
already reached. arq re-runs a job interrupted by a worker restart (a deploy), but NOT one that
hit its timeout. Either way the job gets cancelled: it then records what the in-flight chunk
had already sent, tells the requester how far it got, and re-raises. A new send-now is a new
run and goes to everyone again.
"""

import asyncio
from dataclasses import dataclass
from itertools import batched
from uuid import uuid4

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.database.models.enums import NotificationSlot
from core.infrastructure.i18n import t
from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema
from core.services.broadcast_formatting import broadcast_content
from core.services.messages import user_language
from core.services.notifications.broadcasts import ImmediateBroadcastNotification
from core.services.notifications.service import DeliveryAttempt, NotificationsService

logger = get_logger(__name__)

CHUNK_SIZE = 100  # users per send phase + recording transaction
_MESSAGE_KEY_MAX = 128  # notification_deliveries.message_key

USER_BROADCAST_JOB_TIMEOUT = 12 * 60 * 60
"""Seconds ``user_broadcast_job`` may run (apps register it with ``func(..., timeout=...)``).

A send takes ~0.1-0.2 s (the engine's pause plus the Telegram call), so 12 h covers a few
hundred thousand users; the worker-wide default (600 s) stops it after a few thousand.
"""


def broadcast_message_key(run_id: str, broadcast_id: int | None = None) -> str:
    """The delivery-log key of one run (a saved row's runs keep its id in the key)."""
    key = f"promotional_broadcast.{broadcast_id}.{run_id}" if broadcast_id is not None else f"broadcast_now.{run_id}"
    return key[:_MESSAGE_KEY_MAX]


@dataclass
class _Progress:
    total: int = 0
    delivered: int = 0
    failed: int = 0

    @property
    def rate(self) -> float:
        return round(self.delivered / self.total * 100, 1) if self.total else 0.0


@inject_context
async def user_broadcast_job(
    ctx: WorkerContext,
    broadcast_data: dict,
    requester_telegram_id: int | None = None,
    broadcast_id: int | None = None,
):
    """Send a broadcast to every user who can get it (in Telegram, bot not blocked).

    Args:
        broadcast_data: The content (``broadcast_content`` keys), ``keyboard_type`` /
            ``keyboard_button_text`` and ``run_id``. The bots' legacy keys still work.
        requester_telegram_id: Who gets the completion (or failure / stopped) message.
        broadcast_id: The saved ``promotional_broadcasts`` row this run sends, if any: its
            counters move per chunk (one cycle per run).
    """
    logger.info(f"Job started: user_broadcast - Type: {broadcast_data.get('message_type')}, row: {broadcast_id}")
    template_name = ImmediateBroadcastNotification.TEMPLATE_NAME
    progress = _Progress()
    try:
        content = broadcast_content(broadcast_data)
        keyboard = {
            "keyboard_type": broadcast_data.get("keyboard_type"),
            "keyboard_button_text": broadcast_data.get("keyboard_button_text"),
        }
        run_id = broadcast_data.get("run_id") or ctx.ctx_dict.get("job_id") or uuid4().hex
        message_key = broadcast_message_key(str(run_id), broadcast_id)
        template = ImmediateBroadcastNotification(content, keyboard, message_key)

        # Short transaction: the audience, and whom this run already reached (a re-run).
        async with ctx.with_transaction() as services:
            audience = [UserSchema.model_validate(u) for u in await services.repo.users.get_broadcast_audience()]
            deliveries = services.repo.notification_deliveries
            earlier_rows = await deliveries.count_for_key(template_name, message_key)
            reached = await deliveries.delivered_user_ids(template_name, message_key) if earlier_rows else set()
        if earlier_rows:
            logger.warning(f"user_broadcast {message_key}: resuming, {len(reached)} users already reached")

        progress.total = len(audience)
        progress.delivered = len(reached)
        pending = [u for u in audience if u.id not in reached]
        new_cycle = earlier_rows == 0
        for chunk in batched(pending, CHUNK_SIZE):
            attempts: list[DeliveryAttempt] = []
            try:
                # No transaction while the chunk's Telegram sends run.
                async with ctx.without_transaction() as services:
                    engine = NotificationsService(services.repo, services.producer, services, services.bot)
                    await engine.send_attempts(template.initialize(services), list(chunk), attempts)
            except BaseException:
                # Stopped mid-chunk (cancelled by the timeout or a worker restart): log whoever
                # already got it, so the counters stay true and a re-run skips them.
                await _record_chunk(ctx, template, attempts, broadcast_id, new_cycle, progress)
                raise
            if await _record_chunk(ctx, template, attempts, broadcast_id, new_cycle, progress):
                new_cycle = False

        await _notify_requester(
            ctx,
            requester_telegram_id,
            "core.admin.broadcasts.done",
            sent=progress.delivered,
            total=progress.total,
            rate=f"{progress.rate:.1f}",
        )
        logger.info(
            f"Job completed: user_broadcast - Sent to {progress.delivered}/{progress.total} users ({progress.rate:.1f}%)"
        )
        return {
            "sent": progress.delivered,
            "total": progress.total,
            "failed": progress.failed,
            "success_rate": progress.rate,
        }

    except asyncio.CancelledError:
        # arq doesn't retry a timed-out job, and `except Exception` doesn't see a cancellation.
        logger.warning(f"Job cancelled: user_broadcast - stopped at {progress.delivered}/{progress.total} users")
        await _notify_requester(
            ctx, requester_telegram_id, "core.admin.broadcasts.stopped", sent=progress.delivered, total=progress.total
        )
        raise
    except Exception as e:
        logger.error(f"Job failed: user_broadcast - {e}", exc_info=True)
        await _notify_requester(ctx, requester_telegram_id, "core.admin.broadcasts.failed", error=str(e))
        raise


async def _record_chunk(
    ctx: WorkerContext,
    template: ImmediateBroadcastNotification,
    attempts: list[DeliveryAttempt],
    broadcast_id: int | None,
    new_cycle: bool,
    progress: _Progress,
) -> bool:
    """Short transaction: a chunk's delivery rows and the saved row's counters. False if nothing was sent."""
    if not attempts:
        return False
    async with ctx.with_transaction() as services:
        engine = NotificationsService(services.repo, services.producer, services, services.bot)
        sent = await engine.record_attempts(template.initialize(services), attempts, NotificationSlot.OTHER)
        failed = len(attempts) - sent
        if broadcast_id is not None:
            await services.repo.promotional_broadcasts.record_send_result(
                broadcast_id, sent, failed, new_cycle=new_cycle
            )
    progress.delivered += sent
    progress.failed += failed
    return True


async def _notify_requester(ctx: WorkerContext, telegram_id: int | None, key: str, **values) -> None:
    """Tell the admin who started the broadcast how it went, in their language. Never raises."""
    if not telegram_id:
        return
    try:
        async with ctx.with_transaction() as services:
            user = await services.repo.users.get_by_telegram_id(telegram_id)
            locale = user_language(UserSchema.model_validate(user)) if user else "en"
        async with ctx.without_transaction() as services:
            await services.messages.send_message(telegram_id, t(key, locale, **values))
    except Exception:
        logger.exception(f"user_broadcast: could not notify the requester {telegram_id}")
