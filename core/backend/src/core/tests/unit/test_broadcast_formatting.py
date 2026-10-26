"""Broadcast formatting helpers: entities → HTML parity and the keyboard registry.

``entities_to_html`` was extracted from the bot's inline ``/broadcast`` + ``/promo``
entity-to-HTML loop. The parity test re-implements the bot's PREVIOUS logic and asserts
byte-for-byte equality on the plain-ASCII cases it handled right; the old loop cut the
str by UTF-16 offsets, didn't escape and broke nested entities, which the tests after it
cover.

Pure unit tests — no DB, no app.
"""

from dataclasses import dataclass

import pytest
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.exceptions import InvalidBroadcastException
from core.infrastructure.i18n import t
from core.services import broadcast_formatting
from core.services.broadcast_formatting import (
    broadcast_content,
    build_keyboard_markup,
    entities_to_html,
    register_broadcast_keyboard,
)

APP_URL = "https://t.me/test_bot/app"


@pytest.fixture(autouse=True)
def app_url(monkeypatch):
    """The ``main`` button's link without loading app settings (core-only CI has no ``app``)."""
    monkeypatch.setattr(broadcast_formatting, "_app_url", lambda: APP_URL)


@dataclass
class _Entity:
    """Minimal stand-in for aiogram's MessageEntity (type/offset/length/url)."""

    type: str
    offset: int
    length: int
    url: str | None = None


def _legacy_entities_to_html(text: str, entities: list[_Entity]) -> str:
    """The bot's ORIGINAL inline implementation (copied before extraction)."""
    message_html = text
    for entity in sorted(entities, key=lambda e: e.offset, reverse=True):
        text_part = text[entity.offset : entity.offset + entity.length]
        if entity.type == "bold":
            replacement = f"<b>{text_part}</b>"
        elif entity.type == "italic":
            replacement = f"<i>{text_part}</i>"
        elif entity.type == "code":
            replacement = f"<code>{text_part}</code>"
        elif entity.type == "pre":
            replacement = f"<pre>{text_part}</pre>"
        elif entity.type == "underline":
            replacement = f"<u>{text_part}</u>"
        elif entity.type == "strikethrough":
            replacement = f"<s>{text_part}</s>"
        elif entity.type == "text_link" and entity.url:
            replacement = f'<a href="{entity.url}">{text_part}</a>'
        elif entity.type == "spoiler":
            replacement = f'<span class="tg-spoiler">{text_part}</span>'
        elif entity.type == "mention":
            replacement = f'<a href="https://t.me/{text_part[1:]}">{text_part}</a>'
        elif entity.type == "hashtag":
            replacement = f'<a href="https://t.me/hashtag/{text_part[1:]}">{text_part}</a>'
        elif entity.type == "url":
            replacement = f'<a href="{text_part}">{text_part}</a>'
        else:
            continue
        message_html = message_html[: entity.offset] + replacement + message_html[entity.offset + entity.length :]
    return message_html


@pytest.mark.business_logic
class TestEntitiesToHtmlParity:
    @pytest.mark.parametrize(
        "text,entities",
        [
            ("bold here", [_Entity("bold", 0, 4)]),
            ("italic word", [_Entity("italic", 0, 6)]),
            ("a code b", [_Entity("code", 2, 4)]),
            ("strike me", [_Entity("strikethrough", 0, 6)]),
            ("under here", [_Entity("underline", 0, 5)]),
            ("click link", [_Entity("text_link", 6, 4, url="https://x.io")]),
            ("@username here", [_Entity("mention", 0, 9)]),
            ("tag #news now", [_Entity("hashtag", 4, 5)]),
            ("visit https://t.me x", [_Entity("url", 6, 12)]),
            ("spoil this", [_Entity("spoiler", 0, 5)]),
            # Multiple, overlapping offsets (reverse processing must keep them stable).
            ("bold and italic", [_Entity("bold", 0, 4), _Entity("italic", 9, 6)]),
            # Unsupported entity type is skipped (no change).
            ("mystery type", [_Entity("custom_emoji", 0, 7)]),
        ],
    )
    def test_matches_legacy_output(self, text: str, entities: list[_Entity]):
        assert entities_to_html(text, entities) == _legacy_entities_to_html(text, entities)

    def test_empty_text(self):
        assert entities_to_html("", None) == ""

    def test_none_entities_passthrough(self):
        assert entities_to_html("plain text", None) == "plain text"

    def test_known_bold_output(self):
        assert entities_to_html("hi there", [_Entity("bold", 0, 2)]) == "<b>hi</b> there"


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


