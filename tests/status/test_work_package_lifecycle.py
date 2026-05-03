"""Tests for shared work-package lifecycle start operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import reduce
from specify_cli.status.store import append_event, read_events
from specify_cli.status.work_package_lifecycle import (
    WorkPackageClaimConflict,
    WorkPackageStartRejected,
    _actor_key,
    _actors_compatible,
    _repo_root_for_lock,
    start_implementation_status,
    start_review_status,
)

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _disable_status_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


def _feature_dir(tmp_path: Path) -> Path:
    feature_dir = tmp_path / "kitty-specs" / "099-lifecycle-test"
    feature_dir.mkdir(parents=True)
    return feature_dir


def _event(
    event_id: str,
    *,
    from_lane: Lane,
    to_lane: Lane,
    actor: str = "claude",
    wp_id: str = "WP01",
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug="099-lifecycle-test",
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=f"2026-04-26T10:00:0{event_id[-1]}+00:00",
        actor=actor,
        force=False,
        execution_mode="worktree",
    )


def test_start_implementation_batches_planned_to_in_progress(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.from_lane == Lane.PLANNED
    assert result.to_lane == Lane.IN_PROGRESS
    assert result.no_op is False

    events = read_events(feature_dir)
    assert [(event.from_lane, event.to_lane) for event in events] == [
        (Lane.PLANNED, Lane.CLAIMED),
        (Lane.CLAIMED, Lane.IN_PROGRESS),
    ]
    snapshot = reduce(events)
    assert snapshot.work_packages["WP01"]["lane"] == Lane.IN_PROGRESS


def test_backgrounded_implementation_start_does_not_strand_claimed(tmp_path: Path) -> None:
    """A normal start writes claim and progress evidence as one durable batch."""
    feature_dir = _feature_dir(tmp_path)

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.to_lane == Lane.IN_PROGRESS
    events = read_events(feature_dir)
    assert [event.to_lane for event in events] == [Lane.CLAIMED, Lane.IN_PROGRESS]
    assert reduce(events).work_packages["WP01"]["lane"] == Lane.IN_PROGRESS


def test_start_implementation_resumes_claimed_same_actor(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(feature_dir, _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED))

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.from_lane == Lane.CLAIMED
    assert result.status_changed is True
    assert read_events(feature_dir)[-1].to_lane == Lane.IN_PROGRESS


def test_interrupted_implementation_claim_recovers_with_progress_event(tmp_path: Path) -> None:
    """If only a claim exists, the same actor records recovery into progress."""
    feature_dir = _feature_dir(tmp_path)
    append_event(feature_dir, _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED))

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    events = read_events(feature_dir)
    assert result.from_lane == Lane.CLAIMED
    assert events[-1].from_lane == Lane.CLAIMED
    assert events[-1].to_lane == Lane.IN_PROGRESS
    assert reduce(events).work_packages["WP01"]["lane"] == Lane.IN_PROGRESS


def test_start_implementation_rejects_claimed_different_actor(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED, actor="other-agent"),
    )

    with pytest.raises(WorkPackageClaimConflict) as exc_info:
        start_implementation_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="claude",
            workspace_context="worktree:/tmp/wp01",
            execution_mode="worktree",
            repo_root=tmp_path,
        )

    assert exc_info.value.claimed_by == "other-agent"
    assert len(read_events(feature_dir)) == 1


def test_interrupted_claim_by_different_actor_returns_claim_diagnostic(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED, actor="other-agent"),
    )

    with pytest.raises(WorkPackageClaimConflict, match="already claimed") as exc_info:
        start_implementation_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="claude",
            workspace_context="worktree:/tmp/wp01",
            execution_mode="worktree",
            repo_root=tmp_path,
        )

    assert exc_info.value.claimed_by == "other-agent"
    assert exc_info.value.requesting_actor == "claude"
    assert reduce(read_events(feature_dir)).work_packages["WP01"]["lane"] == Lane.CLAIMED


def test_start_implementation_noops_in_progress_same_actor(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(feature_dir, _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED))
    append_event(feature_dir, _event("01BBBB0000000000000000002B", from_lane=Lane.CLAIMED, to_lane=Lane.IN_PROGRESS))

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.no_op is True
    assert len(read_events(feature_dir)) == 2


def test_start_implementation_rejects_in_progress_different_actor(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(feature_dir, _event("01AAAA0000000000000000001A", from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED))
    append_event(
        feature_dir,
        _event("01BBBB0000000000000000002B", from_lane=Lane.CLAIMED, to_lane=Lane.IN_PROGRESS, actor="other-agent"),
    )

    with pytest.raises(WorkPackageClaimConflict) as exc_info:
        start_implementation_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="claude",
            workspace_context="worktree:/tmp/wp01",
            execution_mode="worktree",
            repo_root=tmp_path,
        )

    assert exc_info.value.claimed_by == "other-agent"


def test_start_implementation_allows_forced_rework_from_review_lane(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01CCCC0000000000000000003C", from_lane=Lane.IN_PROGRESS, to_lane=Lane.FOR_REVIEW, actor="implementer"),
    )

    result = start_implementation_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="claude",
        workspace_context="worktree:/tmp/wp01",
        execution_mode="worktree",
        repo_root=tmp_path,
        allow_rework=True,
        rework_reason="review changes requested",
    )

    assert result.from_lane == Lane.FOR_REVIEW
    assert result.to_lane == Lane.IN_PROGRESS
    assert read_events(feature_dir)[-1].reason == "review changes requested"


def test_start_implementation_rejects_unstartable_lane(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(feature_dir, _event("01DDDD0000000000000000004D", from_lane=Lane.APPROVED, to_lane=Lane.DONE))

    with pytest.raises(WorkPackageStartRejected, match="cannot start implementation"):
        start_implementation_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="claude",
            workspace_context="worktree:/tmp/wp01",
            execution_mode="worktree",
            repo_root=tmp_path,
        )


def test_start_review_allows_reviewer_after_implementer_for_review(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01CCCC0000000000000000003C", from_lane=Lane.IN_PROGRESS, to_lane=Lane.FOR_REVIEW, actor="implementer"),
    )

    result = start_review_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="reviewer",
        workspace_context="review:/tmp/repo",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.from_lane == Lane.FOR_REVIEW
    assert read_events(feature_dir)[-1].to_lane == Lane.IN_REVIEW


def test_slow_review_claim_uses_in_review_not_claimed(tmp_path: Path) -> None:
    """Review starts never reuse the implementation-only claimed lane."""
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01CCCC0000000000000000003C", from_lane=Lane.IN_PROGRESS, to_lane=Lane.FOR_REVIEW, actor="implementer"),
    )

    result = start_review_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="reviewer",
        workspace_context="review:/tmp/repo",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    events = read_events(feature_dir)
    assert result.to_lane == Lane.IN_REVIEW
    assert events[-1].from_lane == Lane.FOR_REVIEW
    assert events[-1].to_lane == Lane.IN_REVIEW
    assert reduce(events).work_packages["WP01"]["lane"] == Lane.IN_REVIEW


def test_start_review_noops_same_reviewer(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01DDDD0000000000000000004D", from_lane=Lane.FOR_REVIEW, to_lane=Lane.IN_REVIEW, actor="reviewer-a"),
    )

    result = start_review_status(
        feature_dir=feature_dir,
        mission_slug="099-lifecycle-test",
        wp_id="WP01",
        actor="reviewer-a",
        workspace_context="review:/tmp/repo",
        execution_mode="worktree",
        repo_root=tmp_path,
    )

    assert result.no_op is True
    assert len(read_events(feature_dir)) == 1


def test_start_review_rejects_second_reviewer(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)
    append_event(
        feature_dir,
        _event("01DDDD0000000000000000004D", from_lane=Lane.FOR_REVIEW, to_lane=Lane.IN_REVIEW, actor="reviewer-a"),
    )

    with pytest.raises(WorkPackageClaimConflict) as exc_info:
        start_review_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="reviewer-b",
            workspace_context="review:/tmp/repo",
            execution_mode="worktree",
            repo_root=tmp_path,
        )

    assert exc_info.value.claimed_by == "reviewer-a"


def test_start_review_rejects_non_review_lane(tmp_path: Path) -> None:
    feature_dir = _feature_dir(tmp_path)

    with pytest.raises(WorkPackageStartRejected, match="cannot start review"):
        start_review_status(
            feature_dir=feature_dir,
            mission_slug="099-lifecycle-test",
            wp_id="WP01",
            actor="reviewer-a",
            workspace_context="review:/tmp/repo",
            execution_mode="worktree",
            repo_root=tmp_path,
        )


def test_lifecycle_helpers_normalize_lock_roots_and_actors(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "099-lifecycle-test"

    assert _repo_root_for_lock(feature_dir, None) == tmp_path
    assert _repo_root_for_lock(tmp_path / "loose-feature", None) == tmp_path / "loose-feature"
    assert _actor_key(None) is None
    assert _actors_compatible(None, "claude") is True


def test_claimed_lane_surfaces_as_doing_in_dashboard() -> None:
    assert _KANBAN_COLUMN_FOR_LANE[Lane.CLAIMED] == "doing"
