"""Tests for the arbiter checklist and rationale model.

Covers all 14 required test cases for T035.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.review.arbiter import (
    ArbiterCategory,
    ArbiterChecklist,
    ArbiterDecision,
    _derive_category,
    _is_arbiter_override,
    create_arbiter_decision,
    parse_category_from_note,
    persist_arbiter_decision,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    wp_id: str = "WP01",
    from_lane: Lane,
    to_lane: Lane,
    review_ref: str | None = None,
    force: bool = False,
    mission_slug: str = "066-test",
) -> StatusEvent:
    return StatusEvent(
        event_id="01TESTARBITER000000000000",
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-04-06T12:00:00+00:00",
        actor="test",
        force=force,
        execution_mode="worktree",
        review_ref=review_ref,
    )


def _write_event(feature_dir: Path, event: StatusEvent) -> None:
    append_event(feature_dir, event)


def _make_checklist(
    *,
    is_pre_existing: bool = False,
    is_correct_context: bool = True,
    is_in_scope: bool = True,
    is_environmental: bool = False,
    should_follow_on: bool = False,
) -> ArbiterChecklist:
    return ArbiterChecklist(
        is_pre_existing=is_pre_existing,
        is_correct_context=is_correct_context,
        is_in_scope=is_in_scope,
        is_environmental=is_environmental,
        should_follow_on=should_follow_on,
    )


# ---------------------------------------------------------------------------
# T1: ArbiterCategory enum values
# ---------------------------------------------------------------------------


def test_arbiter_category_enum_values() -> None:
    """All 5 categories have correct string values."""
    assert ArbiterCategory.PRE_EXISTING_FAILURE == "pre_existing_failure"
    assert ArbiterCategory.WRONG_CONTEXT == "wrong_context"
    assert ArbiterCategory.CROSS_SCOPE == "cross_scope"
    assert ArbiterCategory.INFRA_ENVIRONMENTAL == "infra_environmental"
    assert ArbiterCategory.CUSTOM == "custom"


# ---------------------------------------------------------------------------
# T2: ArbiterChecklist round-trip
# ---------------------------------------------------------------------------


def test_checklist_to_dict_round_trip() -> None:
    """Create, to_dict, from_dict, compare."""
    original = _make_checklist(is_pre_existing=True, should_follow_on=True)
    d = original.to_dict()
    restored = ArbiterChecklist.from_dict(d)
    assert restored == original
    assert d["is_pre_existing"] is True
    assert d["should_follow_on"] is True


# ---------------------------------------------------------------------------
# T3: ArbiterDecision round-trip
# ---------------------------------------------------------------------------


def test_decision_to_dict_round_trip() -> None:
    """Full decision round-trip via to_dict / from_dict."""
    checklist = _make_checklist(is_pre_existing=True)
    decision = ArbiterDecision(
        arbiter="robert",
        category=ArbiterCategory.PRE_EXISTING_FAILURE,
        explanation="Test was already failing since commit abc123",
        checklist=checklist,
        decided_at="2026-04-06T14:00:00+00:00",
    )
    d = decision.to_dict()
    restored = ArbiterDecision.from_dict(d)
    assert restored == decision
    assert d["category"] == "pre_existing_failure"
    assert d["arbiter"] == "robert"


# ---------------------------------------------------------------------------
# T4-T8: Category derivation
# ---------------------------------------------------------------------------


def test_derive_category_pre_existing() -> None:
    """is_pre_existing=True → PRE_EXISTING_FAILURE."""
    cl = _make_checklist(is_pre_existing=True)
    assert _derive_category(cl) == ArbiterCategory.PRE_EXISTING_FAILURE


def test_derive_category_wrong_context() -> None:
    """is_correct_context=False → WRONG_CONTEXT."""
    cl = _make_checklist(is_correct_context=False)
    assert _derive_category(cl) == ArbiterCategory.WRONG_CONTEXT


def test_derive_category_cross_scope() -> None:
    """is_in_scope=False → CROSS_SCOPE."""
    cl = _make_checklist(is_in_scope=False)
    assert _derive_category(cl) == ArbiterCategory.CROSS_SCOPE


def test_derive_category_environmental() -> None:
    """is_environmental=True → INFRA_ENVIRONMENTAL."""
    cl = _make_checklist(is_environmental=True)
    assert _derive_category(cl) == ArbiterCategory.INFRA_ENVIRONMENTAL


def test_derive_category_custom() -> None:
    """All normal answers fall through to CUSTOM."""
    cl = _make_checklist()  # all defaults: no flags set
    assert _derive_category(cl) == ArbiterCategory.CUSTOM


# ---------------------------------------------------------------------------
# T9-T11: Override detection
# ---------------------------------------------------------------------------


def test_is_arbiter_override_after_rejection(tmp_path: Path) -> None:
    """Rejection event + forward force → True."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)

    # Simulate: WP01 claimed -> for_review -> planned (rejection with review_ref)
    _write_event(
        feature_dir,
        _make_event(from_lane=Lane.CLAIMED, to_lane=Lane.FOR_REVIEW),
    )
    _write_event(
        feature_dir,
        _make_event(
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.PLANNED,
            review_ref="feedback://066-test/WP01/20260406T120000Z-abc123.md",
        ),
    )

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="planned",
        target_lane="for_review",
        force=True,
    )
    assert result is True