@pytest.mark.business_logic
class TestEntitiesToHtmlUtf16:
    """Telegram offsets/lengths are UTF-16 code units: an astral emoji counts twice."""

    def test_astral_emoji_before_the_entity(self):
        text = "🔥🔥 Sale today"
        offset = _utf16_len("🔥🔥 ")
        assert entities_to_html(text, [_Entity("bold", offset, 4)]) == "🔥🔥 <b>Sale</b> today"

    def test_astral_emoji_inside_the_entity(self):
        text = "Go 🎉 now!"
        assert entities_to_html(text, [_Entity("italic", 3, _utf16_len("🎉 now"))]) == "Go <i>🎉 now</i>!"

    def test_cyrillic(self):
        text = "Привет, мир"
        assert entities_to_html(text, [_Entity("bold", 8, 3)]) == "Привет, <b>мир</b>"

    def test_text_link_after_an_emoji(self):
        text = "🔥 Скидка дня"
        entity = _Entity("text_link", _utf16_len("🔥 "), len("Скидка"), url="https://x.io/a")
        assert entities_to_html(text, [entity]) == '🔥 <a href="https://x.io/a">Скидка</a> дня'

    def test_nested_bold_and_italic(self):
        text = "bold and italic"
        entities = [_Entity("italic", 5, 3), _Entity("bold", 0, 15)]
        assert entities_to_html(text, entities) == "<b>bold <i>and</i> italic</b>"

    def test_same_start_nests_the_longer_outside(self):
        text = "🌙 moon light"
        whole = _utf16_len(text)
        entities = [_Entity("italic", 0, _utf16_len("🌙 moon")), _Entity("bold", 0, whole)]
        assert entities_to_html(text, entities) == "<b><i>🌙 moon</i> light</b>"

    def test_unsupported_entity_keeps_the_nested_ones(self):
        text = "⭐ star"
        entities = [_Entity("custom_emoji", 0, 1), _Entity("bold", 0, _utf16_len(text))]
        assert entities_to_html(text, entities) == "<b>⭐ star</b>"


@pytest.mark.business_logic
class TestEntitiesToHtmlEscaping:
    """The output goes out with parse_mode=HTML: text and link targets must be escaped."""

    def test_text_around_and_inside_entities_is_escaped(self):
        text = "a < b & c > d"
        assert entities_to_html(text, [_Entity("bold", 4, 5)]) == "a &lt; <b>b &amp; c</b> &gt; d"

    def test_text_link_url_is_attribute_escaped(self):
        url = 'https://x.io/?a=1&b="2"<'
        html = entities_to_html("click", [_Entity("text_link", 0, 5, url=url)])
        assert html == '<a href="https://x.io/?a=1&amp;b=&quot;2&quot;&lt;">click</a>'

    def test_url_entity_is_escaped_in_href_and_text(self):
        text = "see https://x.io/?a=1&b=2"
        html = entities_to_html(text, [_Entity("url", 4, len(text) - 4)])
        assert html == 'see <a href="https://x.io/?a=1&amp;b=2">https://x.io/?a=1&amp;b=2</a>'

    def test_without_entities_text_is_returned_as_is(self):
        """The web composer's preview sends HTML the admin typed, with no entities."""
        assert entities_to_html("<b>typed</b> & sent", None) == "<b>typed</b> & sent"


def _only_button(markup: InlineKeyboardMarkup | None):
    assert markup is not None
    [[button]] = markup.inline_keyboard
    return button


@pytest.fixture
def registry(monkeypatch):
    """An isolated copy of the keyboard registry (core's ``main`` only)."""
    keyboards = dict(broadcast_formatting._KEYBOARDS)
    keyboards.pop("daily", None)  # an app may have registered it in this process
    monkeypatch.setattr(broadcast_formatting, "_KEYBOARDS", keyboards)
    return keyboards


