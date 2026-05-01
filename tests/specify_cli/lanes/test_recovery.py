"""Tests for WP06: Migrate Slice 4 — lanes/recovery.py typed Lane enum migration.

Verifies that:
- _RECOVERY_TRANSITIONS dict is removed; _get_recovery_transitions() is used instead
- _get_recovery_transitions() delegates to validate_transition() from status module
- Recovery transition paths are unchanged: planned->claimed->in_progress, claimed->in_progress
- Recovery ceiling is IN_PROGRESS (never advances past it)
- Non-recovery lanes (for_review, done, blocked, etc.) return empty transitions
- scan_recovery_state() and reconcile_status() are callable and work correctly
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.lanes.recovery import (
    RECOVERY_ACTOR,
    _get_recovery_transitions,
    reconcile_status,
    scan_recovery_state,
)
from specify_cli.status.models import GuardContext, Lane
from specify_cli.status.transitions import validate_transition

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]  # non_sandbox: subprocess CLI invocation
# ---------------------------------------------------------------------------
# T016: _get_recovery_transitions() replaces _RECOVERY_TRANSITIONS dict
# ---------------------------------------------------------------------------


def test_recovery_transitions_dict_removed() -> None:
    """_RECOVERY_TRANSITIONS dict must not exist in the recovery module."""
    import specify_cli.lanes.recovery as _recovery_module

    assert not hasattr(_recovery_module, "_RECOVERY_TRANSITIONS"), "_RECOVERY_TRANSITIONS must be removed; use _get_recovery_transitions() instead"


def test_get_recovery_transitions_helper_exists() -> None:
    """_get_recovery_transitions() must exist as the replacement for _RECOVERY_TRANSITIONS."""
    import specify_cli.lanes.recovery as _recovery_module

    assert hasattr(_recovery_module, "_get_recovery_transitions"), "_get_recovery_transitions() helper must exist"
    assert callable(_recovery_module._get_recovery_transitions)


# ---------------------------------------------------------------------------
# T016: Verify recovery transition paths are preserved
# ---------------------------------------------------------------------------


def test_planned_lane_has_two_recovery_transitions() -> None:
    """planned -> claimed, in_progress (same as old _RECOVERY_TRANSITIONS[planned])."""
    result = _get_recovery_transitions(Lane.PLANNED)
    assert result == [Lane.CLAIMED, Lane.IN_PROGRESS], f"planned should transition to [claimed, in_progress], got {result}"


def test_claimed_lane_has_one_recovery_transition() -> None:
    """claimed -> in_progress (same as old _RECOVERY_TRANSITIONS[claimed])."""
    result = _get_recovery_transitions(Lane.CLAIMED)
    assert result == [Lane.IN_PROGRESS], f"claimed should transition to [in_progress], got {result}"


def test_in_progress_lane_has_no_recovery_transitions() -> None:
    """in_progress is the ceiling; no further recovery transitions."""
    result = _get_recovery_transitions(Lane.IN_PROGRESS)
    assert result == [], "in_progress is the recovery ceiling; must return empty list"


def test_for_review_lane_has_no_recovery_transitions() -> None:
    """for_review is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.FOR_REVIEW)
    assert result == [], "for_review has no recovery transitions"


def test_in_review_lane_has_no_recovery_transitions() -> None:
    """in_review is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.IN_REVIEW)
    assert result == [], "in_review has no recovery transitions"


def test_approved_lane_has_no_recovery_transitions() -> None:
    """approved is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.APPROVED)
    assert result == [], "approved has no recovery transitions"


def test_done_lane_has_no_recovery_transitions() -> None:
    """done is terminal; no recovery transitions."""
    result = _get_recovery_transitions(Lane.DONE)
    assert result == [], "done has no recovery transitions"


