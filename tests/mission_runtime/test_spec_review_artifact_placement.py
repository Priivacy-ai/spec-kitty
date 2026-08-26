"""ATDD contracts for the PRIMARY spec-review artifact boundary (WP03)."""

from __future__ import annotations

import pytest

import mission_runtime.artifacts as artifacts_mod
from mission_runtime import CommitTarget, MissionArtifactKind, TopologySurface, artifact_home_for


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_spec_review_yaml_is_primary_and_filename_anchored() -> None:
    """Only top-level ``reviews/spec-review-*.yaml`` is durable PRIMARY evidence."""
    path = "kitty-specs/demo-mission/reviews/spec-review-run_20260823_a1.yaml"

    kind = artifacts_mod.kind_for_mission_file(path)

    assert kind is MissionArtifactKind.SPEC_REVIEW
    assert artifacts_mod.is_primary_artifact_kind(kind)
    assert artifact_home_for(kind, CommitTarget(ref="codex/demo")).write_surface is TopologySurface.PRIMARY


def test_legacy_and_nested_review_files_remain_unclassified() -> None:
    """The classifier must not capture historical or nested review artifacts."""
    samples = (
        "kitty-specs/demo-mission/reviews/spec-arch.findings.yaml",
        "kitty-specs/demo-mission/reviews/spec-review-run_20260823_a1.json",
        "kitty-specs/demo-mission/reviews/archive/spec-review-run_20260823_a1.yaml",
    )

    assert all(artifacts_mod.kind_for_mission_file(path) is None for path in samples)


def test_spec_review_classifier_rejects_other_mission_and_accepts_windows_path() -> None:
    assert artifacts_mod.kind_for_mission_file(
        "kitty-specs\\other\\reviews\\spec-review-run_a.yaml", mission_slug="demo"
    ) is None
    assert artifacts_mod.kind_for_mission_file(
        "kitty-specs\\demo\\reviews\\spec-review-run_a.yaml", mission_slug="demo"
    ) is MissionArtifactKind.SPEC_REVIEW
