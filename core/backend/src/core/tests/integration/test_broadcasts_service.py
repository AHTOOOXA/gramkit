"""BroadcastsService on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session), bot=api_bot_mock(), arq=…)``
directly (core has no ``services`` fixture). Covers the rules with one home in the
service: 'both' makes two rows, the audit rows of every mutation, domain errors instead
of HTTP errors, and send-now's job payload.
"""

import random
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BroadcastNotFoundException, InvalidBroadcastException
from core.infrastructure.database.models import AuditLog
from core.infrastructure.database.models.enums import NotificationTimeSlot, UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.broadcasts import (
    BroadcastCreateRequest,
    BroadcastPreviewRequest,
    BroadcastPreviewResponse,
    BroadcastSendNowRequest,
    BroadcastUpdateRequest,
)
from core.schemas.users import UserSchema
from core.services import broadcast_formatting
from core.services import broadcasts as broadcasts_module
from core.services.requests import CoreRequestsService
from core.testing.fixtures.bot import api_bot_mock

pytestmark = pytest.mark.business_logic


APP_URL = "https://t.me/test_bot/app"


@pytest.fixture(autouse=True)
def app_url(monkeypatch):
    """The ``main`` button's link without loading app settings (core-only CI has no ``app``)."""
    monkeypatch.setattr(broadcast_formatting, "_app_url", lambda: APP_URL)


@pytest.fixture
def arq() -> MagicMock:
    return MagicMock(enqueue_job=AsyncMock(return_value=MagicMock(job_id="job-1")))


@pytest.fixture
def services(db_session: AsyncSession, arq: MagicMock) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session), bot=api_bot_mock(), arq=arq)


async def _actor(services: CoreRequestsService, role: UserRole = UserRole.OWNER) -> UserSchema:
    user = await services.repo.users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"bcast_{uuid4().hex[:8]}",
            "role": role,
        }
    )
    await services.repo.session.flush()
    return UserSchema.model_validate(user)


def _create_body(time_slot: str = "morning", **overrides) -> BroadcastCreateRequest:
    return BroadcastCreateRequest(
        **{
            "message_type": "text",
            "time_slot": time_slot,
            "deadline": datetime.now(UTC) + timedelta(days=3),
            "priority": 80,
            "message_text": "Hello",
            "has_text_formatting": False,
            "keyboard_type": "none",
            **overrides,
        }
    )


async def _audit_rows(services: CoreRequestsService, action: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.action == action, AuditLog.target_type == "broadcast")
    return list((await services.repo.session.execute(stmt)).scalars().all())


def _detail(audit: AuditLog) -> dict:
    assert audit.detail is not None
    return audit.detail


class TestCreate:
    async def test_both_creates_two_independent_rows_and_one_audit_row(self, services):
        actor = await _actor(services)

        result = await services.broadcasts.create(actor, _create_body("both"))

        assert len(result.ids) == 2
        rows = await services.repo.promotional_broadcasts.get_by_ids(result.ids)
        assert sorted(str(r.time_slot) for r in rows) == sorted(
            [str(NotificationTimeSlot.EVENING), str(NotificationTimeSlot.MORNING)]
        )
        assert all(r.created_by_user_id == actor.telegram_id for r in rows)
        [audit] = await _audit_rows(services, "broadcast_create")
        assert audit.target_id == ",".join(str(i) for i in result.ids)
        assert _detail(audit)["rows_created"] == 2
        assert _detail(audit)["ids"] == result.ids

    async def test_actor_without_telegram_id_is_invalid_not_a_500(self, services):
        """created_by_user_id is NOT NULL: a web-only admin used to hit an IntegrityError (500)."""
        actor = UserSchema(id=uuid4(), telegram_id=None)
        with pytest.raises(InvalidBroadcastException, match="Acting admin has no Telegram id"):
            await services.broadcasts.create(actor, _create_body())

    async def test_actor_with_a_telegram_id_beyond_int4_is_stored(self, services):
        """Newer Telegram ids exceed 2**31; created_by_user_id is BIGINT."""
        actor = await _actor(services)
        actor = actor.model_copy(update={"telegram_id": 7_934_526_008})
        result = await services.broadcasts.create(actor, _create_body())
        rows = await services.repo.promotional_broadcasts.get_by_creator(7_934_526_008)
        assert sorted(r.id for r in rows) == sorted(result.ids)

    async def test_text_without_text_is_invalid(self, services):
        actor = await _actor(services)
        with pytest.raises(InvalidBroadcastException, match="Text broadcast requires message_text"):
            await services.broadcasts.create(actor, _create_body(message_text=""))


