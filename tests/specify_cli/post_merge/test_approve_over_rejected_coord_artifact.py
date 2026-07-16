"""WP07: confirm review-artifact override remains primary-owned.

This test file validates the post-cleanup behavior where override metadata is
written only to the primary/lane artifact. The merge gate continues to read the
coord artifact set via ``find_rejected_review_artifact_conflicts``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.tasks_materialization import (
    _persist_review_artifact_override,
)
from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
    find_rejected_review_artifact_conflicts,
)
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast

_MISSION_SLUG = "release-320-workflow-reliability-01KQKV85"
_MISSION_ID = "01KQKV85RELIABILITY000000000"
_WP_ID = "WP01"
_WP_SLUG = "WP01-regression-harness"


def _make_feature_dir(root: Path, subdir: str) -> Path:
    feature_dir = root / subdir / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta = {"mission_id": _MISSION_ID, "mission_slug": _MISSION_SLUG}
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return feature_dir


def _append_approved_event(feature_dir: Path) -> None:
    event = StatusEvent(
        event_id="01KQKV85WP07STATUS0000001",
        mission_slug=_MISSION_SLUG,
        mission_id=_MISSION_ID,
        wp_id=_WP_ID,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        at="2026-06-30T12:00:00Z",
        actor="operator",
        force=False,
        execution_mode="worktree",
        reason="approved for merge",
    )
    append_event(feature_dir, event)


def _write_rejected_artifact(artifact_dir: Path) -> Path:
    artifact = ReviewCycleArtifact(
        cycle_number=1,
        wp_id=_WP_ID,
        mission_slug=_MISSION_SLUG,
        reviewer_agent="reviewer-renata",
        verdict="rejected",
        reviewed_at="2026-06-30T11:00:00+00:00",
        body="# Review\n\nVerdict: rejected — changes needed.\n",
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "review-cycle-1.md"
    artifact.write(path)
    return path


def test_approve_over_coord_rejected_gate_fires_when_only_primary_override_exists(
    tmp_path: Path,
) -> None:
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_dir = coord_feature_dir / "tasks" / _WP_SLUG
    _write_rejected_artifact(coord_artifact_dir)

    primary_feature_dir = _make_feature_dir(tmp_path, "primary")
    primary_artifact_path = _write_rejected_artifact(primary_feature_dir / "tasks" / _WP_SLUG)

    _persist_review_artifact_override(
        primary_artifact_path,
        repo_root=primary_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Arbiter override: changes accepted despite review rejection.",
    )

    findings = find_rejected_review_artifact_conflicts(coord_feature_dir)
    assert findings
    assert findings[0].wp_id == _WP_ID
    assert findings[0].verdict == "rejected"

    from specify_cli.post_merge.review_artifact_consistency import (
        review_artifact_finding_diagnostic,
    )

    diagnostic = review_artifact_finding_diagnostic(findings[0])
    assert diagnostic["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT


def test_primary_override_is_not_mirrored_to_coord(
    tmp_path: Path,
) -> None:
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_path = _write_rejected_artifact(coord_feature_dir / "tasks" / _WP_SLUG)

    primary_feature_dir = _make_feature_dir(tmp_path, "primary")
    primary_artifact_path = _write_rejected_artifact(
        primary_feature_dir / "tasks" / _WP_SLUG
    )

    _persist_review_artifact_override(
        primary_artifact_path,
        repo_root=primary_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Arbiter override: changes accepted despite review rejection.",
    )

    primary_artifact = ReviewCycleArtifact.from_file(primary_artifact_path)
    assert primary_artifact.has_complete_override
    assert primary_artifact.override_actor == "operator"

    coord_artifact = ReviewCycleArtifact.from_file(coord_artifact_path)
    assert not coord_artifact.has_complete_override

    assert find_rejected_review_artifact_conflicts(coord_feature_dir)


def test_genuine_coord_rejection_without_override_still_blocks(
    tmp_path: Path,
) -> None:
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    _write_rejected_artifact(coord_feature_dir / "tasks" / _WP_SLUG)

    findings = find_rejected_review_artifact_conflicts(coord_feature_dir)

    assert findings
    assert findings[0].wp_id == _WP_ID
    assert findings[0].verdict == "rejected"
