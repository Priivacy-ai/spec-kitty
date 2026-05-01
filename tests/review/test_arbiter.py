"""Tests for the arbiter checklist and rationale model.

Covers all 14 required test cases for T035.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.review.arbiter import (
    ArbiterCategory,
    ArbiterChecklist,
    ArbiterDecision,
    _derive_category,
    _find_review_cycle_artifact,
    _is_arbiter_override,
    _persist_in_artifact,
    create_arbiter_decision,
    get_arbiter_overrides_for_wp,
    parse_category_from_note,
    persist_arbiter_decision,
    prompt_arbiter_checklist,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast


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


# ---------------------------------------------------------------------------
# _find_review_cycle_artifact — coverage for lines 395, 404-407
# ---------------------------------------------------------------------------


def test_find_review_cycle_artifact_no_tasks_dir(tmp_path: Path) -> None:
    """Returns None when the tasks directory does not exist."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)
    # No tasks/ subdirectory created
    result = _find_review_cycle_artifact(feature_dir, "WP01", "review-cycle://any")
    assert result is None


def test_find_review_cycle_artifact_finds_wp_subdir_file(tmp_path: Path) -> None:
    """Returns the review-cycle artifact from the tasks/<wp_id>/ subdirectory."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    wp_subdir = feature_dir / "tasks" / "WP01"
    wp_subdir.mkdir(parents=True)
    artifact = wp_subdir / "review-cycle-001.md"
    artifact.write_text("---\nreview_ref: x\n---\n", encoding="utf-8")

    result = _find_review_cycle_artifact(feature_dir, "WP01", "review-cycle://066-test/WP01/001")
    assert result == artifact


def test_find_review_cycle_artifact_fallback_tasks_level(tmp_path: Path) -> None:
    """Falls back to scanning tasks/ level when <wp_id>/ subdir is absent."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    # No tasks/WP01 subdir — put file at tasks/ level with wp_id in name
    artifact = tasks_dir / "WP01-review-cycle-001.md"
    artifact.write_text("---\nreview_ref: x\n---\n", encoding="utf-8")

    result = _find_review_cycle_artifact(feature_dir, "WP01", "review-cycle://066-test/WP01/001")
    assert result == artifact


def test_find_review_cycle_artifact_returns_none_when_no_match(tmp_path: Path) -> None:
    """Returns None when tasks/ exists but has no matching review-cycle files."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    (feature_dir / "tasks").mkdir(parents=True)
    result = _find_review_cycle_artifact(feature_dir, "WP01", "review-cycle://any")
    assert result is None


# ---------------------------------------------------------------------------
# _persist_in_artifact — no-frontmatter branch (lines 480-485)
# ---------------------------------------------------------------------------


def test_persist_in_artifact_no_frontmatter(tmp_path: Path) -> None:
    """Artifact without frontmatter gets frontmatter prepended with decision."""
    artifact = tmp_path / "review-cycle-001.md"
    artifact.write_text("# Review\n\nSome plain content with no frontmatter.\n", encoding="utf-8")

    checklist = _make_checklist(is_in_scope=False)
    decision = ArbiterDecision(
        arbiter="operator",
        category=ArbiterCategory.CROSS_SCOPE,
        explanation="Finding is outside WP scope",
        checklist=checklist,
        decided_at="2026-04-06T14:00:00+00:00",
    )

    result = _persist_in_artifact(artifact, decision)

    assert result == artifact
    content = artifact.read_text(encoding="utf-8")
    # Should now have frontmatter prepended
    assert content.startswith("---\n")
    assert "arbiter_override" in content
    assert "cross_scope" in content
    # Original content still present
    assert "Some plain content" in content


# ---------------------------------------------------------------------------
# get_arbiter_overrides_for_wp — coverage for lines 525-554
# ---------------------------------------------------------------------------


def test_get_arbiter_overrides_empty_when_no_tasks_dir(tmp_path: Path) -> None:
    """Returns empty list when tasks/ directory does not exist."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)
    result = get_arbiter_overrides_for_wp(feature_dir, "WP01")
    assert result == []


def test_get_arbiter_overrides_empty_when_no_wp_subdir(tmp_path: Path) -> None:
    """Returns empty list when tasks/<wp_id>/ does not exist."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    (feature_dir / "tasks").mkdir(parents=True)
    result = get_arbiter_overrides_for_wp(feature_dir, "WP01")
    assert result == []


def test_get_arbiter_overrides_from_standalone_json(tmp_path: Path) -> None:
    """Reads decisions from standalone arbiter-override-N.json files."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    wp_subdir = feature_dir / "tasks" / "WP01"
    wp_subdir.mkdir(parents=True)

    decision_data = {
        "arbiter": "operator",
        "category": "infra_environmental",
        "explanation": "CI was flaky",
        "checklist": {
            "is_pre_existing": False,
            "is_correct_context": True,
            "is_in_scope": True,
            "is_environmental": True,
            "should_follow_on": False,
        },
        "decided_at": "2026-04-06T14:00:00+00:00",
    }
    json_file = wp_subdir / "arbiter-override-1.json"
    json_file.write_text(json.dumps(decision_data), encoding="utf-8")

    result = get_arbiter_overrides_for_wp(feature_dir, "WP01")
    assert len(result) == 1
    assert result[0]["category"] == "infra_environmental"
    assert result[0]["explanation"] == "CI was flaky"