@pytest.mark.business_logic
class TestKeyboardRegistry:
    @pytest.mark.parametrize("config", [None, {}, {"keyboard_type": None}, {"keyboard_type": "none"}])
    def test_no_keyboard(self, registry, config):
        assert build_keyboard_markup(config, "en") is None

    def test_main_uses_the_custom_text_and_opens_the_app(self, registry):
        button = _only_button(build_keyboard_markup({"keyboard_type": "main", "keyboard_button_text": "Go!"}, "en"))
        assert button.text == "Go!"
        assert button.url == APP_URL

    @pytest.mark.parametrize("locale", ["en", "ru", None])
    def test_main_without_text_has_a_localized_fallback_label(self, registry, locale):
        button = _only_button(build_keyboard_markup({"keyboard_type": "main"}, locale))
        assert button.text == t("core.admin.broadcasts.open_app", locale)
        assert button.url == APP_URL

    def test_fallback_label_is_translated(self):
        assert t("core.admin.broadcasts.open_app", "en") == "Open App"
        assert t("core.admin.broadcasts.open_app", "ru") != "Open App"

    def test_unregistered_type_sends_no_keyboard(self, registry):
        assert build_keyboard_markup({"keyboard_type": "daily"}, "en") is None

    def test_registered_builder_gets_text_and_locale(self, registry):
        calls = []

        def builder(button_text, locale):
            calls.append((button_text, locale))
            kb = InlineKeyboardBuilder()
            kb.button(text=f"daily-{locale}", url="https://example.com/daily")
            return kb.as_markup()

        register_broadcast_keyboard("daily", builder)

        button = _only_button(build_keyboard_markup({"keyboard_type": "daily", "keyboard_button_text": "x"}, "ru"))

        assert calls == [("x", "ru")]
        assert button.text == "daily-ru"

    def test_registering_again_replaces_the_builder(self, registry):
        register_broadcast_keyboard("daily", lambda _text, _locale: None)
        register_broadcast_keyboard("daily", lambda _text, _locale: InlineKeyboardMarkup(inline_keyboard=[]))
        assert build_keyboard_markup({"keyboard_type": "daily"}, "en") == InlineKeyboardMarkup(inline_keyboard=[])


@pytest.mark.business_logic
class TestBroadcastContent:
    def test_plain_text(self):
        assert broadcast_content({"message_type": "text", "message_text": "hi"}) == {
            "type": "text",
            "text": "hi",
            "parse_mode": None,
        }

    def test_formatted_text_uses_the_html(self):
        content = broadcast_content(
            {"message_type": "text", "message_text": "hi", "message_html": "<b>hi</b>", "has_text_formatting": True}
        )
        assert content == {"type": "text", "text": "<b>hi</b>", "parse_mode": "HTML"}

    def test_legacy_bot_text_with_only_html(self):
        """The bot's /broadcast payload: ``has_formatting`` and the HTML, no plain-text requirement."""
        content = broadcast_content({"message_type": "text", "message_html": "<b>Bold</b>", "has_formatting": True})
        assert content == {"type": "text", "text": "<b>Bold</b>", "parse_mode": "HTML"}

    def test_message_type_defaults_to_text(self):
        assert broadcast_content({"message_text": "x"})["type"] == "text"

    @pytest.mark.parametrize("media_type", ["photo", "video", "animation", "document"])
    def test_every_media_type(self, media_type):
        content = broadcast_content(
            {"message_type": media_type, "media_file_id": "f1", "caption": "c", "media_metadata": {"w": 1}}
        )
        assert content == {
            "type": media_type,
            "media_file_id": "f1",
            "caption": "c",
            "parse_mode": None,
            "metadata": {"w": 1},
        }

    def test_legacy_photo_file_id_and_formatted_caption(self):
        content = broadcast_content(
            {
                "message_type": "photo",
                "photo_file_id": "AgAC",
                "caption": "c",
                "caption_html": "<i>c</i>",
                "has_caption_formatting": True,
            }
        )
        assert (content["media_file_id"], content["caption"], content["parse_mode"]) == ("AgAC", "<i>c</i>", "HTML")

    @pytest.mark.parametrize(
        "data,message",
        [
            ({"message_type": "text"}, "Text send-now requires message_text"),
            ({"message_type": "text", "message_html": "<b>x</b>"}, "Text send-now requires message_text"),
            ({"message_type": "video", "caption": "c"}, "Media send-now requires media_file_id"),
            ({"message_type": "sticker", "media_file_id": "x"}, "Unsupported message type: sticker"),
        ],
    )
    def test_invalid_payloads_raise(self, data, message):
        with pytest.raises(InvalidBroadcastException, match=message):
            broadcast_content(data)
