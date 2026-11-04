from aiogram import Bot
from fastapi import Request


async def get_bot(request: Request) -> Bot | None:
    """The worker's Bot, created once in create_api's lifespan (core.infrastructure.fastapi.clients).

    Never build a Bot per request: Bot() loads the CA bundle into a new SSL context every time. None when
    BOT__TOKEN is empty, or under an ASGI test client (no lifespan; tests override this dependency).
    """
    return getattr(request.app.state, "bot", None)
