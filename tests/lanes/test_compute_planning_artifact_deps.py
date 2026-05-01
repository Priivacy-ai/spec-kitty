"""Cross-mode dependency edges in lane compute (P2.7).

The original lane planner iterated only ``code_wp_ids`` when computing
``lane_deps``. Planning-artifact WPs were assembled into the canonical
``lane-planning`` lane *afterwards* with ``depends_on_lanes=()``, which
silently dropped two real dependency cases:

1. A code WP declares it depends on a planning-artifact WP (e.g. an
   ADR or research note must exist before code can be written against
   it). Lane(code) should depend_on_lanes = (PLANNING_LANE_ID,).
2. A planning-artifact WP declares it depends on a code WP (e.g. a
   migration runbook is finalised after the migration code lands).
   The planning lane should depend_on_lanes = (lane(code),).

These tests pin both directions of the cross-mode dependency edge.
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.compute import PLANNING_LANE_ID, compute_lanes
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest


pytestmark = [pytest.mark.fast]


def _code(wp_id: str, owned: tuple[str, ...] = ()) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode.CODE_CHANGE,
        owned_files=owned or (f"src/{wp_id.lower()}.py",),
        authoritative_surface=f"src/{wp_id.lower()}/",
    )


def _plan(wp_id: str) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode.PLANNING_ARTIFACT,
        owned_files=(f"kitty-specs/feature/research/{wp_id.lower()}.md",),
        authoritative_surface="kitty-specs/feature/research/",
    )


def test_code_wp_depends_on_planning_wp_creates_lane_edge(tmp_path):
    """Case 1: code WP depends on planning WP → code lane depends on planning lane."""
    deps = {
        "WP01": [],  # planning-artifact (e.g. ADR)
        "WP02": ["WP01"],  # code WP that depends on the ADR
    }
    manifests = {
        "WP01": _plan("WP01"),
        "WP02": _code("WP02"),
    }

    manifest = compute_lanes(
        dependency_graph=deps,
        ownership_manifests=manifests,
        mission_slug="feature",
        target_branch="main",
    )

    by_id = {lane.lane_id: lane for lane in manifest.lanes}
    assert PLANNING_LANE_ID in by_id, "FR-005 / P2.7 regression: planning lane must exist when the mission has any planning-artifact WPs."
    code_lane = next(lane for lane in manifest.lanes if lane.lane_id != PLANNING_LANE_ID)
    assert PLANNING_LANE_ID in code_lane.depends_on_lanes, (
        f"FR-005 / P2.7 regression: code lane {code_lane.lane_id!r} declares "
        f"WP02 -> WP01 (planning) but its depends_on_lanes does not include "
        f"PLANNING_LANE_ID. Got {code_lane.depends_on_lanes!r}. The lane "
        "planner must capture cross-mode (code -> planning) dependencies."
    )


def test_planning_wp_depends_on_code_wp_creates_lane_edge(tmp_path):
    """Case 2: planning WP depends on code WP → planning lane depends on code lane."""
    deps = {
        "WP01": [],  # code WP (the implementation)
        "WP02": ["WP01"],  # planning-artifact WP (e.g. migration runbook)
    }
    manifests = {
        "WP01": _code("WP01"),
        "WP02": _plan("WP02"),
    }

    manifest = compute_lanes(
        dependency_graph=deps,
        ownership_manifests=manifests,
        mission_slug="feature",
        target_branch="main",
    )

    by_id = {lane.lane_id: lane for lane in manifest.lanes}
    assert PLANNING_LANE_ID in by_id

    planning_lane = by_id[PLANNING_LANE_ID]
    # The single code lane in this fixture is whichever lane is not planning.
    code_lane_ids = [lane.lane_id for lane in manifest.lanes if lane.lane_id != PLANNING_LANE_ID]
    assert len(code_lane_ids) == 1
    code_lane_id = code_lane_ids[0]

    assert code_lane_id in planning_lane.depends_on_lanes, (
        f"FR-005 / P2.7 regression: planning lane declares WP02 (planning) -> "
        f"WP01 (code) but its depends_on_lanes does not include the code lane "
        f"{code_lane_id!r}. Got {planning_lane.depends_on_lanes!r}."
    )


def test_no_planning_wp_means_no_planning_lane_dep_seeded():
    """Sanity: if there are no planning WPs, lane_deps stays code-only."""
    deps = {"WP01": [], "WP02": ["WP01"]}
    manifests = {
        "WP01": _code("WP01"),
        "WP02": _code("WP02", owned=("src/wp02.py",)),
    }
    manifest = compute_lanes(
        dependency_graph=deps,
        ownership_manifests=manifests,
        mission_slug="feature",
        target_branch="main",
    )
    assert all(lane.lane_id != PLANNING_LANE_ID for lane in manifest.lanes), "Planning lane must NOT be synthesised when there are zero planning-artifact WPs."


def test_planning_lane_parallel_group_honours_code_dependency():
    """Case 2 check: planning lane that depends on a code lane sits at depth >= 1.

    Without the P2.7 fix, the planning lane was always assigned
    parallel_group=0 even when it had upstream lane dependencies, which
    made the lane planner think it could run concurrently with its
    upstream — silently violating the dependency contract.
    """
    deps = {
        "WP01": [],
        "WP02": ["WP01"],  # planning depends on code
    }
    manifests = {
        "WP01": _code("WP01"),
        "WP02": _plan("WP02"),
    }
    manifest = compute_lanes(
        dependency_graph=deps,
        ownership_manifests=manifests,
        mission_slug="feature",
        target_branch="main",
    )
    by_id = {lane.lane_id: lane for lane in manifest.lanes}
    code_lane = next(lane for lane in manifest.lanes if lane.lane_id != PLANNING_LANE_ID)
    planning_lane = by_id[PLANNING_LANE_ID]

    assert planning_lane.parallel_group > code_lane.parallel_group, (
        "Planning lane that depends on a code lane must sit at a strictly "
        "higher parallel_group depth so the runtime does not schedule them "
        "concurrently. Got planning="
        f"{planning_lane.parallel_group}, code={code_lane.parallel_group}."
    )
