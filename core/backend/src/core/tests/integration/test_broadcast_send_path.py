"""The one broadcast send path: ``user_broadcast_job`` and the scheduled promo templates.

Real Postgres through a worker context (each ``with_transaction`` commits, like
production), the core aggregators and a capturing ``MockBot``. No ``app`` imports.
"""

import asyncio
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine

from core.exceptions import InvalidBroadcastException
from core.infrastructure.arq.jobs.broadcasts import broadcast_message_key, user_broadcast_job
from core.infrastructure.database.models import NotificationDelivery, PromotionalBroadcast, User
from core.infrastructure.database.models.enums import NotificationSlot, NotificationTimeSlot
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.i18n import t
from core.schemas.users import UserSchema
from core.services import broadcast_formatting
from core.services.notifications import NotificationsService
from core.services.notifications import service as engine_module
from core.services.notifications.broadcasts import (
    EveningPromotionalBroadcast,
    ImmediateBroadcastNotification,
    MorningPromotionalBroadcast,
)
from core.services.requests import CoreRequestsService
from core.testing.fixtures.worker import MockBot, create_worker_context

pytestmark = pytest.mark.business_logic

REQUESTER = 4242


APP_URL = "https://t.me/test_bot/app"


@pytest.fixture(autouse=True)
def app_url(monkeypatch):
    """The ``main`` button's link without loading app settings (core-only CI has no ``app``)."""
    monkeypatch.setattr(broadcast_formatting, "_app_url", lambda: APP_URL)


class ForbiddingBot(MockBot):
    """MockBot whose sends to ``blocked`` chat ids fail like a user who blocked the bot."""

    def __init__(self, blocked: set[int]):
        super().__init__()
        self.blocked = blocked

    async def send_message(self, chat_id: int, text: str, **kwargs):
        if chat_id in self.blocked:
            raise TelegramForbiddenError(method=SendMessage(chat_id=chat_id, text=text), message="Forbidden: blocked")
        return await super().send_message(chat_id, text, **kwargs)


class StoppingBot(MockBot):
    """MockBot that gets cancelled (like arq's timeout or a worker restart) on its ``stop_at``-th user send."""

    def __init__(self, stop_at: int):
        super().__init__()
        self.stop_at = stop_at
        self.user_sends = 0

    async def send_message(self, chat_id: int, text: str, **kwargs):
        if chat_id != REQUESTER:
            self.user_sends += 1
            if self.user_sends == self.stop_at:
                raise asyncio.CancelledError
        return await super().send_message(chat_id, text, **kwargs)


class ConnectionCountingBot(MockBot):
    """MockBot that notes how many DB connections are checked out at each user send."""

    def __init__(self, engine: AsyncEngine):
        super().__init__()
        self.open_connections = 0
        self.seen: list[int] = []
        event.listen(engine.sync_engine, "checkout", self._out)
        event.listen(engine.sync_engine, "checkin", self._in)
        self._engine = engine

    def _out(self, *_):
        self.open_connections += 1

    def _in(self, *_):
        self.open_connections -= 1

    def detach(self):
        event.remove(self._engine.sync_engine, "checkout", self._out)
        event.remove(self._engine.sync_engine, "checkin", self._in)

    async def send_message(self, chat_id: int, text: str, **kwargs):
        if chat_id != REQUESTER:
            self.seen.append(self.open_connections)
        return await super().send_message(chat_id, text, **kwargs)


@pytest.fixture(autouse=True)
def no_send_delay(monkeypatch):
    monkeypatch.setattr(engine_module, "SEND_INTERVAL_SECONDS", 0)


@pytest.fixture
def bot() -> MockBot:
    return MockBot()


@pytest.fixture
async def worker_ctx(db_engine: AsyncEngine, bot: MockBot):
    return await create_worker_context(
        db_engine,
        bot,
        CoreRequestsRepo,
        lambda repo, bot: CoreRequestsService(repo, bot=bot),
        clean_tables=["notification_deliveries", "promotional_broadcasts", "users"],
    )


