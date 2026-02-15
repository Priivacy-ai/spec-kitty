"""ULID generation utilities for event IDs and session IDs."""

import time
import random


def generate_event_id() -> str:
    """
    Generate a ULID-format identifier (26 characters).

    ULID format: TTTTTTTTTTRRRRRRRRRRRRRRR
    - First 10 chars: Timestamp (base32-encoded milliseconds)
    - Last 16 chars: Random component (base32-encoded)

    Returns:
        26-character ULID string
    """
    # Crockford base32 alphabet (case-insensitive, excludes I/L/O/U)
    BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    # Timestamp component (10 characters, milliseconds since epoch)
    timestamp_ms = int(time.time() * 1000)
    timestamp_part = ""
    for _ in range(10):
        timestamp_part = BASE32[timestamp_ms % 32] + timestamp_part
        timestamp_ms //= 32

    # Random component (16 characters)
    random_part = "".join(random.choices(BASE32, k=16))

    return timestamp_part + random_part