class TestCancelAndEdit:
    async def test_cancel_sets_inactive_and_audits(self, services):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids

        detail = await services.broadcasts.cancel(actor, broadcast_id)

        assert detail.is_active is False
        assert detail.completed_at is not None
        audits = await _audit_rows(services, "broadcast_cancel")
        assert [a.target_id for a in audits] == [str(broadcast_id)]

    async def test_cancel_of_an_inactive_row_is_a_no_op(self, services):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids
        first = await services.broadcasts.cancel(actor, broadcast_id)

        again = await services.broadcasts.cancel(actor, broadcast_id)

        assert again.completed_at == first.completed_at
        assert len(await _audit_rows(services, "broadcast_cancel")) == 1

    async def test_cancel_of_an_expired_row_is_a_no_op(self, services):
        actor = await _actor(services)
        body = _create_body(deadline=datetime.now(UTC) - timedelta(minutes=1))
        [broadcast_id] = (await services.broadcasts.create(actor, body)).ids

        detail = await services.broadcasts.cancel(actor, broadcast_id)

        assert (detail.is_active, detail.completed_at) == (False, None)
        assert await _audit_rows(services, "broadcast_cancel") == []

    @pytest.mark.parametrize("field", ["message_type", "deadline", "priority"])
    async def test_edit_rejects_null_for_a_not_null_column(self, services, field):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids

        with pytest.raises(InvalidBroadcastException, match=field):
            await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest.model_validate({field: None}))

    async def test_edit_text_without_the_flag_keeps_the_formatting(self, services):
        actor = await _actor(services)
        body = _create_body(message_text="<b>Hi</b>", has_text_formatting=True)
        [broadcast_id] = (await services.broadcasts.create(actor, body)).ids

        detail = await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest(message_text="<i>Hey</i>"))

        assert (detail.message_html, detail.has_text_formatting) == ("<i>Hey</i>", True)

    async def test_edit_caption_without_the_flag_keeps_the_formatting(self, services):
        actor = await _actor(services)
        body = _create_body(
            message_type="photo", message_text=None, media_file_id="f1", caption="<b>c</b>", has_caption_formatting=True
        )
        [broadcast_id] = (await services.broadcasts.create(actor, body)).ids

        detail = await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest(caption="<i>d</i>"))

        assert (detail.caption_html, detail.has_caption_formatting) == ("<i>d</i>", True)

    async def test_edit_only_the_flag(self, services):
        actor = await _actor(services)
        body = _create_body(message_text="<b>Hi</b>", has_text_formatting=True)
        [broadcast_id] = (await services.broadcasts.create(actor, body)).ids

        detail = await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest(has_text_formatting=False))

        assert (detail.message_text, detail.has_text_formatting) == ("<b>Hi</b>", False)

    async def test_edit_updates_and_audits(self, services):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids

        detail = await services.broadcasts.edit(
            actor, broadcast_id, BroadcastUpdateRequest(priority=300, message_text="Updated")
        )

        assert detail.priority == 300
        assert detail.message_text == "Updated"
        [audit] = await _audit_rows(services, "broadcast_edit")
        assert _detail(audit)["changed_fields"] == ["has_text_formatting", "message_html", "message_text", "priority"]

    async def test_edit_validates_the_merged_row(self, services):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids

        with pytest.raises(InvalidBroadcastException, match="photo broadcast requires media_file_id"):
            await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest(message_type="photo"))
        with pytest.raises(InvalidBroadcastException, match="Text broadcast requires message_text"):
            await services.broadcasts.edit(actor, broadcast_id, BroadcastUpdateRequest(message_text=""))

        detail = await services.broadcasts.edit(
            actor, broadcast_id, BroadcastUpdateRequest(message_type="photo", media_file_id="file-1")
        )
        assert (detail.message_type, detail.media_file_id) == ("photo", "file-1")

    async def test_expired_row_is_inactive_in_list_and_detail(self, services):
        actor = await _actor(services)
        body = _create_body(deadline=datetime.now(UTC) - timedelta(minutes=1))
        [broadcast_id] = (await services.broadcasts.create(actor, body)).ids

        listing = await services.broadcasts.list_broadcasts()
        detail = await services.broadcasts.get_broadcast(broadcast_id)

        assert broadcast_id in [b.id for b in listing.completed]
        assert [b.is_active for b in listing.completed if b.id == broadcast_id] == [False]
        assert detail is not None and detail.is_active is False

    @pytest.mark.parametrize("method", ["cancel", "edit", "get_stats"])
    async def test_missing_row_raises_not_found(self, services, method):
        actor = await _actor(services)
        calls = {
            "cancel": lambda: services.broadcasts.cancel(actor, 99999999),
            "edit": lambda: services.broadcasts.edit(actor, 99999999, BroadcastUpdateRequest(priority=1)),
            "get_stats": lambda: services.broadcasts.get_stats(99999999),
        }
        with pytest.raises(BroadcastNotFoundException, match="Broadcast not found"):
            await calls[method]()

    async def test_get_broadcast_missing_is_none(self, services):
        assert await services.broadcasts.get_broadcast(99999999) is None


