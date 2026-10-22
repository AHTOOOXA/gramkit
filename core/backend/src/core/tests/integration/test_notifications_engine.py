"""Core notification engine: delivery log, blocked flag, recipients, one message per slot.

Real Postgres (``db_session``), a fake bot. No ``app`` imports (core CI runs without the app).
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import CommandObject
from aiogram.methods import SendMessage
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import NotificationDelivery, NotificationSlot, User
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.i18n import supported_locale
from core.infrastructure.telegram.handlers import start as start_handlers
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.messages import SendFailure, send_error_code, user_language
from core.services.notifications import NotificationsService, NotificationTemplate
from core.services.notifications import service as engine_module
from core.services.requests import CoreRequestsService
from core.services.users import is_valid_timezone

pytestmark = pytest.mark.business_logic


class FakeBot:
    """Records sends; raises Forbidden / BadRequest for the configured chat ids."""

    def __init__(self, forbidden=(), bad_request=()):
        self.forbidden = set(forbidden)
        self.bad_request = set(bad_request)
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):
        method = SendMessage(chat_id=chat_id, text=text)
        if chat_id in self.forbidden:
            raise TelegramForbiddenError(method=method, message="Forbidden: bot was blocked by the user")
        if chat_id in self.bad_request:
            raise TelegramBadRequest(method=method, message="Bad Request: chat not found")
        self.sent.append((chat_id, text))


class KeyPerUser(NotificationTemplate):
    """Key depends on the user, to prove keys are picked per user and logged."""

    def __init__(self):
        super().__init__()
        self._priority = 10

    async def get_message_key(self) -> str:
        return "core.test.default"

    async def get_message_key_for_user(self, user: UserSchema) -> str:
        return f"core.test.{user.username}"


class HighPriorityEveryone(NotificationTemplate):
    def __init__(self):
        super().__init__()
        self._priority = 100

    async def get_message_key(self) -> str:
        return "core.test.high"


class LowPriorityEveryone(NotificationTemplate):
    def __init__(self):
        super().__init__()
        self._priority = 1

    async def get_message_key(self) -> str:
        return "core.test.low"


class SendsOnlyToSome(NotificationTemplate):
    """pre_send_actions narrows the audience (e.g. to users a gift was actually credited to)."""

    def __init__(self, keep: set):
        super().__init__()
        self.keep = keep

    async def get_message_key(self) -> str:
        return "core.test.some"

    async def pre_send_actions(self, users: list[UserSchema]) -> list[UserSchema]:
        return [user for user in users if user.id in self.keep]


@pytest.fixture(autouse=True)
def no_send_delay(monkeypatch):
    monkeypatch.setattr(engine_module, "SEND_INTERVAL_SECONDS", 0)


def _engine(db_session: AsyncSession, bot: FakeBot) -> tuple[NotificationsService, CoreRequestsRepo]:
    repo = CoreRequestsRepo(db_session)
    services = CoreRequestsService(repo=repo, bot=cast(Any, bot))
    return NotificationsService(repo, None, services, cast(Any, bot)), repo


async def _user(repo: CoreRequestsRepo, **fields) -> UserSchema:
    data = {
        "username": f"n_{uuid4().hex[:10]}",
        "telegram_id": random.randint(10**9, 10**10),
        "timezone": "UTC",
        **fields,
    }
    return UserSchema.model_validate(await repo.users.create(data))


async def _deliveries(db_session: AsyncSession, user_id) -> list[NotificationDelivery]:
    result = await db_session.execute(select(NotificationDelivery).where(NotificationDelivery.user_id == user_id))
    return list(result.scalars().all())


async def test_every_attempt_is_logged_with_its_outcome_and_per_user_key(db_session: AsyncSession):
    bot = FakeBot()
    notifications, repo = _engine(db_session, bot)
    ok = await _user(repo)
    blocked = await _user(repo)
    broken = await _user(repo)
    bot.forbidden.add(blocked.telegram_id)
    bot.bad_request.add(broken.telegram_id)

    sent, eligible = await notifications.send_notification(
        KeyPerUser().initialize(notifications.services), [ok, blocked, broken], slot=NotificationSlot.EVENING
    )

    assert sent == 1
    assert len(eligible) == 3
    assert [chat_id for chat_id, _ in bot.sent] == [ok.telegram_id]
    expected = [(ok, True, None), (blocked, False, "forbidden"), (broken, False, "bad_request")]
    for user, delivered, error_code in expected:
        [row] = await _deliveries(db_session, user.id)
        assert (row.delivered, row.error_code) == (delivered, error_code)
        assert row.template == "KeyPerUser"
        assert row.message_key == f"core.test.{user.username}"
        assert row.slot == "evening"


async def test_forbidden_flags_the_user_and_recipients_skip_them(db_session: AsyncSession):
    bot = FakeBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)
    bot.forbidden.add(user.telegram_id)

    result = await notifications.services.messages.send_message(user.telegram_id, "hi")

    assert not result
    assert send_error_code(result) == SendFailure.FORBIDDEN
    flagged = await repo.users.get_user_by_id(user.id)
    await db_session.refresh(flagged)
    assert flagged.bot_blocked_at is not None
    assert user.id not in {u.id for u in await repo.users.get_notifiable_users()}


async def test_recipients_exclude_blocked_and_users_without_telegram(db_session: AsyncSession):
    _, repo = _engine(db_session, FakeBot())
    reachable = await _user(repo)
    blocked = await _user(repo, bot_blocked_at=datetime.now(UTC))
    no_telegram = await _user(repo, telegram_id=None)
    hour = int((await db_session.execute(text("SELECT extract(hour FROM now() AT TIME ZONE 'UTC')"))).scalar_one())

    at_hour = {u.id for u in await repo.users.get_users_by_local_time(hour)}

    assert reachable.id in at_hour
    assert blocked.id not in at_hour
    assert no_telegram.id not in at_hour


async def test_clear_bot_blocked_on_app_open(db_session: AsyncSession):
    notifications, repo = _engine(db_session, FakeBot())
    user = await _user(repo, bot_blocked_at=datetime.now(UTC) - timedelta(days=3))

    updated = await notifications.services.users.update_user_streak(user.id)

    assert updated is not None
    assert updated.bot_blocked_at is None
    assert user.id in {u.id for u in await repo.users.get_notifiable_users()}


async def test_clear_bot_blocked_on_start_command(db_session: AsyncSession, monkeypatch):
    notifications, repo = _engine(db_session, FakeBot())
    user = await _user(repo, bot_blocked_at=datetime.now(UTC) - timedelta(days=3))
    monkeypatch.setattr(start_handlers, "send_menu", AsyncMock())
    monkeypatch.setattr(start_handlers.posthog, "capture", lambda *args, **kwargs: None)

    await start_handlers.start_command(
        message=cast(Any, MagicMock()),
        command=CommandObject(command="start"),
        user=user,
        services=notifications.services,
    )

    assert user.id in {u.id for u in await repo.users.get_notifiable_users()}


async def test_one_message_per_user_per_slot(db_session: AsyncSession, monkeypatch):
    bot = FakeBot()
    notifications, repo = _engine(db_session, bot)
    users = [await _user(repo) for _ in range(3)]

    async def users_at_hour(hour):
        return users

    monkeypatch.setattr(notifications.services.users, "get_users_by_local_time", users_at_hour)

    results = await notifications.send_notifications_by_time(
        [LowPriorityEveryone, HighPriorityEveryone], hour=10, slot=NotificationSlot.MORNING
    )

    assert results == {"HighPriorityEveryone": 3, "LowPriorityEveryone": 0}
    assert sorted(chat_id for chat_id, _ in bot.sent) == sorted(u.telegram_id for u in users)
    for user in users:
        [row] = await _deliveries(db_session, user.id)
        assert (row.template, row.slot) == ("HighPriorityEveryone", "morning")


async def test_delivery_log_cap_helpers(db_session: AsyncSession):
    _, repo = _engine(db_session, FakeBot())
    user = await _user(repo)
    other = await _user(repo)
    log = repo.notification_deliveries
    t0 = datetime(2026, 9, 1, 19, tzinfo=UTC)
    for days, delivered in ((0, True), (5, True), (9, False)):
        await log.record(
            user_id=user.id,
            template="Invite",
            message_key="k",
            slot="evening",
            delivered=delivered,
            error_code=None if delivered else "other",
            sent_at=t0 + timedelta(days=days),
        )

    assert await log.last_sent_by_user("Invite", [user.id, other.id]) == {user.id: t0 + timedelta(days=5)}
    assert await log.last_sent_by_user("Invite", [user.id], delivered_only=False) == {user.id: t0 + timedelta(days=9)}
    times = await log.sent_times_by_user("Invite", [user.id, other.id], since=t0 + timedelta(days=1))
    assert times == {user.id: [t0 + timedelta(days=5)]}


async def test_deleting_a_user_deletes_their_log(db_session: AsyncSession):
    _, repo = _engine(db_session, FakeBot())
    user = await _user(repo)
    await repo.notification_deliveries.record(
        user_id=user.id, template="T", message_key="k", slot="other", delivered=True
    )

    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    assert await _deliveries(db_session, user.id) == []
    assert (await db_session.execute(select(User).where(User.id == user.id))).scalar_one_or_none() is None


class FlakyBot(FakeBot):
    """One chat raises a non-Telegram error; one is rate-limited on every try (RetryAfter twice)."""

    def __init__(self, crash=(), rate_limited=()):
        super().__init__()
        self.crash = set(crash)
        self.rate_limited = set(rate_limited)

    async def send_message(self, chat_id, text, **kwargs):
        if chat_id in self.crash:
            raise RuntimeError("network blew up")
        if chat_id in self.rate_limited:
            raise TelegramRetryAfter(
                method=SendMessage(chat_id=chat_id, text=text), message="Too Many Requests", retry_after=0
            )
        await super().send_message(chat_id, text, **kwargs)


async def test_a_failing_send_is_logged_and_the_slot_goes_on(db_session: AsyncSession):
    """A crash or a repeated flood limit for one user must not stop the others (or lose their log rows)."""
    bot = FlakyBot()
    notifications, repo = _engine(db_session, bot)
    crashes = await _user(repo)
    rate_limited = await _user(repo)
    fine = await _user(repo)
    bot.crash.add(crashes.telegram_id)
    bot.rate_limited.add(rate_limited.telegram_id)

    sent, _ = await notifications.send_notification(
        HighPriorityEveryone().initialize(notifications.services), [crashes, rate_limited, fine]
    )

    assert sent == 1
    assert [chat_id for chat_id, _ in bot.sent] == [fine.telegram_id]
    for user, delivered in [(crashes, False), (rate_limited, False), (fine, True)]:
        [row] = await _deliveries(db_session, user.id)
        assert row.delivered is delivered


@pytest.mark.parametrize(
    ("language_code", "tg_language_code", "expected"),
    [
        ("ru", None, "ru"),
        (None, "ru-RU", "ru"),
        (None, "en", "en"),
        (None, "uk", "en"),
        ("de", "ru", "en"),  # the explicit app language wins, and we have no German
        (None, None, "en"),
    ],
)
def test_user_language_is_always_a_locale_we_have(language_code, tg_language_code, expected):
    """An unknown locale made ``t()`` return the bare key: users on uk/es/de… got "myapp.notifications.…"."""
    user = UserSchema(id=uuid4(), language_code=language_code, tg_language_code=tg_language_code)
    assert user_language(user) == expected
    assert supported_locale(expected) == expected


@pytest.mark.parametrize(
    ("timezone", "valid"),
    [
        ("Europe/Moscow", True),
        ("UTC", True),
        ("Asia/Yekaterinburg", True),
        ("", False),
        (None, False),
        ("Mars/Olympus", False),
    ],
)
def test_only_resolvable_timezones_are_valid(timezone, valid):
    """Postgres ``timezone()`` raises on an unknown name for the whole hourly recipients query."""
    assert is_valid_timezone(timezone) is valid


class RetryThenForbiddenBot(FakeBot):
    """Flood-limited on the first try, then the user turns out to have blocked the bot."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.calls += 1
        method = SendMessage(chat_id=chat_id, text=text)
        if self.calls == 1:
            raise TelegramRetryAfter(method=method, message="Too Many Requests", retry_after=0)
        raise TelegramForbiddenError(method=method, message="Forbidden: bot was blocked by the user")