def test_is_arbiter_override_normal_claim(tmp_path: Path) -> None:
    """No rejection event in history + force → False (normal claim, not override)."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)

    # Only a planned -> claimed event, no rejection
    _write_event(
        feature_dir,
        _make_event(from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED),
    )

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="planned",
        target_lane="for_review",
        force=True,
    )
    assert result is False


def test_is_arbiter_override_no_force(tmp_path: Path) -> None:
    """Rejection event present but force=False → False (not an override)."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)

    _write_event(
        feature_dir,
        _make_event(
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.PLANNED,
            review_ref="feedback://066-test/WP01/20260406T120000Z-abc123.md",
        ),
    )

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="planned",
        target_lane="for_review",
        force=False,  # no force!
    )
    assert result is False


# ---------------------------------------------------------------------------
# T12: Persist decision in artifact
# ---------------------------------------------------------------------------


def test_persist_decision_in_artifact(tmp_path: Path) -> None:
    """Decision appears in artifact frontmatter when review-cycle file exists."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    wp_subdir = feature_dir / "tasks" / "WP01"
    wp_subdir.mkdir(parents=True)

    # Create a review-cycle artifact
    artifact = wp_subdir / "review-cycle-001.md"
    artifact.write_text(
        "---\nreview_ref: review-cycle://066-test/WP01/001\n---\n\n# Review\n\nSome feedback.\n",
        encoding="utf-8",
    )

    checklist = _make_checklist(is_pre_existing=True)
    decision = ArbiterDecision(
        arbiter="robert",
        category=ArbiterCategory.PRE_EXISTING_FAILURE,
        explanation="Test was pre-existing",
        checklist=checklist,
        decided_at="2026-04-06T14:00:00+00:00",
    )

    result_path = persist_arbiter_decision(
        feature_dir=feature_dir,
        wp_id="WP01",
        review_ref="review-cycle://066-test/WP01/001",
        decision=decision,
    )

    assert result_path == artifact
    content = artifact.read_text(encoding="utf-8")
    assert "arbiter_override" in content
    assert "pre_existing_failure" in content
    assert "Test was pre-existing" in content


# ---------------------------------------------------------------------------
# T13: Standalone fallback when no artifact
# ---------------------------------------------------------------------------


def test_persist_decision_standalone_fallback(tmp_path: Path) -> None:
    """No artifact → standalone JSON created."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    # Do NOT create any review-cycle artifact

    checklist = _make_checklist(is_environmental=True)
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category=ArbiterCategory.INFRA_ENVIRONMENTAL,
        explanation="CI server was down",
        checklist=checklist,
    )

    result_path = persist_arbiter_decision(
        feature_dir=feature_dir,
        wp_id="WP01",
        review_ref=None,
        decision=decision,
    )

    assert result_path.name == "arbiter-override-1.json"
    assert result_path.parent.name == "WP01"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["category"] == "infra_environmental"
    assert data["explanation"] == "CI server was down"


# ---------------------------------------------------------------------------
# T14: parse_category_from_note
# ---------------------------------------------------------------------------


def test_parse_category_from_note() -> None:
    """``"[pre_existing_failure] explanation"`` parsed correctly."""
    cat, expl = parse_category_from_note("[pre_existing_failure] Test was already failing")
    assert cat == ArbiterCategory.PRE_EXISTING_FAILURE
    assert expl == "Test was already failing"


def test_parse_category_from_note_wrong_context() -> None:
    """``"[wrong_context]"`` parsed correctly."""
    cat, expl = parse_category_from_note("[wrong_context] Reviewer confused WP06 with WP07")
    assert cat == ArbiterCategory.WRONG_CONTEXT
    assert "confused" in expl


def test_parse_category_from_note_freeform() -> None:
    """Freeform note without bracket → CUSTOM category."""
    cat, expl = parse_category_from_note("No bracket here at all")
    assert cat == ArbiterCategory.CUSTOM
    assert expl == "No bracket here at all"


def test_parse_category_from_note_none() -> None:
    """None note → CUSTOM with generic explanation."""
    cat, expl = parse_category_from_note(None)
    assert cat == ArbiterCategory.CUSTOM
    assert expl  # must be non-empty


def test_parse_category_from_note_unknown_bracket() -> None:
    """Unknown category in brackets → CUSTOM, full note as explanation."""
    cat, expl = parse_category_from_note("[unknown_category] some explanation")
    assert cat == ArbiterCategory.CUSTOM


# ---------------------------------------------------------------------------
# Additional: create_arbiter_decision non-interactive factory
# ---------------------------------------------------------------------------


def test_create_arbiter_decision_string_category() -> None:
    """String category is coerced to ArbiterCategory."""
    decision = create_arbiter_decision(
        arbiter_name="claude",
        category="cross_scope",
        explanation="Finding is outside WP scope",
    )
    assert decision.category == ArbiterCategory.CROSS_SCOPE
    assert decision.arbiter == "claude"
    assert decision.checklist is not None
    # Synthetic checklist should be consistent with CROSS_SCOPE
    assert decision.checklist.is_in_scope is False


def test_create_arbiter_decision_invalid_category_falls_back() -> None:
    """Invalid category string falls back to CUSTOM."""
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category="totally_invalid",
        explanation="Some explanation",
    )
    assert decision.category == ArbiterCategory.CUSTOM


def test_create_arbiter_decision_empty_explanation_uses_default() -> None:
    """Empty explanation is filled with category default."""
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category=ArbiterCategory.PRE_EXISTING_FAILURE,
        explanation="",
    )
    assert decision.explanation  # must be non-empty
    assert "pre-existing" in decision.explanation.lower() or "base branch" in decision.explanation.lower()
