"""Infrastructure utilities."""


def normalize_email(email: str) -> str:
    """
    Normalize email for consistent storage and lookup.

    - Strips whitespace
    - Converts to lowercase

    Args:
        email: Email address to normalize

    Returns:
        Normalized email address
    """
    return email.strip().lower()