async def test_a_forbidden_on_the_flood_retry_still_flags_the_user(db_session: AsyncSession):
    """Regression (PR #131 review): the retry ran outside the error handling, so Forbidden escaped."""
    bot = RetryThenForbiddenBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)

    result = await notifications.services.messages.send_message(user.telegram_id, "hi")

    assert send_error_code(result) == SendFailure.FORBIDDEN
    assert bot.calls == 2
    flagged = await repo.users.get_user_by_id(user.id)
    await db_session.refresh(flagged)
    assert flagged.bot_blocked_at is not None


def test_send_failure_hashes_like_the_false_it_equals():
    failure = SendFailure(SendFailure.OTHER)
    assert failure == False  # noqa: E712 — the point of the test
    assert failure in {False}
    assert {False: "x"}[failure] == "x"


class BrokenKeyForOne(NotificationTemplate):
    """Picking the key raises for one user: the slot must go on for the others."""

    def __init__(self, broken_username: str):
        super().__init__()
        self._broken = broken_username

    async def get_message_key(self) -> str:
        return "core.test.ok"

    async def get_message_key_for_user(self, user: UserSchema) -> str:
        if user.username == self._broken:
            raise KeyError("no copy for this user")
        return "core.test.ok"


async def test_a_template_error_for_one_user_does_not_end_the_slot(db_session: AsyncSession):
    bot = FakeBot()
    notifications, repo = _engine(db_session, bot)
    broken = await _user(repo)
    fine = await _user(repo)

    sent, _ = await notifications.send_notification(
        BrokenKeyForOne(broken.username).initialize(notifications.services), [broken, fine]
    )

    assert sent == 1
    assert [chat_id for chat_id, _ in bot.sent] == [fine.telegram_id]
    [row] = await _deliveries(db_session, broken.id)
    assert (row.delivered, row.error_code) == (False, "other")


