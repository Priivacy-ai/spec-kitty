"""Artifact-home contract tests for coordination-topology mission artifacts."""

from __future__ import annotations

from mission_runtime import (
    CommitTarget,
    CommitTargetKind,
    MissionArtifactKind,
    artifact_home_for,
    is_coordination_artifact_residue_path,
)


def test_coordination_artifact_home_marks_finalized_artifacts_coord_owned() -> None:
    placement = CommitTarget(
        ref="kitty/mission-demo-01ABCDEF",
        kind=CommitTargetKind.COORDINATION,
    )

    home = artifact_home_for(MissionArtifactKind.ISSUE_MATRIX, placement)

    assert home.commit_target == placement
    assert home.read_surface == "placement"
    assert home.write_surface == "placement"
    assert home.is_coordination_owned


def test_primary_placement_keeps_artifacts_primary_owned() -> None:
    placement = CommitTarget(ref="fix/demo", kind=CommitTargetKind.PRIMARY)

    home = artifact_home_for(MissionArtifactKind.ISSUE_MATRIX, placement)

    assert not home.is_coordination_owned


def test_coordination_residue_path_filter_is_specific_to_finalized_artifacts() -> None:
    assert is_coordination_artifact_residue_path(
        "kitty-specs/demo/plan.md", mission_slug="demo"
    )
    assert is_coordination_artifact_residue_path(
        "kitty-specs/demo/tasks/WP01.md", mission_slug="demo"
    )
    assert is_coordination_artifact_residue_path(
        "kitty-specs/demo/tasks/", mission_slug="demo"
    )
    assert is_coordination_artifact_residue_path(
        "kitty-specs/demo/issue-matrix.md", mission_slug="demo"
    )
    assert not is_coordination_artifact_residue_path(
        "kitty-specs/demo/spec.md", mission_slug="demo"
    )
    assert not is_coordination_artifact_residue_path(
        "kitty-specs/other/plan.md", mission_slug="demo"
    )