async def _users(worker_ctx, count: int, **fields) -> list[User]:
    created = []
    async with worker_ctx.with_transaction() as services:
        for _ in range(count):
            created.append(
                await services.repo.users.create(
                    {
                        "username": f"b_{uuid4().hex[:10]}",
                        "telegram_id": random.randint(10**9, 10**10),
                        **fields,
                    }
                )
            )
    return created


async def _deliveries(worker_ctx) -> list[NotificationDelivery]:
    async with worker_ctx.with_repo() as repo:
        return list((await repo.session.execute(select(NotificationDelivery))).scalars().all())


async def _broadcast(worker_ctx, **fields) -> PromotionalBroadcast:
    async with worker_ctx.with_transaction() as services:
        return await services.repo.promotional_broadcasts.create(
            {
                "message_type": "text",
                "message_text": "Saved",
                "message_html": "Saved",
                "has_text_formatting": False,
                "time_slot": NotificationTimeSlot.MORNING,
                "deadline": datetime.now(UTC) + timedelta(days=1),
                "priority": 80,
                "created_by_user_id": REQUESTER,
                "keyboard_type": "none",
                **fields,
            }
        )


async def _reload(worker_ctx, broadcast_id: int) -> PromotionalBroadcast:
    async with worker_ctx.with_repo() as repo:
        return await repo.promotional_broadcasts.get_by_id(broadcast_id)


def _to_users(bot: MockBot) -> list:
    return [m for m in bot.messages if m.chat_id != REQUESTER]