class TestSendNow:
    async def test_enqueues_the_job_and_audits(self, services, arq):
        actor = await _actor(services)
        [broadcast_id] = (await services.broadcasts.create(actor, _create_body())).ids

        assert await services.broadcasts.send_now(actor, BroadcastSendNowRequest(broadcast_id=broadcast_id)) is True

        arq.enqueue_job.assert_awaited_once()
        assert arq.enqueue_job.await_args.args == ("user_broadcast_job",)
        kwargs = arq.enqueue_job.await_args.kwargs
        assert kwargs["requester_telegram_id"] == actor.telegram_id
        assert kwargs["broadcast_id"] == broadcast_id
        data = kwargs["broadcast_data"]
        assert (data["message_type"], data["message_text"], data["has_text_formatting"]) == ("text", "Hello", False)
        assert len(data["run_id"]) == 32  # one id per run: the job skips users the run already reached
        [audit] = await _audit_rows(services, "broadcast_send_now")
        assert audit.target_id == str(broadcast_id)
        assert _detail(audit)["from_broadcast_id"] == broadcast_id
        assert _detail(audit)["run_id"] == data["run_id"]

    async def test_audit_row_is_written_before_the_job_is_queued(self, services, arq):
        """Once queued the blast can't be taken back: nothing that can fail may come after the enqueue."""
        actor = await _actor(services)
        seen_at_enqueue: list[int] = []

        async def enqueue(*args, **kwargs):
            seen_at_enqueue.append(len(await _audit_rows(services, "broadcast_send_now")))
            return MagicMock(job_id="job-1")

        arq.enqueue_job.side_effect = enqueue

        await services.broadcasts.send_now(actor, BroadcastSendNowRequest(message_type="text", message_text="x"))

        assert seen_at_enqueue == [1]

    async def test_inline_media_keeps_its_type(self, services, arq):
        """Regression: every media type went out as ``photo_file_id`` and the job dropped all but photos."""
        actor = await _actor(services)
        body = BroadcastSendNowRequest(message_type="video", media_file_id="vid-1", caption="c", keyboard_type="main")

        await services.broadcasts.send_now(actor, body)

        kwargs = arq.enqueue_job.await_args.kwargs
        data = kwargs["broadcast_data"]
        assert kwargs["broadcast_id"] is None
        assert (data["message_type"], data["media_file_id"], data["keyboard_type"]) == ("video", "vid-1", "main")

    async def test_each_send_is_a_new_run(self, services, arq):
        actor = await _actor(services)
        body = BroadcastSendNowRequest(message_type="text", message_text="x")

        await services.broadcasts.send_now(actor, body)
        await services.broadcasts.send_now(actor, body)

        run_ids = {c.kwargs["broadcast_data"]["run_id"] for c in arq.enqueue_job.await_args_list}
        assert len(run_ids) == 2

    @pytest.mark.parametrize(
        "body,message",
        [
            (BroadcastSendNowRequest(message_type="text"), "Text send-now requires message_text"),
            (BroadcastSendNowRequest(message_type="photo"), "Media send-now requires media_file_id"),
        ],
    )
    async def test_inline_content_is_validated_before_queueing(self, services, arq, body, message):
        actor = await _actor(services)
        with pytest.raises(InvalidBroadcastException, match=message):
            await services.broadcasts.send_now(actor, body)
        arq.enqueue_job.assert_not_awaited()

    async def test_unknown_row_raises_not_found_and_queues_nothing(self, services, arq):
        actor = await _actor(services)
        with pytest.raises(BroadcastNotFoundException):
            await services.broadcasts.send_now(actor, BroadcastSendNowRequest(broadcast_id=99999999))
        arq.enqueue_job.assert_not_awaited()

    async def test_without_content_is_invalid(self, services, arq):
        actor = await _actor(services)
        with pytest.raises(InvalidBroadcastException, match="send-now requires broadcast_id or message_type"):
            await services.broadcasts.send_now(actor, BroadcastSendNowRequest())
        arq.enqueue_job.assert_not_awaited()


