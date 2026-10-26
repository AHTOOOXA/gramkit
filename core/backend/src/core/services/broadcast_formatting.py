"""Shared broadcast formatting helpers: entities → HTML and the broadcast keyboard registry.

Used by the admin composer (``services/broadcasts.py``), the bots' ``/broadcast`` flows and
the scheduled promo template, so every path produces IDENTICAL output:

- ``entities_to_html(text, entities)`` — converts a Telegram message's text +
  ``MessageEntity`` list (UTF-16 offsets) into the escaped HTML the send pipeline ships
  (parse_mode=HTML).
- ``build_keyboard_markup(config, locale)`` — builds a broadcast's inline keyboard from
  its stored keyboard config (``keyboard_type`` + ``keyboard_button_text``).
- ``broadcast_content(data)`` — normalizes a send-now / bot ``/broadcast`` payload into the
  content dict ``MessageService.send_content`` sends (validating it on the way).

Keyboard registry (D6 mechanism: a module dict + ``register_*``, registered explicitly at
startup): core provides ``"main"`` (a URL button that opens the app, with the custom
button text). Apps register their other keyboard types (e.g. ``"daily"``) from
``setup_infrastructure()``. Builders receive ``(button_text, locale)``; translate with
``t(key, locale)`` — ``i18n(key, locale=...)`` ignores ``locale`` whenever a
process-global translation is set (the webhook sets one per request).
"""

from __future__ import annotations

import html
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.exceptions import InvalidBroadcastException
from core.infrastructure.config import settings
from core.infrastructure.i18n import t
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


def _wrap_entity(entity_type: str, inner_html: str, raw: str, url: str | None) -> str | None:
    """Wrap one entity's (already escaped) inner HTML in the tag of its type.

    ``raw`` is the entity's plain text (for the mention / hashtag / url links). Returns
    ``None`` for unsupported entity types: the caller keeps the inner HTML without a tag.
    """
    if entity_type == "bold":
        return f"<b>{inner_html}</b>"
    if entity_type == "italic":
        return f"<i>{inner_html}</i>"
    if entity_type == "code":
        return f"<code>{inner_html}</code>"
    if entity_type == "pre":
        return f"<pre>{inner_html}</pre>"
    if entity_type == "underline":
        return f"<u>{inner_html}</u>"
    if entity_type == "strikethrough":
        return f"<s>{inner_html}</s>"
    if entity_type == "text_link" and url:
        return f'<a href="{_attr(url)}">{inner_html}</a>'
    if entity_type == "spoiler":
        return f'<span class="tg-spoiler">{inner_html}</span>'
    if entity_type == "mention":
        return f'<a href="https://t.me/{_attr(raw[1:])}">{inner_html}</a>'
    if entity_type == "hashtag":
        return f'<a href="https://t.me/hashtag/{_attr(raw[1:])}">{inner_html}</a>'
    if entity_type == "url":
        return f'<a href="{_attr(raw)}">{inner_html}</a>'
    return None


def _text(value: str) -> str:
    """Escape text for Telegram's HTML parse mode (``&``, ``<``, ``>``)."""
    return html.escape(value, quote=False)


def _attr(value: str) -> str:
    """Escape an attribute value (also the quotes)."""
    return html.escape(value, quote=True)


def _utf16_slice(data: bytes, start: int, end: int) -> str:
    """``data`` (UTF-16-LE) between two UTF-16 code-unit positions, as a str."""
    return data[start * 2 : end * 2].decode("utf-16-le", errors="replace")


def _render(data: bytes, entities: list[Any], start: int, end: int) -> str:
    """HTML of ``data[start:end]`` (code units) with ``entities`` (sorted, all starting at >= ``start``).

    An entity's nested entities are the ones that start inside it; one that runs past its
    parent's end is cut at that end (Telegram only nests, so that never happens in practice).
    """
    out: list[str] = []
    pos = start
    i = 0
    while i < len(entities):
        entity = entities[i]
        e_start = max(entity.offset, pos)
        e_end = min(entity.offset + entity.length, end)
        j = i + 1
        while j < len(entities) and entities[j].offset < e_end:
            j += 1
        if e_start >= e_end:  # empty, out of range, or inside an entity already rendered
            i += 1
            continue
        out.append(_text(_utf16_slice(data, pos, e_start)))
        inner = _render(data, entities[i + 1 : j], e_start, e_end)
        wrapped = _wrap_entity(entity.type, inner, _utf16_slice(data, e_start, e_end), getattr(entity, "url", None))
        out.append(inner if wrapped is None else wrapped)
        pos = e_end
        i = j
    out.append(_text(_utf16_slice(data, pos, end)))
    return "".join(out)


