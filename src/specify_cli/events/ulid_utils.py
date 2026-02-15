"""ULID generation utilities for event IDs."""

from ulid import ULID


def generate_event_id() -> str:
    """
    Generate ULID for event_id.

    ULIDs are 26-character strings that are:
    - Lexicographically sortable by creation time
    - Globally unique (128-bit entropy)
    - URL-safe (Base32 encoding)

    Returns:
        26-character ULID string
    """
    return str(ULID())


def validate_ulid_format(ulid_str: str) -> bool:
    """
    Validate ULID format (26 chars, alphanumeric).

    Args:
        ulid_str: String to validate

    Returns:
        True if valid ULID format, False otherwise
    """
    if len(ulid_str) != 26:
        return False

    # ULID uses Crockford Base32 (0-9, A-Z excluding I, L, O, U)
    valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return all(c in valid_chars for c in ulid_str.upper())
