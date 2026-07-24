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

from pathlib import Path
from typing import Any

import pytest

from doctrine.drg.loader import load_built_in_graph
from doctrine.drg.migration.extractor import extract_mission_type_edges, generate_graph
from doctrine.drg.migration.hand_authored_overlay import (
    HAND_AUTHORED_EDGES,
    HAND_AUTHORED_NODES,
    generate_reference_graph_with_overlay,
)
from doctrine.drg.models import Relation
from doctrine.missions.mission_step_repository import MissionStepRepository

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

DOCTRINE_ROOT: Path = Path(__file__).resolve().parents[4] / "src" / "doctrine"

#: Baseline DRG counts pinned by the mission-step-authority mission (NFR-002).
#: Any drift here is a defect, not an accepted change -- see WP04's Definition
#: of Done in kitty-specs/mission-step-authority-01KXNZMT/tasks/WP04-extractor-repoint.md.
#: WP06 (mission-step-creatability-01KXQA6R, S-C / #2724) grafts the
#: mission_type->step->template chain into the shipped graph: 8 mission-qualified
#: template nodes (software-dev 2 + documentation/research/plan x {spec,plan})
#: and 8 matching action->template ``instantiates`` edges (N=8, computed from
#: the authored ``iter_template_refs`` refs, not hand-picked). Every new
#: template node gets an ``instantiates`` in-edge (S-C adds 0 orphans).
#: Re-baselined after rebase onto upstream/main: the base advanced by +1 node
#: / +1 orphan -- ``procedure:red-main-release-discipline`` was present in the
#: upstream doctrine source but missing from upstream's shipped graph (a
#: pre-existing upstream freshness drift this regeneration incidentally fixes).
#: So the counts are (upstream-source-truth 281/757/11) + S-C's intentional
#: +8/+8/+0 = 289/765/11.
#:
#: Re-baselined for WP03 of doctrine-tension-edges-01KY1WPC: retiring the
#: contradiction-declaration field removes the 6 phantom paradigm/tactic-kind
#: nodes and 10 mis-minted ``replaces`` edges the field used to produce (2
#: directive<->directive + 8 paradigm->{paradigm,tactic}), and the new
#: ``reconcile-change-scope-tensions`` directive (a plain built-in directive
#: with no ordinary ``tactic_refs``/``references``) adds one orphan of its own
#: in a PURE regeneration -- its only edges are the hand-authored
#: ``reconciles_tension`` edges the extractor cannot mint (see
#: ``doctrine.drg.migration.hand_authored_overlay``). So a bare
#: ``generate_graph`` run yields 289 - 6 + 1 = 284 nodes,
#: 765 - 10 = 755 edges, 11 - 1 + 2 = 12 orphans.
#:
#: Mission glossary-pack-doctrine-kind-01KY30SW (WP03) then adds the built-in
#: ``spec-kitty-core`` glossary pack's own source node
#: (``glossary_pack:spec-kitty-core``, emitted by the
#: ``_emit_glossary_pack_nodes`` block in ``extract_artifact_edges``). Mission
#: A ships zero outbound references for the pack (enforcement fields are inert
#: until Mission B), so this is +1 node / +0 edges / +1 orphan (the new node
#: has no edges yet, same shape as any freshly-registered kind with no
#: cross-references). Both changes compose over the same base:
#: 284/755/12 + 1/0/1 = 285/755/13 (verified by regenerating the DRG against
#: the current base -- see the base-divergence reconciliation).
#:
#: Two independent changes compose over the same 285/755/13 base:
#: (1) upstream's ``git-worktree-pr-workflow`` toolguide (agent-knowledge-
#:     canonical-homes) adds +1 node / +2 edges / +0 orphans -- its two
#:     ``suggests`` refs (``clean-linear-commit-history``,
#:     ``pr-agent-worktree-isolation``) are ordinary outbound edges and both
#:     targets already had edges: 285/755/13 + 1/2/0 = 286/757/13.
#: (2) Mission doctrine-controlled-transition-gates (epic #2535 half A, WP09)
#:     teaches the extractor to mint one ``mission_step_contract:<mission>/<action>``
#:     node per built-in step contract (``missions/built_in_step_contracts/
#:     *.step-contract.yaml``) so the pre-review activation join resolves ACTIVE.
#:     17 shipped contracts (documentation x7 + research x5 + software-dev x5),
#:     each edge-less (the MSC fragment ships ``edges: []``): +17 nodes / +0 edges
#:     / +17 orphans.
#: Composed: 285/755/13 + 1/2/0 + 17/0/17 = 303/757/30.
#: (3) Mission ship-structural-lint-as-asset: the common-docs structural lint is
#:     relocated into ``assets/built-in`` as the first shipped doctrine ASSET,
#:     so the extractor mints one edge-less ``asset:common-docs-structural-lint``
#:     node (the asset fragment ships ``edges: []``): +1 node / +0 edges /
#:     +1 orphan. Composed: 303/757/30 + 1/0/1 = 304/757/31.
_EXPECTED_NODE_COUNT = 304
_EXPECTED_EDGE_COUNT = 757
_EXPECTED_ORPHAN_COUNT = 31

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

    def test_regenerated_graph_matches_baseline_counts(self, tmp_path: Path) -> None:
        graph = generate_graph(DOCTRINE_ROOT, tmp_path / "graph.yaml")

        assert len(graph.nodes) == _EXPECTED_NODE_COUNT  # golden-count: cardinality-is-contract
        assert len(graph.edges) == _EXPECTED_EDGE_COUNT  # golden-count: cardinality-is-contract
        orphans = _orphan_urns(graph.nodes, graph.edges)
        assert len(orphans) == _EXPECTED_ORPHAN_COUNT  # golden-count: cardinality-is-contract

    def test_shipped_graph_is_fresh_and_byte_identical(self) -> None:
        """A fresh regeneration + the hand-authored overlay matches the shipped graph.

        Post-WP03 (doctrine-tension-edges-01KY1WPC): the shipped graph also
        carries hand-authored ``in_tension_with``/``reconciles_tension``/
        ``rejects`` edges and ``anti_pattern`` nodes the extractor has no
        frontmatter mechanism to mint (C-005). The reference is therefore
        "pure regeneration + the enumerable overlay", not a bare regeneration.
        """
        shipped = load_built_in_graph()
        regenerated = generate_reference_graph_with_overlay(DOCTRINE_ROOT)

        assert {n.urn for n in regenerated.nodes} == {n.urn for n in shipped.nodes}
        assert {
            (e.source, e.target, e.relation.value) for e in regenerated.edges
        } == {(e.source, e.target, e.relation.value) for e in shipped.edges}
        assert len(regenerated.nodes) == len(shipped.nodes) == _EXPECTED_NODE_COUNT + len(
            HAND_AUTHORED_NODES
        )
        assert len(regenerated.edges) == len(shipped.edges) == _EXPECTED_EDGE_COUNT + len(
            HAND_AUTHORED_EDGES
        )


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