class TestPreview:
    async def test_failed_send_is_false_not_an_error(self, services):
        """A failed send returns a falsy SendFailure; the preview must turn it into ``sent: false``.

        Regression: BroadcastPreviewResponse(sent=SendFailure(...)) failed validation → 500.
        """
        services.bot.send_message = AsyncMock(
            side_effect=TelegramBadRequest(method=SendMessage(chat_id=1, text="x"), message="Bad Request: can't parse")
        )
        admin = UserSchema(id=uuid4(), telegram_id=1)
        body = BroadcastPreviewRequest(message_type="text", message_text="<b>broken", keyboard_type="none")

        sent = await services.broadcasts.preview(admin, body)

        assert sent is False
        assert BroadcastPreviewResponse(sent=sent).sent is False

    async def test_actor_without_telegram_chat_is_invalid(self, services):
        body = BroadcastPreviewRequest(message_type="text", message_text="x")
        with pytest.raises(InvalidBroadcastException, match="no Telegram chat"):
            await services.broadcasts.preview(UserSchema(id=uuid4()), body)

    async def test_media_preview_goes_through_send_content_with_the_keyboard(self, services):
        actor = await _actor(services)
        body = BroadcastPreviewRequest(
            message_type="animation",
            media_file_id="gif-1",
            caption="c",
            keyboard_type="main",
            keyboard_button_text="Go",
        )

        assert await services.broadcasts.preview(actor, body) is True

        services.bot.send_animation.assert_awaited_once()
        kwargs = services.bot.send_animation.await_args.kwargs
        assert (kwargs["animation"], kwargs["caption"]) == ("gif-1", "c")
        assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Go"


class TestUploadMedia:
    async def test_mints_a_file_id_and_deletes_the_upload_message(self, services):
        actor = await _actor(services)

        result = await services.broadcasts.upload_media(
            actor, message_type="video", filename="clip.mp4", content=b"\x00\x01"
        )

        assert result.file_id == "file_video_123"
        services.bot.delete_message.assert_awaited_once()

    async def test_file_over_the_telegram_limit_is_invalid_and_not_sent(self, services, monkeypatch):
        actor = await _actor(services)
        monkeypatch.setitem(broadcasts_module.UPLOAD_LIMITS, "video", 3)

        with pytest.raises(InvalidBroadcastException, match="File too large"):
            await services.broadcasts.upload_media(actor, message_type="video", filename="v.mp4", content=b"1234")
        services.bot.send_video.assert_not_awaited()

    def test_upload_limits_follow_the_bot_api(self):
        assert broadcasts_module.UPLOAD_LIMITS["photo"] == 10 * 1024 * 1024
        assert {broadcasts_module.UPLOAD_LIMITS[k] for k in ("video", "animation", "document")} == {50 * 1024 * 1024}

    async def test_telegram_failure_is_invalid(self, services):
        actor = await _actor(services)
        services.bot.send_photo = AsyncMock(side_effect=RuntimeError("telegram down"))
        with pytest.raises(InvalidBroadcastException, match="Failed to upload media via Telegram"):
            await services.broadcasts.upload_media(actor, message_type="photo", filename="p.jpg", content=b"x")
