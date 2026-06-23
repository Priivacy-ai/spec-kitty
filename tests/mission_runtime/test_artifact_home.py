"""Artifact-home contract tests for coordination-topology mission artifacts."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    MissionTopology,
    artifact_home_for,
    is_coordination_artifact_residue_path,
)
from mission_runtime.artifacts import kind_is_coordination_residue


def test_placement_artifact_home_carries_ref_only_placement() -> None:
    """A placement-kind artifact's home carries the ref-only CommitTarget (C-007).

    The retired ``is_coordination_owned`` per-ref enum routing is gone — the
    coord-vs-primary residue decision now reads the STORED topology via
    ``kind_is_coordination_residue`` (covered below), not a ``CommitTarget.kind``.
    This pins the home's surface contract + the ref-only placement it carries.
    """
    placement = CommitTarget(ref="kitty/mission-demo-01ABCDEF")

    home = artifact_home_for(MissionArtifactKind.ISSUE_MATRIX, placement)

    assert home.commit_target == placement
    assert home.read_surface == "placement"
    assert home.write_surface == "placement"
    assert home.ignores_primary_coord_residue is True


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
    # Remediated 2026-06-23: under coordination topology the planning SOURCE docs
    # (spec.md / data-model.md / research.md / checklists/) are committed to the
    # coordination branch exactly like plan.md, so a stale primary copy IS coord
    # residue. The prior assertion (spec.md NOT residue) encoded a now-overturned
    # intent that blocked record-analysis on coord missions (#2084-sibling). See
    # test_coordination_residue_includes_planning_source_docs.
    assert is_coordination_artifact_residue_path(
        "kitty-specs/demo/spec.md", mission_slug="demo"
    )
    # Mission-isolation negative control (still valid): another mission's residue
    # never counts as this mission's residue.
    assert not is_coordination_artifact_residue_path(
        "kitty-specs/other/plan.md", mission_slug="demo"
    )


def test_coordination_residue_includes_planning_source_docs() -> None:
    """The planning SOURCE docs are coord-placement residue under coord topology.

    Red-first reproduction (2026-06-23): on the current incomplete residue set
    these all return False, so the record-analysis dirty-gate counts the stale
    primary copies as a dirty tree and refuses — the #2084-sibling that blocked
    the implement bootstrap of mission single-authority-topology-cleanup-01KVRJ6P.
    """
    for residue_path in (
        "kitty-specs/demo/spec.md",
        "kitty-specs/demo/data-model.md",
        "kitty-specs/demo/research.md",
        "kitty-specs/demo/checklists/requirements.md",
        "kitty-specs/demo/checklists/",
    ):
        assert is_coordination_artifact_residue_path(
            residue_path, mission_slug="demo"
        ), residue_path

    # Negative controls — genuine non-residue paths must still block:
    #  - a real source edit is never mission residue
    #  - an unknown mission file is not in the residue authority
    #  - another mission's source doc is not THIS mission's residue
    assert not is_coordination_artifact_residue_path(
        "src/specify_cli/foo.py", mission_slug="demo"
    )
    assert not is_coordination_artifact_residue_path(
        "kitty-specs/demo/notes-scratch.md", mission_slug="demo"
    )
    assert not is_coordination_artifact_residue_path(
        "kitty-specs/other/spec.md", mission_slug="demo"
    )


# --------------------------------------------------------------------------- #
# WP04 (T009) — the residue authority derives coord-routing from the STORED
# topology (#2090-clean projection), NOT a fabricated CommitTarget(.kind) shim.
# The COORD→True / coord-less→False differential is the over-allow mutation-killer.
# --------------------------------------------------------------------------- #


def test_kind_is_coordination_residue_coord_topology_is_owned() -> None:
    """A placement-kind artifact IS residue under a coord-routing topology (True cell).

    Positive cell: both coord-routing topologies (``COORD`` / ``LANES_WITH_COORD``)
    classify a placement-kind artifact's stale primary copy as coordination residue.
    """
    for topology in (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD):
        assert kind_is_coordination_residue(
            MissionArtifactKind.ISSUE_MATRIX, topology
        ), topology.value


def test_kind_is_coordination_residue_flat_topology_is_not_owned() -> None:
    """The coord-less cells are NOT residue — the over-allow mutation-killer (False cell).

    Paired negative control to the positive cell above: under the two coord-less
    topologies (``SINGLE_BRANCH`` = flat, ``LANES``) there is no primary↔coordination
    split, so NOTHING is coordination residue. A mutant that always returned True
    (the prior always-coord shim's behavior projected onto every topology) survives
    the positive cell but dies here. This is the FR-001b stored-topology projection
    pinned: the routing decision reads the topology, not a synthetic ``.kind``.
    """
    for topology in (MissionTopology.SINGLE_BRANCH, MissionTopology.LANES):
        assert not kind_is_coordination_residue(
            MissionArtifactKind.ISSUE_MATRIX, topology
        ), topology.value


def test_kind_is_coordination_residue_primary_metadata_never_residue() -> None:
    """PRIMARY_METADATA is never residue even under coord topology (kind negative control).

    The kind axis of the differential: PRIMARY_METADATA lives on the primary
    checkout (``ignores_primary_coord_residue=False``), so its stale copy is a real
    dirty-tree blocker, never coordination residue — even under ``COORD``. Pairs the
    topology negative control above with a kind negative control so neither axis can
    be silently widened.
    """
    assert not kind_is_coordination_residue(
        MissionArtifactKind.PRIMARY_METADATA, MissionTopology.COORD
    )
