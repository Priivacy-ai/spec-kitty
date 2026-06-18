"""Tests for _validate_mission_slug in status/aggregate.py.

Verifies the exact exception type (InvalidMissionSlug, NOT raw ValueError) is raised for
multiple distinct malformed inputs, and that a real-format valid slug is accepted.

T009 — RED-first: these tests are written before the delegate edits so they fail
until _validate_mission_slug is wired to assert_safe_path_segment (WP02 T007).

Exception-type rule: use ``type(exc) is InvalidMissionSlug`` not isinstance — InvalidMissionSlug
subclasses ValueError, so isinstance(ValueError) would wrongly pass on a leaked raw ValueError;
the exact-type check catches that regression.
"""
from __future__ import annotations

import pytest

from specify_cli.status.aggregate import InvalidMissionSlug, MissionStatus

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


@pytest.mark.parametrize("label,bad_slug", _MALFORMED_INPUTS, ids=[t[0] for t in _MALFORMED_INPUTS])
def test_validate_mission_slug_raises_invalid_mission_slug(label: str, bad_slug: str) -> None:
    """_validate_mission_slug must raise exactly InvalidMissionSlug (not raw ValueError) for malformed input."""
    with pytest.raises(InvalidMissionSlug) as exc_info:
        MissionStatus._validate_mission_slug(bad_slug)
    # Exact-type check: must not leak a raw ValueError even if the delegate raises one.
    assert type(exc_info.value) is InvalidMissionSlug, (
        f"Expected exact type InvalidMissionSlug for slug {bad_slug!r}, "
        f"got {type(exc_info.value).__name__}"
    )


# ---------------------------------------------------------------------------
# Accept paths — real-format mission slugs
# ---------------------------------------------------------------------------

_VALID_SLUGS = [
    ("slug with hyphens", "my-mission-slug"),
    ("slug with numeric prefix", "034-feature-slug"),
    ("slug with underscores", "my_mission_slug"),
    ("short alphanumeric", "abc123"),
]


@pytest.mark.parametrize("label,good_slug", _VALID_SLUGS, ids=[t[0] for t in _VALID_SLUGS])
def test_validate_mission_slug_accepts_valid_slug(label: str, good_slug: str) -> None:
    """_validate_mission_slug must not raise for a valid ASCII identifier slug."""
    # If this raises, the delegate is over-rejecting valid inputs.
    MissionStatus._validate_mission_slug(good_slug)