async def test_update_user_ignores_an_unknown_timezone(db_session: AsyncSession):
    """``PATCH /users/me`` goes through ``update_user``; a bad zone must not reach the DB."""
    notifications, repo = _engine(db_session, FakeBot())
    user = await _user(repo, timezone="Europe/Moscow")

    updated = await notifications.services.users.update_user(
        user.id, UpdateUserRequest(timezone="Mars/Olympus", is_onboarded=True)
    )

    assert updated.timezone == "Europe/Moscow"
    assert updated.is_onboarded is True


async def test_recipients_query_survives_an_unknown_stored_timezone(db_session: AsyncSession):
    """A bad zone stored before validation existed must not fail the hourly query for everyone."""
    _, repo = _engine(db_session, FakeBot())
    good = await _user(repo, timezone="UTC")
    bad = await _user(repo, timezone="Mars/Olympus")
    hour = int((await db_session.execute(text("SELECT extract(hour FROM now() AT TIME ZONE 'UTC')"))).scalar_one())

    at_hour = {u.id for u in await repo.users.get_users_by_local_time(hour)}

    assert good.id in at_hour
    assert bad.id not in at_hour


async def test_pre_send_actions_can_narrow_who_gets_the_message(db_session: AsyncSession):
    """Users pre_send_actions leaves out get no message and no delivery row; an empty list sends none."""
    bot = FakeBot()
    notifications, repo = _engine(db_session, bot)
    kept, dropped = await _user(repo), await _user(repo)

    sent, _ = await notifications.send_notification(
        SendsOnlyToSome({kept.id}).initialize(notifications.services), [kept, dropped]
    )
    assert sent == 1
    assert [chat_id for chat_id, _ in bot.sent] == [kept.telegram_id]
    assert await _deliveries(db_session, dropped.id) == []

    sent, _ = await notifications.send_notification(SendsOnlyToSome(set()).initialize(notifications.services), [kept])
    assert sent == 0
    assert len(bot.sent) == 1


