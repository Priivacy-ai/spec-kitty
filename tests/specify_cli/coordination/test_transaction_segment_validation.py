"""Tests for _validate_safe_segment in coordination/transaction.py.

Verifies the exact exception type (BookkeepingError, NOT ValueError) is raised for
multiple distinct malformed inputs, and that a real-format valid value is accepted.

T009 — RED-first: these tests are written before the delegate edits so they fail
until _validate_safe_segment is wired to assert_safe_path_segment (WP02 T006).

Exception-type rule: use ``type(exc) is BookkeepingError`` not isinstance — BookkeepingError
does NOT subclass ValueError, but correctness requires we verify the exact domain type
rather than relying on structural typing.
"""
from __future__ import annotations

import pytest

from specify_cli.coordination.transaction import BookkeepingError, _validate_safe_segment

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Reject paths — each exercises a distinct rejection branch
# ---------------------------------------------------------------------------

_MALFORMED_INPUTS = [
    ("dot-dot segment", ".."),
    ("slash in value", "a/b"),
    ("backslash in value", "a\\b"),
    ("non-ASCII character", "café"),
    ("empty string", ""),
]


@pytest.mark.parametrize("label,bad_value", _MALFORMED_INPUTS, ids=[t[0] for t in _MALFORMED_INPUTS])
def test_validate_safe_segment_raises_bookkeeping_error(label: str, bad_value: str) -> None:
    """_validate_safe_segment must raise exactly BookkeepingError (not raw ValueError) for malformed input."""
    with pytest.raises(BookkeepingError) as exc_info:
        _validate_safe_segment("test_field", bad_value)
    # Exact-type check: must not leak a raw ValueError even if the delegate raises one.
    assert type(exc_info.value) is BookkeepingError, (
        f"Expected exact type BookkeepingError for input {bad_value!r}, "
        f"got {type(exc_info.value).__name__}"
    )


# ---------------------------------------------------------------------------
# Accept paths — real-format ULID, mid8, and slug values
# ---------------------------------------------------------------------------

_VALID_INPUTS = [
    ("26-char ULID", "01KVBBT6XYZABCDEFG0123456789"),
    ("8-char mid8", "01KVBBT6"),
    ("mission slug with hyphens", "my-mission-slug"),
    ("slug with numeric prefix", "034-feature-slug"),
    ("slug with underscores", "my_mission_slug"),
]


@pytest.mark.parametrize("label,good_value", _VALID_INPUTS, ids=[t[0] for t in _VALID_INPUTS])
def test_validate_safe_segment_accepts_valid_value(label: str, good_value: str) -> None:
    """_validate_safe_segment must return the value unchanged for a valid path segment."""
    result = _validate_safe_segment("test_field", good_value)
    assert result == good_value
