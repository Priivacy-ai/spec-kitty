"""Invariance assertions for the WP04 extractor re-point (mission-step-authority).

``extract_mission_type_edges`` (``doctrine.drg.migration.extractor``) was
re-pointed from a raw ``data.get("action_sequence")`` YAML read to the WP02
projection seam (``doctrine.missions.step_projection.project_action_sequence``,
resolved builtin-only via ``MissionStepRepository``). This module pins the
three invariants that re-point must hold (T012, FR-004/FR-010):

1. **DRG 0-delta (NFR-002)** -- the regenerated graph still counts 280 nodes /
   757 edges / 10 orphans, and is byte-identical to the shipped graph
   (:func:`~doctrine.drg.loader.load_built_in_graph`).
2. **No edge for non-sequence steps** -- a step with ``in_action_sequence:
   false`` (``retrospect``, and software-dev's other 6 non-sequence steps)
   never mints a ``mission_type --requires--> action`` edge.
3. **Projection == pre-mission action_sequence** -- the projected edge set for
   every shipped mission type matches the edge set the raw YAML
   ``action_sequence`` would have produced (byte-for-byte, order preserved).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from doctrine.drg.loader import load_built_in_graph
from doctrine.drg.migration.extractor import extract_mission_type_edges, generate_graph
from doctrine.drg.models import Relation
from doctrine.missions.mission_step_repository import MissionStepRepository

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

DOCTRINE_ROOT: Path = Path(__file__).resolve().parents[4] / "src" / "doctrine"

#: Baseline DRG counts pinned by the mission-step-authority mission (NFR-002).
#: Any drift here is a defect, not an accepted change -- see WP04's Definition
#: of Done in kitty-specs/mission-step-authority-01KXNZMT/tasks/WP04-extractor-repoint.md.
_EXPECTED_NODE_COUNT = 280
_EXPECTED_EDGE_COUNT = 757
_EXPECTED_ORPHAN_COUNT = 10

#: software-dev steps that are not action-sequence members (retrospect lives
#: outside every type's step directory and is asserted separately).
_SOFTWARE_DEV_NON_SEQUENCE_STEPS = frozenset(
    {"accept", "analyze", "charter", "research", "tasks-finalize", "tasks-outline", "tasks-packages"}
)


#: The hand-pinned authored action_sequence per built-in type. Post-WP07 the
#: flat ``action_sequence`` is removed from the mission_types YAML (the step.yaml
#: projection is the sole authority), so this test compares the projected edge
#: set against this independent human-authored contract rather than a raw-YAML
#: read of a field that no longer exists.
_SHIPPED_ACTION_SEQUENCES: dict[str, list[str]] = {
    "software-dev": ["specify", "plan", "tasks", "implement", "review"],
    "documentation": ["discover", "audit", "design", "generate", "validate", "publish", "accept"],
    "research": ["scoping", "methodology", "gathering", "synthesis", "output"],
    "plan": ["specify", "research", "plan", "review"],
}


def _shipped_action_sequences() -> dict[str, list[str]]:
    """The pinned authored ``action_sequence`` per built-in type (the projected
    edge set must equal the edges these sequences imply)."""
    return dict(_SHIPPED_ACTION_SEQUENCES)


def _orphan_urns(nodes: Any, edges: Any) -> set[str]:
    """Return node URNs incident to no edge (neither source nor target)."""
    incident: set[str] = set()
    for edge in edges:
        incident.add(edge.source)
        incident.add(edge.target)
    return {node.urn for node in nodes if node.urn not in incident}


@pytest.mark.doctrine
class TestDRGZeroDelta:
    """The projection re-point leaves the shipped DRG graph unchanged (NFR-002)."""

    # Accepted red (regression): the `red-main-release-discipline` procedure
    # landed (1eb035e20) as a doctrine source without regenerating the shipped
    # DRG / bumping this zero-delta baseline (280), so the extractor now sees a
    # node the frozen baseline does not. Tracked by #2770 (open until the shipped
    # DRG is regenerated); honest red until it lands.
    @pytest.mark.regression
    def test_regenerated_graph_matches_baseline_counts(self, tmp_path: Path) -> None:
        graph = generate_graph(DOCTRINE_ROOT, tmp_path / "graph.yaml")

        assert len(graph.nodes) == _EXPECTED_NODE_COUNT  # golden-count: cardinality-is-contract
        assert len(graph.edges) == _EXPECTED_EDGE_COUNT  # golden-count: cardinality-is-contract
        orphans = _orphan_urns(graph.nodes, graph.edges)
        assert len(orphans) == _EXPECTED_ORPHAN_COUNT  # golden-count: cardinality-is-contract

    # Accepted red (regression): same root cause as
    # test_regenerated_graph_matches_baseline_counts — the red-main procedure
    # (1eb035e20) landed without regenerating the shipped DRG, so the extractor
    # and the shipped graph split-brain. Tracked by #2770 (open until the shipped
    # DRG is regenerated); honest red until it lands.
    @pytest.mark.regression
    def test_shipped_graph_is_fresh_and_byte_identical(self) -> None:
        """A fresh regeneration matches the committed shipped graph exactly."""
        shipped = load_built_in_graph()
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = generate_graph(DOCTRINE_ROOT, Path(tmp) / "graph.yaml")

        assert {n.urn for n in regenerated.nodes} == {n.urn for n in shipped.nodes}
        assert {
            (e.source, e.target, e.relation.value) for e in regenerated.edges
        } == {(e.source, e.target, e.relation.value) for e in shipped.edges}
        assert len(regenerated.nodes) == len(shipped.nodes) == _EXPECTED_NODE_COUNT
        assert len(regenerated.edges) == len(shipped.edges) == _EXPECTED_EDGE_COUNT


@pytest.mark.doctrine
class TestNonSequenceStepsMintNoEdge:
    """``in_action_sequence: false`` steps never mint a mission_type->action edge."""

    def test_software_dev_non_sequence_steps_mint_no_edge(self) -> None:
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        sw_dev_targets = {
            e.target
            for e in edges
            if e.source == "mission_type:software-dev" and e.relation is Relation.REQUIRES
        }

        steps = MissionStepRepository.default().resolve_all_for_mission_type(
            "software-dev", pack_context=None
        )
        non_sequence_step_ids = {
            step_id for step_id, step in steps.items() if not step.in_action_sequence
        }

        assert non_sequence_step_ids == _SOFTWARE_DEV_NON_SEQUENCE_STEPS
        for step_id in non_sequence_step_ids:
            assert f"action:software-dev/{step_id}" not in sw_dev_targets, (
                f"{step_id} is in_action_sequence:false but minted a requires edge"
            )

    def test_retrospect_never_appears_as_a_requires_edge_target(self) -> None:
        """``retrospect`` is not a member of any shipped type's action sequence."""
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        retrospect_targets = {
            e.target
            for e in edges
            if e.relation is Relation.REQUIRES and e.target.endswith("/retrospect")
        }
        assert not retrospect_targets


@pytest.mark.doctrine
class TestProjectedEdgeSetMatchesActionSequence:
    """Projected edges == the pre-mission ``action_sequence``-derived edges, per type."""

    def test_every_type_projected_edges_match_shipped_action_sequence(self) -> None:
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        sequences = _shipped_action_sequences()

        assert sequences, "expected at least one shipped mission type"
        for mission_id, steps in sequences.items():
            source_urn = f"mission_type:{mission_id}"
            emitted = [
                e.target
                for e in edges
                if e.source == source_urn and e.relation is Relation.REQUIRES
            ]
            expected = [f"action:{mission_id}/{step}" for step in steps]
            assert emitted == expected, (
                f"{source_urn}: projected edges {emitted} != "
                f"raw action_sequence-derived edges {expected}"
            )