class TestUserBroadcastJob:
    async def test_text_reaches_everyone_and_logs_each_delivery(self, worker_ctx, bot):
        users = await _users(worker_ctx, 2)

        result = await user_broadcast_job(
            worker_ctx.ctx_dict, {"message_type": "text", "message_text": "Hi all", "run_id": "r1"}, REQUESTER
        )

        assert result == {"sent": 2, "total": 2, "failed": 0, "success_rate": 100.0}
        assert sorted(m.chat_id for m in _to_users(bot)) == sorted(u.telegram_id for u in users)
        assert all(m.text == "Hi all" and m.kwargs.get("parse_mode") is None for m in _to_users(bot))
        rows = await _deliveries(worker_ctx)
        assert {(r.template, r.message_key, r.slot, r.delivered) for r in rows} == {
            ("ImmediateBroadcastNotification", "broadcast_now.r1", str(NotificationSlot.OTHER), True)
        }
        assert len(rows) == 2
        [done] = [m for m in bot.messages if m.chat_id == REQUESTER]
        assert done.text == t("core.admin.broadcasts.done", "en", sent=2, total=2, rate="100.0")

    async def test_every_media_type_is_sent(self, worker_ctx, bot):
        await _users(worker_ctx, 1)

        for media_type in ("video", "animation", "document"):
            await user_broadcast_job(
                worker_ctx.ctx_dict,
                {"message_type": media_type, "media_file_id": f"file-{media_type}", "caption": "c"},
                REQUESTER,
            )

        assert [(m.kwargs["media_type"], m.photo, m.text) for m in bot.media] == [
            ("video", "file-video", "c"),
            ("animation", "file-animation", "c"),
            ("document", "file-document", "c"),
        ]

    async def test_legacy_bot_photo_payload(self, worker_ctx, bot):
        await _users(worker_ctx, 1)

        result = await user_broadcast_job(
            worker_ctx.ctx_dict,
            {
                "message_type": "photo",
                "photo_file_id": "AgAC",
                "caption": "Look",
                "caption_html": "<b>Look</b>",
                "has_caption_formatting": True,
                "keyboard_type": "none",
            },
            REQUESTER,
        )

        assert result["sent"] == 1
        [photo] = bot.photos
        assert (photo.photo, photo.text, photo.kwargs.get("parse_mode")) == ("AgAC", "<b>Look</b>", "HTML")

    async def test_blocked_users_are_skipped_and_new_blocks_flagged(self, db_engine, worker_ctx):
        [reachable, newly_blocked] = await _users(worker_ctx, 2)
        await _users(worker_ctx, 1, bot_blocked_at=datetime.now(UTC))
        bot = ForbiddingBot(blocked={newly_blocked.telegram_id})
        ctx = await create_worker_context(
            db_engine, bot, CoreRequestsRepo, lambda repo, bot: CoreRequestsService(repo, bot=bot)
        )

        result = await user_broadcast_job(ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, REQUESTER)

        assert (result["sent"], result["total"], result["failed"]) == (1, 2, 1)
        assert [m.chat_id for m in _to_users(bot)] == [reachable.telegram_id]
        async with ctx.with_repo() as repo:
            flagged = await repo.users.get_by_telegram_id(newly_blocked.telegram_id)
        assert flagged.bot_blocked_at is not None
        rows = {r.user_id: r for r in await _deliveries(ctx)}
        assert rows[newly_blocked.id].error_code == "forbidden"

    async def test_saved_row_counts_one_cycle(self, worker_ctx, bot):
        await _users(worker_ctx, 3)
        row = await _broadcast(worker_ctx)

        await user_broadcast_job(
            worker_ctx.ctx_dict, {"message_type": "text", "message_text": "Saved", "run_id": "r2"}, REQUESTER, row.id
        )

        row = await _reload(worker_ctx, row.id)
        assert (row.sent_count, row.success_count, row.fail_count, row.cycles_run) == (3, 3, 0, 1)
        assert row.last_sent_at is not None
        assert {r.message_key for r in await _deliveries(worker_ctx)} == {broadcast_message_key("r2", row.id)}

    async def test_counts_land_per_chunk(self, worker_ctx, bot, monkeypatch):
        monkeypatch.setattr("core.infrastructure.arq.jobs.broadcasts.CHUNK_SIZE", 2)
        await _users(worker_ctx, 5)
        row = await _broadcast(worker_ctx)

        result = await user_broadcast_job(
            worker_ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, REQUESTER, row.id
        )

        assert result["sent"] == 5
        row = await _reload(worker_ctx, row.id)
        assert (row.success_count, row.cycles_run) == (5, 1)

    async def test_a_rerun_of_the_same_run_sends_nothing_twice(self, worker_ctx, bot):
        """arq re-runs a cancelled job from the start (e.g. a deploy restarts the worker)."""
        await _users(worker_ctx, 2)
        row = await _broadcast(worker_ctx)
        payload = {"message_type": "text", "message_text": "Once", "run_id": "same-run"}
        await user_broadcast_job(worker_ctx.ctx_dict, payload, REQUESTER, row.id)
        late = await _users(worker_ctx, 1)
        bot.messages.clear()

        result = await user_broadcast_job(worker_ctx.ctx_dict, payload, REQUESTER, row.id)

        assert [m.chat_id for m in _to_users(bot)] == [late[0].telegram_id]  # only who the run hadn't reached
        assert (result["sent"], result["total"]) == (3, 3)
        row = await _reload(worker_ctx, row.id)
        assert (row.success_count, row.cycles_run) == (3, 1)

    async def test_sends_run_outside_any_transaction(self, db_engine, worker_ctx, monkeypatch):
        """Slow Telegram sends must not hold a DB connection (and an open transaction)."""
        monkeypatch.setattr("core.infrastructure.arq.jobs.broadcasts.CHUNK_SIZE", 2)
        await _users(worker_ctx, 3)
        row = await _broadcast(worker_ctx)
        bot = ConnectionCountingBot(db_engine)
        ctx = await create_worker_context(
            db_engine, bot, CoreRequestsRepo, lambda repo, bot: CoreRequestsService(repo, bot=bot)
        )
        try:
            result = await user_broadcast_job(
                ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, REQUESTER, row.id
            )
        finally:
            bot.detach()

        assert result["sent"] == 3
        assert bot.seen == [0, 0, 0]
        row = await _reload(worker_ctx, row.id)
        assert (row.success_count, row.cycles_run) == (3, 1)
        assert len(await _deliveries(worker_ctx)) == 3

    async def test_cancelled_mid_chunk_records_what_went_out_and_tells_the_requester(self, db_engine, worker_ctx):
        """arq cancels the job on its timeout (no retry) or a worker restart (retried later)."""
        await _users(worker_ctx, 4)
        row = await _broadcast(worker_ctx)
        bot = StoppingBot(stop_at=3)
        ctx = await create_worker_context(
            db_engine, bot, CoreRequestsRepo, lambda repo, bot: CoreRequestsService(repo, bot=bot)
        )
        payload = {"message_type": "text", "message_text": "x", "run_id": "stopped-run"}

        with pytest.raises(asyncio.CancelledError):
            await user_broadcast_job(ctx.ctx_dict, payload, REQUESTER, row.id)

        reached = {r.user_id for r in await _deliveries(ctx) if r.delivered}
        assert len(reached) == 2  # the two sends before the stop are logged
        row = await _reload(ctx, row.id)
        assert (row.sent_count, row.success_count, row.cycles_run) == (2, 2, 1)
        [stopped] = [m for m in bot.messages if m.chat_id == REQUESTER]
        assert stopped.text == t("core.admin.broadcasts.stopped", "en", sent=2, total=4)

        # The worker re-runs the same job: only the two not reached yet get it.
        bot.stop_at = 0
        sent_before = {m.chat_id for m in _to_users(bot)}
        result = await user_broadcast_job(ctx.ctx_dict, payload, REQUESTER, row.id)

        assert (result["sent"], result["total"]) == (4, 4)
        assert len({m.chat_id for m in _to_users(bot)} - sent_before) == 2
        row = await _reload(ctx, row.id)
        assert (row.success_count, row.cycles_run) == (4, 1)

    async def test_without_run_id_the_arq_job_id_keys_the_run(self, worker_ctx, bot):
        await _users(worker_ctx, 1)
        worker_ctx.ctx_dict["job_id"] = "arq-job-7"

        await user_broadcast_job(worker_ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, REQUESTER)
        await user_broadcast_job(worker_ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, REQUESTER)

        assert len(_to_users(bot)) == 1
        assert {r.message_key for r in await _deliveries(worker_ctx)} == {"broadcast_now.arq-job-7"}

    async def test_keyboard_is_built_per_user_in_their_language(self, worker_ctx, bot):
        [ru_user] = await _users(worker_ctx, 1, language_code="ru")
        [en_user] = await _users(worker_ctx, 1, language_code="en")

        await user_broadcast_job(
            worker_ctx.ctx_dict, {"message_type": "text", "message_text": "x", "keyboard_type": "main"}, REQUESTER
        )

        labels = {m.chat_id: m.kwargs["reply_markup"].inline_keyboard[0][0] for m in _to_users(bot)}
        assert labels[ru_user.telegram_id].text == t("core.admin.broadcasts.open_app", "ru")
        assert labels[en_user.telegram_id].text == "Open App"
        assert labels[ru_user.telegram_id].url == APP_URL

    async def test_requester_is_answered_in_their_language(self, worker_ctx, bot):
        [owner] = await _users(worker_ctx, 1, language_code="ru")

        await user_broadcast_job(worker_ctx.ctx_dict, {"message_type": "text", "message_text": "x"}, owner.telegram_id)

        done = [m for m in bot.messages if m.chat_id == owner.telegram_id][-1]
        assert done.text == t("core.admin.broadcasts.done", "ru", sent=1, total=1, rate="100.0")

    async def test_invalid_payload_tells_the_requester_and_raises(self, worker_ctx, bot):
        await _users(worker_ctx, 1)

        with pytest.raises(InvalidBroadcastException):
            await user_broadcast_job(worker_ctx.ctx_dict, {"message_type": "video"}, REQUESTER)

        assert _to_users(bot) == []
        [failed] = [m for m in bot.messages if m.chat_id == REQUESTER]
        assert failed.text.startswith("❌")
        assert "Media send-now requires media_file_id" in failed.text


