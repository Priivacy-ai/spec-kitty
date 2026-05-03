"""WP06 review artifact consistency gate tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.merge import _enforce_review_artifact_consistency
from specify_cli.post_merge.review_artifact_consistency import (
    find_rejected_review_artifact_conflicts,
    format_review_artifact_conflict,
    review_artifact_conflict_diagnostic,
)
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = pytest.mark.fast


def _write_review_artifact(
    artifact_dir: Path,
    *,
    cycle_number: int,
    verdict: str,
) -> Path:
    artifact = ReviewCycleArtifact(
        cycle_number=cycle_number,
        wp_id="WP01",
        mission_slug="release-320-workflow-reliability-01KQKV85",
        reviewer_agent="reviewer-renata",
        verdict=verdict,
        reviewed_at="2026-05-03T12:00:00+00:00",
        body=f"# Review\n\nVerdict: {verdict}\n",
    )
    path = artifact_dir / f"review-cycle-{cycle_number}.md"
    artifact.write(path)
    return path


def test_latest_rejected_review_artifact_conflicts_with_approved_wp(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVED000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    rejected = _write_review_artifact(artifact_dir, cycle_number=2, verdict="rejected")

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1
    assert findings[0].wp_id == "WP01"
    assert findings[0].lane == "approved"
    assert findings[0].artifact_path == rejected
    assert "review-cycle-2.md has verdict 'rejected'" in format_review_artifact_conflict(
        findings[0],
        repo_root=mission.repo_root,
    )
    diagnostic = review_artifact_conflict_diagnostic(
        findings[0],
        repo_root=mission.repo_root,
    )
    assert diagnostic["diagnostic_code"] == "REJECTED_REVIEW_ARTIFACT_CONFLICT"
    assert diagnostic["branch_or_work_package"] == "WP01"
    assert (
        diagnostic["violated_invariant"]
        == "terminal_wp_latest_review_artifact_must_not_be_rejected"
    )
    assert diagnostic["latest_review_cycle_path"] == str(
        rejected.relative_to(mission.repo_root)
    )
    assert diagnostic["latest_review_cycle_verdict"] == "rejected"
    assert diagnostic["remediation"]


def test_latest_rejected_review_artifact_conflicts_with_done_wp(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="approved")
    _write_review_artifact(artifact_dir, cycle_number=2, verdict="rejected")

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1
    assert findings[0].lane == "done"
    assert findings[0].cycle_number == 2


def test_later_approved_review_artifact_clears_rejected_conflict(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="rejected")
    _write_review_artifact(artifact_dir, cycle_number=2, verdict="approved")

    assert find_rejected_review_artifact_conflicts(mission.mission_dir) == []


def test_merge_review_artifact_consistency_gate_blocks_done_signoff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="rejected")

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_review_artifact_consistency(
            repo_root=mission.repo_root,
            feature_dir=mission.mission_dir,
            mission_slug=mission.mission_slug,
            wp_ids=["WP01"],
        )

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert "diagnostic_code: REJECTED_REVIEW_ARTIFACT_CONFLICT" in output
    assert "branch_or_work_package: WP01" in output
    assert (
        "violated_invariant: "
        "terminal_wp_latest_review_artifact_must_not_be_rejected"
    ) in output
    assert "latest_review_cycle_verdict: rejected" in output
    assert "remediation:" in output
