"""Authentication fixtures for testing Telegram Mini App auth."""

import hashlib
import hmac
import json
from urllib.parse import urlencode


def generate_telegram_init_data(
    user_id: int,
    username: str,
    first_name: str = "Test",
    last_name: str | None = None,
    language_code: str = "en",
    is_premium: bool = False,
    auth_date: int = 1640000000,
    bot_token: str = "test_token",
) -> str:
    """
    Generate valid Telegram Mini App init_data for testing.

    This creates properly signed init_data that will pass
    TelegramAuthenticator.verify_token() validation.

    Args:
        user_id: Telegram user ID (use random.randint for parallel safety)
        username: Telegram username (use uuid for uniqueness)
        first_name: User's first name
        last_name: User's last name (optional)
        language_code: User's language code
        is_premium: Whether user has Telegram Premium
        auth_date: Unix timestamp (fixed is fine for tests)
        bot_token: Bot token (must match config.tgbot_config.token)

    Returns:
        URL-encoded init_data string for initData header

    Example:
        >>> init_data = generate_telegram_init_data(123456, "test_user")
        >>> client.headers["initData"] = init_data
    """
    # Build user data matching Telegram's WebAppUser structure
    user_data = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "language_code": language_code,
        "is_premium": is_premium,
    }

    if last_name:
        user_data["last_name"] = last_name

    # Build data_check_string (alphabetically sorted, newline-separated)
    # This MUST match Telegram's algorithm exactly
    data_check_string_parts = [
        f"auth_date={auth_date}",
        f"user={json.dumps(user_data, separators=(',', ':'))}",
    ]
    data_check_string = "\n".join(sorted(data_check_string_parts))

    # Generate HMAC hash using same algorithm as Telegram
    # Step 1: Create secret key from bot token
    secret_key = hmac.digest(b"WebAppData", bot_token.encode(), hashlib.sha256)

    # Step 2: Generate hash of data_check_string
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Build final init_data with hash
    # IMPORTANT: Must use same JSON formatting as in data_check_string
    init_data_parts = {
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(auth_date),
        "hash": hash_value,
    }

    return urlencode(init_data_parts)
