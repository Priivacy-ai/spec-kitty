"""WP07 (T027-T030): approve-over-rejected must persist override in coord worktree.

T027 RED: stamp the approval override only on the *primary/lane* artifact; verify
the merge gate (which reads from the coord feature_dir) still fires
REJECTED_REVIEW_ARTIFACT_CONFLICT.  Proves the pre-fix split: writing to the
primary does not help the gate that reads coord.

T030 GREEN: after calling ``_persist_review_artifact_override_in_coord``, the
gate no longer fires.

T030 counter-assertion: a genuinely-rejected coord artifact (no override stamped
anywhere) STILL blocks — the gate keeps its real signal.

Relation: FR-008 / #2275 / sibling #1817 under epic #2160.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.tasks_materialization import (
    _persist_review_artifact_override,
    _persist_review_artifact_override_in_coord,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_feature_dir(root: Path, subdir: str) -> Path:
    """Create a minimal mission feature_dir with meta.json."""
    feature_dir = root / subdir / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta = {"mission_id": _MISSION_ID, "mission_slug": _MISSION_SLUG}
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return feature_dir


def _append_approved_event(feature_dir: Path) -> None:
    """Write a status event that puts WP01 in the approved lane."""
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
    """Write a ``verdict: rejected`` ReviewCycleArtifact to *artifact_dir*."""
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


# ---------------------------------------------------------------------------
# T027 RED: stamp primary only — gate still fires on coord
# ---------------------------------------------------------------------------


def test_approve_over_coord_rejected_gate_fires_without_coord_override(
    tmp_path: Path,
) -> None:
    """T027 RED: gate fires when primary override is written but coord is untouched.

    This demonstrates the pre-fix split: ``_persist_review_artifact_override``
    writes to the primary/lane artifact only.  The coord artifact (where the
    merge gate reads via ``find_rejected_review_artifact_conflicts(feature_dir)``)
    is unchanged — still ``verdict: rejected``, no override block.  The gate
    therefore fires ``REJECTED_REVIEW_ARTIFACT_CONFLICT`` even though the
    operator ran ``move-task --to approved --skip-review-artifact-check``.
    """
    # Coord feature_dir: where the merge gate reads artifacts
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_dir = coord_feature_dir / "tasks" / _WP_SLUG
    _write_rejected_artifact(coord_artifact_dir)

    # Primary feature_dir: where the approval handler currently writes the override
    primary_feature_dir = _make_feature_dir(tmp_path, "primary")
    primary_artifact_dir = primary_feature_dir / "tasks" / _WP_SLUG
    primary_artifact_path = _write_rejected_artifact(primary_artifact_dir)

    # Current broken behavior: stamp override on PRIMARY only (the lane checkout)
    _persist_review_artifact_override(
        primary_artifact_path,
        repo_root=primary_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Arbiter override: changes accepted despite review rejection.",
    )

    # Gate reads from COORD — must still fire because coord was never overridden
    findings = find_rejected_review_artifact_conflicts(coord_feature_dir)

    assert findings, (
        "Gate must fire: primary artifact is overridden but coord artifact is not. "
        "The merge gate reads coord, so the false-block still triggers."
    )
    assert findings[0].wp_id == _WP_ID
    assert getattr(findings[0], "verdict", None) == "rejected", (
        "Finding must report the rejected verdict from the coord artifact"
    )
    # Confirm the diagnostic code is the expected one
    from specify_cli.post_merge.review_artifact_consistency import (
        review_artifact_finding_diagnostic,
    )
    diagnostic = review_artifact_finding_diagnostic(findings[0])
    assert diagnostic["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT


# ---------------------------------------------------------------------------
# T030 GREEN: writing override to coord clears the gate
# ---------------------------------------------------------------------------


def test_approve_over_coord_rejected_coord_override_clears_gate(
    tmp_path: Path,
) -> None:
    """T030 GREEN: after ``_persist_review_artifact_override_in_coord``, gate is clear.

    ``_persist_review_artifact_override_in_coord`` writes the override fields
    onto the coord artifact — where the merge gate reads — so
    ``has_complete_override`` fires and ``rejected_review_artifact_for_terminal_lane``
    returns None (no conflict). #1924 honored: the existing override-check in
    ``artifacts.py`` handles the clearing; we do not duplicate it.
    """
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_dir = coord_feature_dir / "tasks" / _WP_SLUG
    _write_rejected_artifact(coord_artifact_dir)

    primary_feature_dir = _make_feature_dir(tmp_path, "primary")
    primary_artifact_dir = primary_feature_dir / "tasks" / _WP_SLUG
    primary_artifact_path = _write_rejected_artifact(primary_artifact_dir)

    # Stamp override on primary (unchanged behavior)
    _persist_review_artifact_override(
        primary_artifact_path,
        repo_root=primary_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Arbiter override: changes accepted despite review rejection.",
    )

    # FIX: also stamp override on COORD (where the gate reads)
    result = _persist_review_artifact_override_in_coord(
        primary_artifact_path,
        coord_feature_dir=coord_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Arbiter override: changes accepted despite review rejection.",
    )

    assert result, "_persist_review_artifact_override_in_coord must return True when coord artifact exists"

    # Gate reads from COORD — must NOT fire now
    findings = find_rejected_review_artifact_conflicts(coord_feature_dir)
    assert not findings, (
        f"Gate must not fire after coord override is stamped, got: {findings}"
    )


# ---------------------------------------------------------------------------
# T030 counter-assertion: genuine rejection (no override) still blocks
# ---------------------------------------------------------------------------


def test_genuine_coord_rejection_without_override_still_blocks(
    tmp_path: Path,
) -> None:
    """T030 counter: a coord artifact rejected with no override still blocks.

    Confirms the gate keeps its real signal — only coordinator-overridden
    rejections are cleared.  A WP in approved lane with an unoverridden
    ``verdict: rejected`` coord artifact must still raise
    ``REJECTED_REVIEW_ARTIFACT_CONFLICT``.
    """
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_dir = coord_feature_dir / "tasks" / _WP_SLUG
    _write_rejected_artifact(coord_artifact_dir)  # no override written

    findings = find_rejected_review_artifact_conflicts(coord_feature_dir)

    assert findings, "Gate must fire: genuine rejected coord artifact with no override"
    assert findings[0].wp_id == _WP_ID
    assert getattr(findings[0], "verdict", None) == "rejected"


# ---------------------------------------------------------------------------
# Artifact placement check: override written WHERE the gate reads (not primary)
# ---------------------------------------------------------------------------


def test_coord_override_artifact_is_written_in_coord_dir_not_primary(
    tmp_path: Path,
) -> None:
    """Integration check: the overridden file is in coord, not only in primary.

    Confirms gate-read symmetry: the coord artifact carries the override fields
    after ``_persist_review_artifact_override_in_coord``, while the primary
    artifact is unaffected (it might not even exist).
    """
    coord_feature_dir = _make_feature_dir(tmp_path, "coord")
    _append_approved_event(coord_feature_dir)
    coord_artifact_dir = coord_feature_dir / "tasks" / _WP_SLUG
    coord_artifact_path = _write_rejected_artifact(coord_artifact_dir)

    primary_feature_dir = _make_feature_dir(tmp_path, "primary")
    primary_artifact_dir = primary_feature_dir / "tasks" / _WP_SLUG
    primary_artifact_path = _write_rejected_artifact(primary_artifact_dir)

    _persist_review_artifact_override_in_coord(
        primary_artifact_path,
        coord_feature_dir=coord_feature_dir,
        wp_id=_WP_ID,
        actor="operator",
        reason="Accepted.",
    )

    # Coord artifact must now carry override fields
    coord_artifact = ReviewCycleArtifact.from_file(coord_artifact_path)
    assert coord_artifact.has_complete_override, (
        "Coord artifact must have a complete override (actor + reason) after stamping"
    )
    assert coord_artifact.override_actor == "operator"
    assert coord_artifact.override_reason == "Accepted."

    # Gate no longer fires on coord
    assert find_rejected_review_artifact_conflicts(coord_feature_dir) == []

    # Primary artifact is NOT auto-modified by _persist_review_artifact_override_in_coord
    # (it was not touched by the coord helper — each direction is explicit)
    primary_artifact = ReviewCycleArtifact.from_file(primary_artifact_path)
    assert not primary_artifact.has_complete_override, (
        "Primary artifact should NOT be modified by the coord-side helper"
    )
