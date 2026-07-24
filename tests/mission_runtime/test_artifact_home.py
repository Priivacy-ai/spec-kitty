"""Artifact-home contract tests for coordination-topology mission artifacts."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    MissionTopology,
    artifact_home_for,
)
from mission_runtime.artifacts import kind_is_coordination_residue
from specify_cli.coordination.coherence import is_coord_residue_churn


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
    assert home.read_surface == "coord"
    assert home.write_surface == "coord"
    # The dead ``ignores_primary_coord_residue`` field was retired (IC-07g /
    # WP17, zero external consumers) — the real residue authority is
    # ``kind_is_coordination_residue``, asserted directly against the owner.
    assert kind_is_coordination_residue(MissionArtifactKind.ISSUE_MATRIX, MissionTopology.COORD) is True


def test_coordination_residue_path_filter_is_specific_to_coord_artifacts() -> None:
    """Only the COORD-partition artifacts are coordination residue.

    Remediated for write-surface-coherence WP01 (FR-002 / FR-004): the planning +
    identity kinds (spec / data-model / research / checklist / plan / tasks /
    lanes) were re-partitioned onto the PRIMARY ``target_branch``, so their stale
    primary copies are NO LONGER coordination residue — they live with their
    mission on primary by design. FR-003 (coord-commit-integrity) then re-homed
    ``analysis-report.md`` COORD→PRIMARY, so it too is no longer residue. The
    residue authority now matches the COORD partition only: issue-matrix, status
    events, acceptance-matrix.
    """
    assert is_coord_residue_churn(
        "kitty-specs/demo/issue-matrix.md", mission_slug="demo"
    )
    assert is_coord_residue_churn(
        "kitty-specs/demo/status.events.jsonl", mission_slug="demo"
    )
    assert is_coord_residue_churn(
        "kitty-specs/demo/acceptance-matrix.json", mission_slug="demo"
    )
    # The re-partitioned PRIMARY kinds are NOT coordination residue (the WP01
    # correctness change + the FR-003 analysis-report re-home): their home is the
    # primary surface.
    assert not is_coord_residue_churn(
        "kitty-specs/demo/analysis-report.md", mission_slug="demo"
    )
    assert not is_coord_residue_churn(
        "kitty-specs/demo/plan.md", mission_slug="demo"
    )
    assert not is_coord_residue_churn(
        "kitty-specs/demo/tasks/WP01.md", mission_slug="demo"
    )
    assert not is_coord_residue_churn(
        "kitty-specs/demo/spec.md", mission_slug="demo"
    )
    # Mission-isolation negative control (still valid): another mission's residue
    # never counts as this mission's residue.
    assert not is_coord_residue_churn(
        "kitty-specs/other/issue-matrix.md", mission_slug="demo"
    )


def test_planning_source_docs_are_not_coordination_residue() -> None:
    """The planning SOURCE + identity docs are PRIMARY, not coord residue (WP01).

    write-surface-coherence WP01 re-partitions the planning + identity kinds onto
    the primary ``target_branch`` (FR-002 / FR-004): spec / data-model / research /
    checklist / lanes resolve to the primary surface, so their stale primary copies
    are NOT coordination residue. (The downstream dirty-filter reconciliation that
    consumes this partition is WP05's confirmation, per the WP01 prompt.)
    """
    for primary_path in (
        "kitty-specs/demo/spec.md",
        "kitty-specs/demo/data-model.md",
        "kitty-specs/demo/research.md",
        "kitty-specs/demo/checklists/requirements.md",
        "kitty-specs/demo/checklists/",
        "kitty-specs/demo/tasks/",
    ):
        assert not is_coord_residue_churn(
            primary_path, mission_slug="demo"
        ), primary_path

    # Negative controls — genuine non-residue paths must still block:
    #  - a real source edit is never mission residue
    #  - an unknown mission file is not in the residue authority
    #  - another mission's coord doc is not THIS mission's residue
    assert not is_coord_residue_churn(
        "src/specify_cli/foo.py", mission_slug="demo"
    )
    assert not is_coord_residue_churn(
        "kitty-specs/demo/notes-scratch.md", mission_slug="demo"
    )
    assert not is_coord_residue_churn(
        "kitty-specs/other/issue-matrix.md", mission_slug="demo"
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
    checkout (not a ``_PLACEMENT_ARTIFACT_KINDS`` member), so its stale copy is a
    real dirty-tree blocker, never coordination residue — even under ``COORD``. Pairs the
    topology negative control above with a kind negative control so neither axis can
    be silently widened.
    """
    assert not kind_is_coordination_residue(
        MissionArtifactKind.PRIMARY_METADATA, MissionTopology.COORD
    )