class TestScheduledPromoTemplate:
    async def _send(self, worker_ctx, template, users: list[UserSchema]) -> int:
        async with worker_ctx.with_transaction() as services:
            engine = NotificationsService(services.repo, None, services, services.bot)
            sent, _ = await engine.send_notification(
                template.initialize(services), users, slot=NotificationSlot.MORNING
            )
        return sent

    async def test_top_priority_row_of_the_slot_is_sent_and_counted(self, worker_ctx, bot):
        users = [UserSchema.model_validate(u) for u in await _users(worker_ctx, 2)]
        await _broadcast(worker_ctx, message_text="low", message_html="low", priority=10)
        top = await _broadcast(worker_ctx, message_text="top", message_html="top", priority=500)
        await _broadcast(
            worker_ctx,
            message_text="evening",
            message_html="evening",
            priority=999,
            time_slot=NotificationTimeSlot.EVENING,
        )

        sent = await self._send(worker_ctx, MorningPromotionalBroadcast(), users)

        assert sent == 2
        assert {m.text for m in bot.messages} == {"top"}
        top = await _reload(worker_ctx, top.id)
        assert (top.success_count, top.cycles_run) == (2, 1)
        rows = await _deliveries(worker_ctx)
        assert {(r.template, r.message_key) for r in rows} == {
            ("PromotionalBroadcastNotification", f"promotional_broadcast.{top.id}")
        }

    async def test_filter_audience_is_the_app_override_point(self, worker_ctx, bot):
        [keep, drop] = [UserSchema.model_validate(u) for u in await _users(worker_ctx, 2)]
        await _broadcast(worker_ctx, time_slot=NotificationTimeSlot.EVENING)

        class OnlyKeep(EveningPromotionalBroadcast):
            async def filter_audience(self, users):
                return [u for u in users if u.id == keep.id]

        await self._send(worker_ctx, OnlyKeep(), [keep, drop])

        assert [m.chat_id for m in bot.messages] == [keep.telegram_id]

    async def test_keyboard_comes_from_the_registry(self, worker_ctx, bot, monkeypatch):
        keyboards = dict(broadcast_formatting._KEYBOARDS)
        monkeypatch.setattr(broadcast_formatting, "_KEYBOARDS", keyboards)
        broadcast_formatting.register_broadcast_keyboard(
            "daily", lambda _text, locale: broadcast_formatting._open_app_keyboard(f"daily-{locale}", locale)
        )
        users = [UserSchema.model_validate(u) for u in await _users(worker_ctx, 1, language_code="ru")]
        await _broadcast(worker_ctx, keyboard_type="daily")

        await self._send(worker_ctx, MorningPromotionalBroadcast(), users)

        [message] = bot.messages
        assert message.kwargs["reply_markup"].inline_keyboard[0][0].text == "daily-ru"

    async def test_no_active_row_sends_nothing(self, worker_ctx, bot):
        users = [UserSchema.model_validate(u) for u in await _users(worker_ctx, 1)]
        await _broadcast(worker_ctx, is_active=False)

        assert await self._send(worker_ctx, MorningPromotionalBroadcast(), users) == 0
        assert bot.messages == []


def test_immediate_template_is_not_a_promo_template():
    """Its counters are recorded by the job per chunk; the promo template would record them again."""
    from core.services.notifications.broadcasts import PromotionalBroadcastNotification

    assert not issubclass(ImmediateBroadcastNotification, PromotionalBroadcastNotification)
    assert ImmediateBroadcastNotification({}, None, "k").get_posthog_event() is None