def test_get_arbiter_overrides_from_review_cycle_frontmatter(tmp_path: Path) -> None:
    """Reads decisions embedded in review-cycle-*.md frontmatter."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    wp_subdir = feature_dir / "tasks" / "WP01"
    wp_subdir.mkdir(parents=True)

    checklist = _make_checklist(is_pre_existing=True)
    decision = ArbiterDecision(
        arbiter="robert",
        category=ArbiterCategory.PRE_EXISTING_FAILURE,
        explanation="Already broken on main",
        checklist=checklist,
        decided_at="2026-04-06T14:00:00+00:00",
    )

    # Create review-cycle artifact with embedded arbiter_override
    artifact = wp_subdir / "review-cycle-001.md"
    artifact.write_text(
        "---\nreview_ref: review-cycle://066-test/WP01/001\n---\n\n# Review\n\nFeedback here.\n",
        encoding="utf-8",
    )
    _persist_in_artifact(artifact, decision)

    result = get_arbiter_overrides_for_wp(feature_dir, "WP01")
    assert len(result) == 1
    assert result[0]["category"] == "pre_existing_failure"
    assert "Already broken" in result[0]["explanation"]


# ---------------------------------------------------------------------------
# _is_arbiter_override — additional branches (lines 355, 357, 365)
# ---------------------------------------------------------------------------


def test_is_arbiter_override_wrong_old_lane(tmp_path: Path) -> None:
    """old_lane != 'planned' returns False even with force and rejection event."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="in_progress",  # not 'planned'
        target_lane="for_review",
        force=True,
    )
    assert result is False


def test_is_arbiter_override_non_forward_target_lane(tmp_path: Path) -> None:
    """target_lane not in (for_review, claimed, approved) returns False."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="planned",
        target_lane="blocked",  # not a forward lane
        force=True,
    )
    assert result is False


def test_is_arbiter_override_no_events_for_wp(tmp_path: Path) -> None:
    """No events for this WP returns False."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    feature_dir.mkdir(parents=True)
    # Write an event for a *different* WP
    _write_event(
        feature_dir,
        _make_event(wp_id="WP02", from_lane=Lane.FOR_REVIEW, to_lane=Lane.PLANNED, review_ref="feedback://066-test/WP02/20260406T120000Z-abc123.md"),
    )

    result = _is_arbiter_override(
        feature_dir=feature_dir,
        wp_id="WP01",
        old_lane="planned",
        target_lane="for_review",
        force=True,
    )
    assert result is False


# ---------------------------------------------------------------------------
# parse_category_from_note — empty-explanation branch (line 177)
# ---------------------------------------------------------------------------


def test_parse_category_from_note_bracket_no_explanation() -> None:
    """'[pre_existing_failure]' with no trailing explanation uses category default."""
    cat, expl = parse_category_from_note("[pre_existing_failure]")
    assert cat == ArbiterCategory.PRE_EXISTING_FAILURE
    assert expl  # must be non-empty (filled from _CATEGORY_DEFAULTS)
    assert "pre" in expl.lower() or "base" in expl.lower()


# ---------------------------------------------------------------------------
# create_arbiter_decision — enum-category branch (line 212) and CUSTOM
# fallback explanation (line 215 "or" branch)
# ---------------------------------------------------------------------------


def test_create_arbiter_decision_enum_category_branch() -> None:
    """Passing an ArbiterCategory enum (not a string) exercises the else branch."""
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category=ArbiterCategory.WRONG_CONTEXT,  # enum, not string
        explanation="Reviewer was confused",
    )
    assert decision.category == ArbiterCategory.WRONG_CONTEXT
    assert decision.explanation == "Reviewer was confused"


def test_create_arbiter_decision_custom_empty_explanation_uses_fallback() -> None:
    """CUSTOM with empty explanation hits the 'or f"Override: {cat}"' branch."""
    decision = create_arbiter_decision(
        arbiter_name="operator",
        category=ArbiterCategory.CUSTOM,  # default is empty string → or-branch
        explanation="",
    )
    assert decision.explanation  # must be non-empty
    assert "Override" in decision.explanation or "custom" in decision.explanation.lower()


# ---------------------------------------------------------------------------
# _persist_in_artifact — empty YAML frontmatter (line 468: data = {})
# ---------------------------------------------------------------------------