def entities_to_html(text: str | None, entities: Iterable[Any] | None) -> str:
    """Convert Telegram text + entities to the HTML used by the send pipeline (parse_mode=HTML).

    Each entity exposes ``.type``, ``.offset``, ``.length`` and (for links) ``.url``: aiogram
    ``MessageEntity`` objects or any object with those attributes. Offsets and lengths are
    UTF-16 code units, as Telegram counts them (an emoji outside the BMP is two), so the
    text is cut on its UTF-16-LE encoding. Nested entities (bold around italic) nest their
    tags. The text is HTML-escaped (``&``, ``<``, ``>``) and link targets also escape quotes,
    so a ``<`` typed in the message can't break the parse.

    Without entities the text comes back unchanged: the bots only call this for a message
    that has entities, and the web composer's ``/format`` preview sends text that is
    already HTML (tags the admin typed).
    """
    if not text:
        return text or ""
    entities = list(entities or [])
    if not entities:
        return text
    data = text.encode("utf-16-le", errors="surrogatepass")
    ordered = sorted(entities, key=lambda e: (e.offset, -e.length))  # an outer entity before the ones it holds
    return _render(data, ordered, 0, len(data) // 2)


# ── Keyboard registry ──────────────────────────────────────────────────────────

BroadcastKeyboardBuilder = Callable[[str | None, str | None], InlineKeyboardMarkup | None]
"""``(button_text, locale) -> markup``: one keyboard type of a broadcast."""


def _app_url() -> str:
    """The Mini App link the ``main`` button opens (one seam, so core-only tests needn't load app settings)."""
    return settings.web.app_url


def _open_app_keyboard(button_text: str | None, locale: str | None) -> InlineKeyboardMarkup:
    """``main``: one URL button that opens the app, labelled with the custom text (or "Open App")."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text=button_text or t("core.admin.broadcasts.open_app", locale),
        url=_app_url(),
    )
    kb.adjust(1)
    return kb.as_markup()


_KEYBOARDS: dict[str, BroadcastKeyboardBuilder] = {"main": _open_app_keyboard}


def register_broadcast_keyboard(keyboard_type: str, builder: BroadcastKeyboardBuilder) -> None:
    """Register (or replace) the builder for a broadcast ``keyboard_type``.

    Call from the app's startup (``setup_infrastructure``); registering the same type again
    replaces the builder, so a re-run of the startup code is harmless.
    """
    _KEYBOARDS[keyboard_type] = builder


def build_keyboard_markup(config: Mapping[str, Any] | None, locale: str | None = None) -> InlineKeyboardMarkup | None:
    """Build a broadcast's inline keyboard from its stored config.

    ``config`` keys:
        keyboard_type: ``"none"`` / ``None`` (no keyboard), ``"main"`` (open-app button,
            optionally with a custom button text) or any type an app registered.
        keyboard_button_text: custom button label (``main`` uses it).

    Returns ``None`` when no keyboard should be attached, including for a type nobody
    registered (logged as a warning: the message still goes out, without a button).
    """
    if not config:
        return None

    keyboard_type = config.get("keyboard_type")
    if not keyboard_type or keyboard_type == "none":
        return None

    builder = _KEYBOARDS.get(keyboard_type)
    if builder is None:
        logger.warning(f"No broadcast keyboard registered for {keyboard_type!r}; sending without a keyboard")
        return None
    return builder(config.get("keyboard_button_text"), locale)


# ── Send-now / bot payload → content ───────────────────────────────────────────

_MEDIA_TYPES = frozenset({"photo", "video", "animation", "document"})


def broadcast_content(data: Mapping[str, Any]) -> dict:
    """Normalize a ``user_broadcast_job`` payload into the content dict ``send_content`` sends.

    Canonical keys (the ``BroadcastSendNowRequest`` content fields): ``message_type``
    (default ``"text"``), ``message_text``, ``message_html``, ``has_text_formatting``,
    ``media_file_id``, ``caption``, ``caption_html``, ``has_caption_formatting``, plus
    ``media_metadata``. Legacy keys of the bots' ``/broadcast`` flow and of jobs queued
    before: ``has_formatting`` (= ``has_text_formatting``) and ``photo_file_id``
    (= ``media_file_id``, for any media type). The bot omits ``message_html`` /
    ``caption_html`` when there's no formatting.

    Returns ``{"type": "text", "text", "parse_mode"}`` or ``{"type": <media>, "media_file_id",
    "caption", "parse_mode", "metadata"}`` (the ``get_content_for_sending()`` shape). Raises
    ``InvalidBroadcastException`` when there's nothing to send.
    """
    message_type = data.get("message_type") or "text"

    if message_type == "text":
        formatted = bool(data.get("has_text_formatting") or data.get("has_formatting"))
        text = (data.get("message_html") or data.get("message_text")) if formatted else data.get("message_text")
        if not text:
            raise InvalidBroadcastException("Text send-now requires message_text")
        return {"type": "text", "text": text, "parse_mode": "HTML" if formatted else None}

    if message_type not in _MEDIA_TYPES:
        raise InvalidBroadcastException(f"Unsupported message type: {message_type}")
    file_id = data.get("media_file_id") or data.get("photo_file_id")
    if not file_id:
        raise InvalidBroadcastException("Media send-now requires media_file_id")
    formatted = bool(data.get("has_caption_formatting"))
    caption = (data.get("caption_html") or data.get("caption")) if formatted else data.get("caption")
    return {
        "type": message_type,
        "media_file_id": file_id,
        "caption": caption or None,
        "parse_mode": "HTML" if formatted else None,
        "metadata": data.get("media_metadata") or {},
    }
