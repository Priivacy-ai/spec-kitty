"""Regression tests for review/arbiter.py — WP05: Migrate Slice 3: Review & Tasks.

Tests verify that:
- _is_arbiter_override() uses typed Lane enum comparisons (not raw strings)
- Arbiter override detection logic is unchanged after migration
- All lane comparison scenarios work correctly with typed Lane enum
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.review.arbiter import (
    ArbiterCategory,
    ArbiterChecklist,
    _is_arbiter_override,
    create_arbiter_decision,
    parse_category_from_note,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event


pytestmark = pytest.mark.fast


def _make_event(
    feature_dir: Path,
    wp_id: str,
    from_lane: Lane,
    to_lane: Lane,
    *,
    review_ref: str | None = None,
) -> StatusEvent:
    """Helper to create and append a StatusEvent."""
    event = StatusEvent(
        event_id=f"01TEST{wp_id}{from_lane}{to_lane}".replace("_", "")[:26].upper().ljust(26, "0"),
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-04-09T12:00:00+00:00",
        actor="test-actor",
        force=True,
        execution_mode="direct_repo",
        review_ref=review_ref,
    )
    append_event(feature_dir, event)
    return event


# ---------------------------------------------------------------------------
# Tests for _is_arbiter_override() using live arbiter function
# ---------------------------------------------------------------------------


def test_is_arbiter_override_returns_false_when_not_forced(tmp_path: Path) -> None:
    """force=False → no override, regardless of lane values."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=False)

    assert result is False


def test_is_arbiter_override_returns_false_when_old_lane_not_planned(tmp_path: Path) -> None:
    """force=True but old_lane != planned → not an override."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "in_progress", "for_review", force=True)

    assert result is False


def test_is_arbiter_override_returns_false_when_target_lane_invalid(tmp_path: Path) -> None:
    """force=True, old_lane=planned, but target_lane not in forward targets → not override."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "in_progress", force=True)

    assert result is False


def test_is_arbiter_override_returns_false_when_no_events(tmp_path: Path) -> None:
    """No events for WP → cannot be a rejection override."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=True)

    assert result is False


def test_is_arbiter_override_returns_false_when_latest_event_not_rejection(tmp_path: Path) -> None:
    """Latest event is not a rejection (for_review → planned with review_ref) → not override."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    # Latest event: planned → claimed (not a rejection)
    _make_event(feature_dir, "WP01", Lane.PLANNED, Lane.CLAIMED)

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=True)

    assert result is False


def test_is_arbiter_override_returns_true_for_valid_rejection_override(tmp_path: Path) -> None:
    """Latest event is for_review→planned with review_ref (rejection) → arbiter override."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=True)

    assert result is True


def test_is_arbiter_override_valid_for_claimed_target(tmp_path: Path) -> None:
    """Arbiter can override back to 'claimed' as a forward target."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "claimed", force=True)

    assert result is True


def test_is_arbiter_override_valid_for_approved_target(tmp_path: Path) -> None:
    """Arbiter can override to 'approved' as a forward target."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "approved", force=True)

    assert result is True


def test_is_arbiter_override_requires_review_ref_in_latest_event(tmp_path: Path) -> None:
    """for_review→planned transition without review_ref is NOT a rejection."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    # for_review → planned but NO review_ref (unusual, not a rejection)
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref=None)

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=True)

    assert result is False


def test_is_arbiter_override_uses_latest_event_only(tmp_path: Path) -> None:
    """Checks only the latest event, not the entire history."""
    feature_dir = tmp_path / "kitty-specs" / "080-test"
    feature_dir.mkdir(parents=True)
    # First: for_review → planned (rejection) with review_ref
    _make_event(feature_dir, "WP01", Lane.FOR_REVIEW, Lane.PLANNED, review_ref="rev://ref/1")
    # Then: planned → claimed (not a rejection, this is the latest)
    _make_event(feature_dir, "WP01", Lane.PLANNED, Lane.CLAIMED)

    result = _is_arbiter_override(feature_dir, "WP01", "planned", "for_review", force=True)

    # Latest event is planned→claimed, not a rejection → no override
    assert result is False


# ---------------------------------------------------------------------------
# Tests for Lane enum type safety (typed comparisons)
# ---------------------------------------------------------------------------


def test_lane_enum_for_review_comparison() -> None:
    """Lane.FOR_REVIEW equals 'for_review' (StrEnum property)."""
    assert Lane.FOR_REVIEW == "for_review"
    assert Lane("for_review") == Lane.FOR_REVIEW


def test_lane_enum_planned_comparison() -> None:
    """Lane.PLANNED equals 'planned' (StrEnum property)."""
    assert Lane.PLANNED == "planned"
    assert Lane("planned") == Lane.PLANNED


def test_lane_enum_all_arbiter_forward_targets() -> None:
    """All three valid arbiter forward targets are valid Lane values."""
    forward_targets = {Lane.FOR_REVIEW, Lane.CLAIMED, Lane.APPROVED}
    assert Lane.FOR_REVIEW in forward_targets
    assert Lane.CLAIMED in forward_targets
    assert Lane.APPROVED in forward_targets
    assert Lane.PLANNED not in forward_targets
    assert Lane.IN_PROGRESS not in forward_targets


# ---------------------------------------------------------------------------
# Tests for arbiter decision functions (verify live module functions)
# ---------------------------------------------------------------------------


def test_create_arbiter_decision_returns_decision() -> None:
    """create_arbiter_decision produces a valid ArbiterDecision."""
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category=ArbiterCategory.PRE_EXISTING_FAILURE,
        explanation="Test failure was pre-existing.",
    )
    assert decision.arbiter == "operator"
    assert decision.category == ArbiterCategory.PRE_EXISTING_FAILURE
    assert decision.explanation == "Test failure was pre-existing."
    assert decision.checklist is not None
    assert decision.decided_at is not None


def test_parse_category_from_note_pre_existing() -> None:
    """parse_category_from_note parses [pre_existing_failure] prefix."""
    category, explanation = parse_category_from_note("[pre_existing_failure] Test was failing before")
    assert category == ArbiterCategory.PRE_EXISTING_FAILURE
    assert explanation == "Test was failing before"


def test_parse_category_from_note_custom_fallback() -> None:
    """parse_category_from_note falls back to CUSTOM for unrecognised prefix."""
    category, explanation = parse_category_from_note("Some freeform note without category")
    assert category == ArbiterCategory.CUSTOM
    assert explanation == "Some freeform note without category"


def test_arbiter_checklist_roundtrip() -> None:
    """ArbiterChecklist serialises and deserialises correctly."""
    checklist = ArbiterChecklist(
        is_pre_existing=True,
        is_correct_context=True,
        is_in_scope=False,
        is_environmental=False,
        should_follow_on=True,
    )
    data = checklist.to_dict()
    restored = ArbiterChecklist.from_dict(data)
    assert restored == checklist