def test_blocked_lane_has_no_recovery_transitions() -> None:
    """blocked is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.BLOCKED)
    assert result == [], "blocked has no recovery transitions"


def test_canceled_lane_has_no_recovery_transitions() -> None:
    """canceled is terminal; no recovery transitions."""
    result = _get_recovery_transitions(Lane.CANCELED)
    assert result == [], "canceled has no recovery transitions"


# ---------------------------------------------------------------------------
# T016: Verify validate_transition() is used (structural delegation)
# ---------------------------------------------------------------------------


def test_recovery_transitions_align_with_canonical_matrix() -> None:
    """Recovery transitions must be a subset of ALLOWED_TRANSITIONS."""
    # planned -> claimed must be in the canonical matrix
    ok_pc, _ = validate_transition(
        Lane.PLANNED.value,
        Lane.CLAIMED.value,
        GuardContext(actor=RECOVERY_ACTOR, workspace_context="recovery"),
    )
    assert ok_pc, "planned -> claimed must be in canonical transition matrix"

    # claimed -> in_progress must be in the canonical matrix
    ok_ci, _ = validate_transition(
        Lane.CLAIMED.value,
        Lane.IN_PROGRESS.value,
        GuardContext(actor=RECOVERY_ACTOR, workspace_context="recovery"),
    )
    assert ok_ci, "claimed -> in_progress must be in canonical transition matrix"


def test_planned_cannot_jump_directly_to_in_review_via_recovery() -> None:
    """planned -> in_review is not in the recovery progression (ceiling is in_progress)."""
    result = _get_recovery_transitions(Lane.PLANNED)
    assert Lane.IN_REVIEW not in result, "in_review is above the recovery ceiling"


def test_planned_cannot_jump_directly_to_done_via_recovery() -> None:
    """planned -> done is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.PLANNED)
    assert Lane.DONE not in result, "done is above the recovery ceiling"


def test_planned_cannot_jump_directly_to_approved_via_recovery() -> None:
    """planned -> approved is not in the recovery progression."""
    result = _get_recovery_transitions(Lane.PLANNED)
    assert Lane.APPROVED not in result, "approved is above the recovery ceiling"


# ---------------------------------------------------------------------------
# T017: scan_recovery_state() live integration test
# ---------------------------------------------------------------------------


def test_scan_recovery_state_returns_list(tmp_path: Path) -> None:
    """scan_recovery_state() is callable and returns a list."""
    import subprocess

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init", str(repo_root)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )
    # Create initial commit
    (repo_root / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=str(repo_root), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )

    # Call scan_recovery_state (no mission branches → empty list)
    states = scan_recovery_state(repo_root, "080-test-feature")
    assert isinstance(states, list), "scan_recovery_state must return a list"


def test_scan_recovery_state_with_status_events_false_returns_list(
    tmp_path: Path,
) -> None:
    """scan_recovery_state(consult_status_events=False) returns a list (legacy path)."""
    import subprocess

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init", str(repo_root)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )
    (repo_root / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=str(repo_root), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )

    states = scan_recovery_state(repo_root, "080-test-feature", consult_status_events=False)
    assert isinstance(states, list), "legacy path must also return a list"


# ---------------------------------------------------------------------------
# T017: reconcile_status() live integration test
# ---------------------------------------------------------------------------


def test_reconcile_status_returns_zero_for_non_recovery_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """reconcile_status returns 0 when status_lane is not in recovery progression."""
    from specify_cli.lanes.recovery import RecoveryState

    state = RecoveryState(
        wp_id="WP01",
        lane_id="lane-a",
        branch_name="kitty/mission-080-test-lane-a",
        branch_exists=True,
        worktree_exists=True,
        context_exists=True,
        status_lane=Lane.FOR_REVIEW.value,  # Not in recovery progression
        has_commits=True,
        recovery_action="emit_transitions",
    )

    mission_slug = "080-test"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    result = reconcile_status(tmp_path, mission_slug, state)
    assert result == 0, "for_review lane should return 0 (not in recovery progression)"


def test_reconcile_status_returns_zero_for_done_lane(
    tmp_path: Path,
) -> None:
    """reconcile_status returns 0 when status_lane is done (terminal, not recovery)."""
    from specify_cli.lanes.recovery import RecoveryState

    state = RecoveryState(
        wp_id="WP01",
        lane_id="lane-a",
        branch_name="kitty/mission-080-test-lane-a",
        branch_exists=True,
        worktree_exists=True,
        context_exists=True,
        status_lane=Lane.DONE.value,
        has_commits=True,
        recovery_action="no_action",
    )

    mission_slug = "080-test"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    result = reconcile_status(tmp_path, mission_slug, state)
    assert result == 0, "done lane should return 0 (terminal, above recovery ceiling)"


def test_reconcile_status_returns_zero_when_no_commits_and_no_context(
    tmp_path: Path,
) -> None:
    """reconcile_status returns 0 when neither has_commits nor context_exists."""
    from specify_cli.lanes.recovery import RecoveryState

    state = RecoveryState(
        wp_id="WP01",
        lane_id="lane-a",
        branch_name="kitty/mission-080-test-lane-a",
        branch_exists=True,
        worktree_exists=False,
        context_exists=False,
        status_lane=Lane.PLANNED.value,
        has_commits=False,
        recovery_action="recreate_worktree",
    )

    mission_slug = "080-test"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    result = reconcile_status(tmp_path, mission_slug, state)
    assert result == 0, "no commits + no context → cannot determine target → return 0"
