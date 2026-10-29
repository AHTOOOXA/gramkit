"""Admin notifications: Telegram-HTML formatting helpers + a sender that never drops an alert.

Every admin message is Telegram HTML (``parse_mode="HTML"``). Anything that comes from users,
products or exceptions MUST go through ``esc()`` — a stray ``<`` makes Telegram reject the
whole message.

A message may also carry a Rich Message body (Bot API 10.1 ``sendRichMessage``, "Rich HTML":
tables, ``<details>``, ``<footer>``). Delivery degrades step by step so formatting can never
cost us an alert:

    rich_html  --rejected-->  text as HTML  --rejected-->  text as plain (tags stripped)
"""

import asyncio
import html
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InputRichMessage

from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.retry import with_retries

logger = get_logger(__name__)

CURRENCY_SYMBOLS = {"RUB": "₽", "USD": "$", "EUR": "€", "XTR": "⭐"}
NBSP = " "  # narrow no-break space: thousands separator that won't wrap

# Classic messages are capped at 4096 chars; keep long user lists well under it.
MAX_LIST_LINES = 25


def esc(value: object) -> str:
    """Escape a value for Telegram HTML (text and attribute context)."""
    return html.escape(str(value), quote=True)


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", NBSP)


def fmt_money(amount: float, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    number = fmt_int(round(amount)) if float(amount).is_integer() else f"{amount:,.2f}".replace(",", NBSP)
    return f"{number}{NBSP}{symbol}"


def fmt_money_map(amounts: Mapping[str, float], empty: str = "0") -> str:
    """Per-currency amounts, largest first. Currencies are never summed together."""
    parts = [fmt_money(v, c) for c, v in sorted(amounts.items(), key=lambda kv: -kv[1]) if v]
    return " + ".join(parts) if parts else empty


def fmt_date(value: datetime) -> str:
    """'25 Sep' (or '25 Sep 2027' outside the current year)."""
    fmt = "%-d %b" if value.year == datetime.now(UTC).year else "%-d %b %Y"
    return value.strftime(fmt)


def fmt_ago(value: datetime | None) -> str:
    if value is None:
        return "?"
    seconds = (datetime.now(UTC) - value).total_seconds()
    if seconds < 3600:
        return f"{max(int(seconds // 60), 0)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def fmt_delta(current: float, previous: float) -> str:
    """'▲12%' / '▼5%' / '=' / 'new' — compact change vs the previous period."""
    if previous == 0:
        return "new" if current else "="
    change = (current - previous) / previous * 100
    if abs(change) < 0.5:
        return "="
    return f"{'▲' if change > 0 else '▼'}{abs(change):.0f}%"


def user_ref(user: object) -> str:
    """Tappable mention for a user (ORM ``User`` or ``UserSchema``), HTML-escaped.

    Falls back through tg handle → app username → name → short id, so users without a
    Telegram @username no longer render as ``@None``.
    """
    handle = getattr(user, "tg_username", None) or getattr(user, "username", None)
    if handle:
        label = f"@{handle}"
    else:
        label = (
            getattr(user, "display_name", None)
            or getattr(user, "tg_first_name", None)
            or f"user {str(getattr(user, 'id', '?'))[:8]}"
        )
    telegram_id = getattr(user, "telegram_id", None)
    if telegram_id:
        return f'<a href="tg://user?id={int(telegram_id)}">{esc(label)}</a>'
    return esc(label)


def tags(*names: str) -> str:
    """'#purchase #u_anna' — tappable in Telegram (tap = search this chat for the tag).

    Hashtags allow only letters, digits and '_', so anything else becomes '_'.
    Convention: put the tag line last; event tag first, then user tags; '#critical' on 🚨 alerts.
    """
    return " ".join("#" + re.sub(r"\W", "_", name) for name in names if name)


def user_tag(user: object) -> str:
    """'u_anna' — per-user tag name (pass to ``tags``) so one tap shows a user's whole history."""
    handle = getattr(user, "tg_username", None) or getattr(user, "username", None)
    return f"u_{handle}" if handle else f"u_{str(getattr(user, 'id', '')).replace('-', '')[:8]}"


def bullet_list(lines: Iterable[str], limit: int = MAX_LIST_LINES) -> str:
    """'• line' per item, truncated with a '…and N more' tail."""
    lines = list(lines)
    shown = [f"• {line}" for line in lines[:limit]]
    if len(lines) > limit:
        shown.append(f"<i>…and {len(lines) - limit} more</i>")
    return "\n".join(shown)


def html_to_plain(text: str) -> str:
    """Last-resort fallback: strip tags and unescape entities."""
    text = re.sub(r"<br\s*/?>", "\n", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text))


