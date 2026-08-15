"""#2959 (WP01 / FR-001): the review-artifact override WRITE must land on the
SAME partition the merge review-artifact gate READS.

On a coord-topology mission the merge gate resolves each WP's lane state from
its COORD ``STATUS_STATE`` home (``post_merge/review_artifact_consistency.py``
→ ``resolve_artifact_surface``). Before this WP,
``_persist_review_artifact_override`` derived the emit's ``feature_dir`` from
the PRIMARY-derived artifact path (``artifact_path.parents[2]``), so the
override was appended to the PRIMARY event log — a surface the gate never reads
under a materialised coord topology. The gate therefore kept seeing the stale
rejection and refused the merge: the #2959 deadlock, with no override escape
hatch.

This is the red-first, live-coord-topology proof (NFR-001): the coord worktree
is genuinely materialised by the shared ``coord_topology_mission`` fixture (real
git, no resolver patched), so the write partition and the gate's read partition
are DIFFERENT dirs. The test is RED before the reroute (override on primary,
gate reads coord → not visible) and GREEN after (override on coord → visible on
the gate's read surface).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.tasks_materialization import (
    _persist_review_artifact_override,
)
from specify_cli.post_merge.review_artifact_consistency import (
    _resolve_lane_state_read_dir,
)
from specify_cli.status import materialize_snapshot
from specify_cli.status.models import ReviewOverride
from tests.integration.coord_topology_fixture import (  # noqa: F401 -- pytest fixture re-export
    coord_topology_mission,
)

pytestmark = [pytest.mark.git_repo]

_WP_ID = "WP01"
_WP_SLUG = "WP01-fixture-slug"
_REASON = "Arbiter override: changes accepted despite the stale review rejection."


def _override_review_slot(read_dir: Path) -> dict | None:
    """Return WP01's reduced ``review`` snapshot slot at *read_dir*, or None."""
    snapshot = materialize_snapshot(read_dir)
    state = snapshot.work_packages.get(_WP_ID)
    if state is None:
        return None
    return state.get("review")


def test_override_write_lands_on_gate_read_partition(
    coord_topology_mission,  # noqa: F811 -- fixture shadows the re-exported name
) -> None:
    """The override must be visible on the STATUS_STATE surface the gate reads.

    RED (pre-WP01): the write derived ``feature_dir`` from the PRIMARY artifact
    path, so the override annotation landed on the PRIMARY event log; the gate
    reads the COORD husk → ``review`` slot absent → merge stays deadlocked.
    GREEN (post-WP01): the write resolves the COORD ``STATUS_STATE`` surface via
    the placement seam, so the override lands where the gate reads it.
    """
    ctx = coord_topology_mission

    # The gate resolves lane state from the mission's STATUS_STATE home. Under a
    # materialised coord topology that is the coord husk, NOT the primary dir the
    # caller happened to pass — fixture invariant that makes this test meaningful.
    gate_read_dir = _resolve_lane_state_read_dir(ctx.primary_feature_dir)
    assert gate_read_dir == ctx.coord_feature_dir, (
        "fixture invariant: the gate must read the coord husk for a coord "
        "topology, or this test cannot distinguish the two partitions"
    )
    assert gate_read_dir != ctx.primary_feature_dir

    # The override caller hands a PRIMARY-derived artifact path (review-cycle
    # artifacts live under the primary tasks/ tree): parents[2] == primary dir.
    artifact_path = (
        ctx.primary_feature_dir / "tasks" / _WP_SLUG / "review-cycle-1.md"
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("# review\nVerdict: rejected\n", encoding="utf-8")
    assert artifact_path.parents[2] == ctx.primary_feature_dir

    _persist_review_artifact_override(
        artifact_path,
        repo_root=ctx.repo,
        wp_id=_WP_ID,
        actor="operator",
        reason=_REASON,
    )

    # The override must be present on the gate's READ surface (coord husk).
    gate_slot = _override_review_slot(gate_read_dir)
    assert gate_slot is not None, (
        "override not visible on the gate's STATUS_STATE read surface — the "
        "write landed on the wrong partition (the #2959 deadlock)"
    )
    override = ReviewOverride.from_dict(gate_slot)
    assert override.complete
    assert override.reason == _REASON

    # And it must NOT have leaked onto the PRIMARY partition (proving the write
    # MOVED to the gate's partition, not merely also-wrote it).
    primary_slot = _override_review_slot(ctx.primary_feature_dir)
    assert primary_slot is None, (
        "override leaked onto the PRIMARY partition; the write must target the "
        "COORD STATUS_STATE surface the gate reads, not the primary event log"
    )