class PollBot(FakeBot):
    """A FakeBot that also records polls (and refuses the forbidden chats)."""

    def __init__(self, forbidden=()):
        super().__init__(forbidden=forbidden)
        self.polls: list[dict] = []

    async def send_poll(self, chat_id, **kwargs):
        if chat_id in self.forbidden:
            raise TelegramForbiddenError(
                method=SendMessage(chat_id=chat_id, text="poll"), message="Forbidden: bot was blocked by the user"
            )
        self.polls.append({"chat_id": chat_id, **kwargs})


class SendsAPoll(NotificationTemplate):
    """Overrides ``send_to_user``: a quiz poll instead of an i18n text."""

    async def get_message_key(self) -> str:
        return "core.test.poll"

    async def send_to_user(self, messages, user, message_key, reply_markup):
        return await messages.send_poll(
            user.telegram_id, "Q?", ["A", "B"], poll_type="quiz", correct_option_id=1, explanation="Because."
        )


async def test_a_template_can_send_its_own_kind_of_message(db_session: AsyncSession):
    bot = PollBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)

    sent = await notifications._deliver(SendsAPoll().initialize(notifications.services), [user], NotificationSlot.OTHER)

    assert sent == 1
    assert bot.sent == []
    [poll] = bot.polls
    assert poll["chat_id"] == user.telegram_id
    assert (poll["question"], poll["options"], poll["type"]) == ("Q?", ["A", "B"], "quiz")
    assert poll["correct_option_ids"] == [1]
    assert poll["explanation"] == "Because."
    assert poll["question_parse_mode"] is None
    assert poll["explanation_parse_mode"] is None
    [row] = await _deliveries(db_session, user.id)
    assert (row.delivered, row.template, row.message_key, row.slot) == (True, "SendsAPoll", "core.test.poll", "other")


