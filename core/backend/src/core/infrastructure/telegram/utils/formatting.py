"""Message formatting utilities for Telegram bot handlers."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram.types import MessageEntity


def format_message_entities(text: str, entities: list[MessageEntity] | None) -> str:
    """
    Convert Telegram message entities to HTML formatting.

    This function processes Telegram MessageEntity objects and converts them
    to HTML markup, preserving formatting like bold, italic, code blocks, links, etc.

    Args:
        text: Original message text without formatting
        entities: List of MessageEntity objects from aiogram (or None)

    Returns:
        HTML-formatted text with preserved formatting.
        Returns original text if entities is None or empty.

    Supported entity types:
        - bold: <b>text</b>
        - italic: <i>text</i>
        - code: <code>text</code>
        - pre: <pre>text</pre>
        - underline: <u>text</u>
        - strikethrough: <s>text</s>
        - text_link: <a href="url">text</a>
        - url: <a href="url">url</a>
        - mention: <a href="https://t.me/username">@username</a>
        - hashtag: <a href="https://t.me/hashtag/tag">#tag</a>
        - spoiler: <span class="tg-spoiler">text</span>

    Example:
        >>> from aiogram.types import MessageEntity
        >>> text = "Hello world"
        >>> entities = [MessageEntity(type="bold", offset=0, length=5)]
        >>> format_message_entities(text, entities)
        '<b>Hello</b> world'

    Note:
        Entities are processed in reverse order (from end to beginning)
        to preserve text offsets during replacements.
    """
    if not entities:
        return text

    # Process entities from end to beginning to preserve offsets
    formatted_text = text
    for entity in sorted(entities, key=lambda e: e.offset, reverse=True):
        text_part = text[entity.offset : entity.offset + entity.length]
        replacement = text_part  # Default: no formatting

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
        elif entity.type == "url":
            replacement = f'<a href="{text_part}">{text_part}</a>'
        elif entity.type == "mention":
            # Remove @ and create link to Telegram profile
            username = text_part[1:] if text_part.startswith("@") else text_part
            replacement = f'<a href="https://t.me/{username}">{text_part}</a>'
        elif entity.type == "hashtag":
            # Remove # and create link to Telegram hashtag search
            tag = text_part[1:] if text_part.startswith("#") else text_part
            replacement = f'<a href="https://t.me/hashtag/{tag}">{text_part}</a>'
        elif entity.type == "spoiler":
            replacement = f'<span class="tg-spoiler">{text_part}</span>'

        # Replace the text part with formatted version
        formatted_text = formatted_text[: entity.offset] + replacement + formatted_text[entity.offset + entity.length :]

    return formatted_text