async def _deliver(bot: Bot, chat_id: int, text: str, rich_html: str | None, silent: bool) -> None:
    if rich_html:
        try:
            await bot.send_rich_message(
                chat_id=chat_id, rich_message=InputRichMessage(html=rich_html), disable_notification=silent
            )
            return
        except TelegramAPIError as e:
            logger.warning(f"Rich admin message rejected for {chat_id}, falling back to HTML: {e}")
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML", disable_notification=silent)
    except TelegramBadRequest as e:
        logger.warning(f"HTML admin message rejected for {chat_id}, falling back to plain text: {e}")
        await bot.send_message(chat_id, html_to_plain(text), parse_mode=None, disable_notification=silent)


async def send_admin_message(
    bot: Bot,
    text: str,
    *,
    rich_html: str | None = None,
    silent: bool = False,
    chat_ids: Iterable[int] | None = None,
) -> int:
    """Send an admin message to ``chat_ids`` (default: all owners). Returns delivered count.

    ``text`` is Telegram HTML and is always required — it is the fallback for ``rich_html``.
    ``silent`` delivers without a notification sound (routine / informational messages).
    """
    # Imported here (not at module level) so tests can patch core.infrastructure.config.settings.
    from core.infrastructure.config import settings

    targets = list(chat_ids) if chat_ids is not None else list(settings.rbac.owner_ids)
    sent = 0
    for chat_id in targets:
        try:
            await _deliver(bot, chat_id, text, rich_html, silent)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send admin message to {chat_id}: {e}")
        await asyncio.sleep(0.05)
    return sent


async def announce_start(service: str, version: str, bot: Bot | None = None) -> None:
    """'🚀 myapp 1.2.0 · worker started' to the owners, silently, when a process starts in prod.

    One per process (webhook / worker / bot) on each deploy: all of them showing the new version
    means the rollout finished; the same one repeating means a restart loop. Skipped in debug —
    local hot reload restarts on every save. Never raises: startup must not depend on Telegram.
    """
    from core.infrastructure.config import settings

    if settings.debug:
        return
    own_bot = bot is None
    try:
        if own_bot:
            bot = with_retries(Bot(token=settings.bot.token))
        text = (
            f"🚀 <b>{esc(getattr(settings, 'app_name', 'app'))} {esc(version)}</b> · {esc(service)} started"
            f" <i>({esc(settings.observability.logfire_environment)})</i>\n{tags('deploy')}"
        )
        await send_admin_message(bot, text, silent=True)
    except Exception as e:
        logger.error(f"Failed to announce {service} start: {e}")
    finally:
        if own_bot and bot is not None:
            await bot.session.close()


async def alert_owners(text: str) -> None:
    """Send an alert to the owners, with sound, from code that has no bot at hand (e.g. a failed
    payment webhook). Opens a short-lived bot client. Skipped in debug (local runs and tests would
    message the real owners). Never raises."""
    from core.infrastructure.config import settings

    if settings.debug:
        return
    bot = None
    try:
        bot = with_retries(Bot(token=settings.bot.token))
        await send_admin_message(bot, text)
    except Exception as e:
        logger.error(f"Failed to alert owners: {e}")
    finally:
        if bot is not None:
            await bot.session.close()