def test_persist_in_artifact_empty_yaml_frontmatter(tmp_path: Path) -> None:
    """Artifact with empty YAML frontmatter (---\n---) still gets decision added."""
    artifact = tmp_path / "review-cycle-001.md"
    # Frontmatter block present but empty (yaml.load returns None)
    artifact.write_text("---\n\n---\n\n# Review\n\nFeedback here.\n", encoding="utf-8")

    checklist = _make_checklist(is_environmental=True)
    decision = ArbiterDecision(
        arbiter="operator",
        category=ArbiterCategory.INFRA_ENVIRONMENTAL,
        explanation="CI server timeout",
        checklist=checklist,
        decided_at="2026-04-06T14:00:00+00:00",
    )

    result = _persist_in_artifact(artifact, decision)

    assert result == artifact
    content = artifact.read_text(encoding="utf-8")
    assert "arbiter_override" in content
    assert "infra_environmental" in content


# ---------------------------------------------------------------------------
# get_arbiter_overrides_for_wp — malformed JSON silently skipped (lines 539-540)
# ---------------------------------------------------------------------------


def test_get_arbiter_overrides_skips_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON in arbiter-override-N.json is silently skipped."""
    feature_dir = tmp_path / "kitty-specs" / "066-test"
    wp_subdir = feature_dir / "tasks" / "WP01"
    wp_subdir.mkdir(parents=True)

    # Write one malformed JSON file
    (wp_subdir / "arbiter-override-1.json").write_text("NOT VALID JSON {{{", encoding="utf-8")

    # Write one valid JSON file
    valid_data = {
        "arbiter": "operator",
        "category": "custom",
        "explanation": "Custom reason",
        "checklist": {
            "is_pre_existing": False,
            "is_correct_context": True,
            "is_in_scope": True,
            "is_environmental": False,
            "should_follow_on": False,
        },
        "decided_at": "2026-04-06T14:00:00+00:00",
    }
    (wp_subdir / "arbiter-override-2.json").write_text(json.dumps(valid_data), encoding="utf-8")

    result = get_arbiter_overrides_for_wp(feature_dir, "WP01")
    # Malformed file silently skipped; valid file returned
    assert len(result) == 1
    assert result[0]["category"] == "custom"


# ---------------------------------------------------------------------------
# prompt_arbiter_checklist — mocked console (lines 260-322)
# ---------------------------------------------------------------------------


def _make_mock_console(answers: list[str]) -> MagicMock:
    """Return a mock Rich Console whose .input() returns answers in sequence."""
    console = MagicMock()
    console.input.side_effect = answers
    return console


def test_prompt_arbiter_checklist_pre_existing_category() -> None:
    """Q1=y → PRE_EXISTING_FAILURE; explanation taken from input."""
    # Q1=y, Q2=y, Q3=y, Q4=n, Q5=n → category=PRE_EXISTING_FAILURE
    # Explanation prompt: "some explanation"
    console = _make_mock_console(["y", "y", "y", "n", "n", "some explanation"])
    decision = prompt_arbiter_checklist("WP01", "robert", console)

    assert decision.category == ArbiterCategory.PRE_EXISTING_FAILURE
    assert decision.arbiter == "robert"
    assert decision.explanation == "some explanation"
    assert decision.checklist.is_pre_existing is True


def test_prompt_arbiter_checklist_custom_requires_non_empty_explanation() -> None:
    """CUSTOM category loops until non-empty explanation is given."""
    # All defaults → CUSTOM category
    # First explanation attempt is empty (loops), second is non-empty
    console = _make_mock_console(["n", "y", "y", "n", "n", "", "my custom reason"])
    decision = prompt_arbiter_checklist("WP01", "operator", console)

    assert decision.category == ArbiterCategory.CUSTOM
    assert decision.explanation == "my custom reason"


def test_prompt_arbiter_checklist_wrong_context_category() -> None:
    """Q1=n, Q2=n → WRONG_CONTEXT; default explanation accepted on empty input."""
    # Q1=n, Q2=n → WRONG_CONTEXT
    # Explanation prompt: empty string → uses default
    console = _make_mock_console(["n", "n", "y", "n", "n", ""])
    decision = prompt_arbiter_checklist("WP01", "claude", console)

    assert decision.category == ArbiterCategory.WRONG_CONTEXT
    assert decision.explanation  # non-empty default
    assert decision.arbiter == "claude"


def test_prompt_arbiter_checklist_accepts_default_answers() -> None:
    """Empty Y/N answers use the per-question default."""
    # All empty answers: defaults are Q1=N, Q2=Y, Q3=Y, Q4=N, Q5=N → CUSTOM
    # Then provide a non-empty explanation
    console = _make_mock_console(["", "", "", "", "", "follow-on required"])
    decision = prompt_arbiter_checklist("WP01", "operator", console)

    # All defaults → CUSTOM
    assert decision.category == ArbiterCategory.CUSTOM
    assert decision.explanation == "follow-on required"