async def test_a_forbidden_poll_flags_the_user(db_session: AsyncSession):
    bot = PollBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)
    bot.forbidden.add(user.telegram_id)

    sent = await notifications._deliver(SendsAPoll().initialize(notifications.services), [user], NotificationSlot.OTHER)

    assert sent == 0
    [row] = await _deliveries(db_session, user.id)
    assert (row.delivered, row.error_code) == (False, "forbidden")
    flagged = await repo.users.get_user_by_id(user.id)
    await db_session.refresh(flagged)
    assert flagged.bot_blocked_at is not None


class PhotoBot(FakeBot):
    """A FakeBot that also records photos (and refuses the forbidden chats)."""

    def __init__(self, forbidden=()):
        super().__init__(forbidden=forbidden)
        self.photos: list[dict] = []

    async def send_photo(self, chat_id, **kwargs):
        if chat_id in self.forbidden:
            raise TelegramForbiddenError(
                method=SendMessage(chat_id=chat_id, text="photo"), message="Forbidden: bot was blocked by the user"
            )
        self.photos.append({"chat_id": chat_id, **kwargs})


class SendsAPhoto(NotificationTemplate):
    """Overrides ``send_to_user``: a photo rendered in memory, with a plain-text caption."""

    async def get_message_key(self) -> str:
        return "core.test.photo"

    async def send_to_user(self, messages, user, message_key, reply_markup):
        return await messages.send_photo_bytes(
            user.telegram_id, b"\xff\xd8jpeg", filename="image.jpg", caption="A <caption>"
        )


async def test_a_template_can_send_a_photo_from_bytes(db_session: AsyncSession):
    bot = PhotoBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)

    sent = await notifications._deliver(
        SendsAPhoto().initialize(notifications.services), [user], NotificationSlot.OTHER
    )

    assert sent == 1
    [photo] = bot.photos
    assert photo["chat_id"] == user.telegram_id
    assert (photo["photo"].data, photo["photo"].filename) == (b"\xff\xd8jpeg", "image.jpg")
    assert photo["caption"] == "A <caption>"
    assert photo["parse_mode"] is None  # plain text, not the bot's default HTML
    [row] = await _deliveries(db_session, user.id)
    assert (row.delivered, row.message_key) == (True, "core.test.photo")


async def test_a_forbidden_photo_flags_the_user(db_session: AsyncSession):
    bot = PhotoBot()
    notifications, repo = _engine(db_session, bot)
    user = await _user(repo)
    bot.forbidden.add(user.telegram_id)

    sent = await notifications._deliver(
        SendsAPhoto().initialize(notifications.services), [user], NotificationSlot.OTHER
    )

    assert sent == 0
    [row] = await _deliveries(db_session, user.id)
    assert (row.delivered, row.error_code) == (False, "forbidden")
    flagged = await repo.users.get_user_by_id(user.id)
    await db_session.refresh(flagged)
    assert flagged.bot_blocked_at is not None
