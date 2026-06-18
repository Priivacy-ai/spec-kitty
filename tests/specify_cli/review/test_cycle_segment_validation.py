"""Tests for _validate_segment in review/cycle.py.

Verifies the exact exception type (ReviewCycleError, NOT raw ValueError) is raised for
multiple distinct malformed inputs, and that a real-format valid value is accepted.

T009 — RED-first: these tests are written before the delegate edits so they fail
until _validate_segment is wired to assert_safe_path_segment (WP02 T008).

Exception-type rule: use ``type(exc) is ReviewCycleError`` not isinstance — ReviewCycleError
subclasses ValueError, so isinstance(ValueError) would wrongly pass on a leaked raw ValueError;
the exact-type check catches that regression.
"""
from __future__ import annotations

import pytest

from specify_cli.review.cycle import ReviewCycleError, _validate_segment

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
def test_validate_segment_raises_review_cycle_error(label: str, bad_value: str) -> None:
    """_validate_segment must raise exactly ReviewCycleError (not raw ValueError) for malformed input."""
    with pytest.raises(ReviewCycleError) as exc_info:
        _validate_segment("test_field", bad_value)
    # Exact-type check: must not leak a raw ValueError even if the delegate raises one.
    assert type(exc_info.value) is ReviewCycleError, (
        f"Expected exact type ReviewCycleError for input {bad_value!r}, "
        f"got {type(exc_info.value).__name__}"
    )


# ---------------------------------------------------------------------------
# Accept paths — real-format valid segment values
# ---------------------------------------------------------------------------

_VALID_INPUTS = [
    ("mission slug with hyphens", "my-mission-slug"),
    ("WP slug", "WP01"),
    ("slug with numeric prefix", "034-feature-slug"),
    ("review cycle filename", "review-cycle-1"),
    ("alphanumeric", "abc123"),
]


@pytest.mark.parametrize("label,good_value", _VALID_INPUTS, ids=[t[0] for t in _VALID_INPUTS])
def test_validate_segment_accepts_valid_value(label: str, good_value: str) -> None:
    """_validate_segment must return the value unchanged for a valid path segment."""
    result = _validate_segment("test_field", good_value)
    assert result == good_value
