"""Utility functions for generating group invite codes."""

import secrets
import string


def generate_invite_code(length: int = 8) -> str:
    """
    Generate a random invite code using uppercase letters and digits.

    Args:
        length: Length of the invite code (default: 8)

    Returns:
        Random invite code string

    Example:
        >>> code = generate_invite_code()
        >>> len(code)
        8
        >>> code = generate_invite_code(12)
        >>> len(code)
        12
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
