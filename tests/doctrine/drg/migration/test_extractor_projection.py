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

_REPO_ROOT: Path = Path(__file__).resolve().parents[4]
DOCTRINE_ROOT: Path = _REPO_ROOT / "src" / "doctrine"

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
#: (4) ADR 2026-07-26-2 (doctrine artefact pack layout): the PowerShell toolguide
#:     and its 245-line guide are promoted from ``toolguides/`` into the pack
#:     layer ``toolguides/built-in/``. It had sat outside ``<type>/<pack>/`` since
#:     the framework's first commit, so node discovery never saw it and the
#:     toolguide was unreachable; promotion mints one edge-less
#:     ``toolguide:powershell-syntax`` node: +1 node / +0 edges / +1 orphan.
#:     The same change handles nine mispacked artefacts: **eight are DELETED**
#:     (three byte-identical duplicates, two stale divergent copies, three
#:     content-free seed stubs) and the ninth is the promotion above -- it was
#:     moved, not deleted. The eight deletions have **zero** count impact: none
#:     of them was ever a node, which is precisely why they were dead.
#:     Composed: 304/757/31 + 1/0/1 = 305/757/32.
#:     (An earlier revision of this ledger said "DELETES nine ... five duplicates,
#:     four seed stubs". Both sub-counts were wrong -- git shows 8 deletions and
#:     3 renames -- while the numeric assertions below stayed green. NFR-006 makes
#:     this prose a contract precisely so the counts stay auditable; it is corrected
#:     here rather than quietly, because a wrong ledger is what NFR-006 forbids.)
#: (5) Mission doctrine-silence-guards-01KYFV7Q, WP09 (FR-012): a
#:     **relation-only change at constant cardinality**, and the mission's single
#:     ledgered exception to its own NFR-004 "no graph content change".
#:     ``agent_profile:doctrine-daphne --applies--> procedure:onboard-external-
#:     agent-to-pack`` is retyped to ``requires`` in ``_CURATED_ARTIFACT_EDGES``.
#:     +0 nodes / +0 edges / +0 orphans -- the counts below are deliberately
#:     UNCHANGED, which is exactly why the change is ledgered here: a cardinality
#:     baseline cannot see it, so without this entry a live traversal result would
#:     have moved with every golden count still green. What DID move is the
#:     relation histogram: ``applies`` 1 -> 0, ``requires`` 259 -> 260 (shipped
#:     graph, i.e. including the hand-authored overlay).
#:     Why: ``applies`` was that procedure's only inbound edge and no traversal
#:     follows ``applies``, so activating the profile could not reach the operating
#:     procedure it declares. Post-change ``cascade_activation_targets`` from
#:     ``agent_profile:doctrine-daphne`` reaches it -- and the activation set grows
#:     by FOUR artifacts, not one: the procedure (procedures 5 -> 6) plus its own
#:     three output templates ``decomposition-table``, ``onboarded-artifact-set``
#:     and ``source-agent-dossier`` (templates 6 -> 9). Recording only the procedure
#:     would understate the traversal move this entry exists to make visible.
#:     Orphan count is unaffected
#:     because ``_orphan_urns`` counts incidence, not relation.
#:     Guarded by ``tests/architectural/test_no_authored_applies_edge.py``.
#: (6) Landing pass for PR #3007, operator ruling 2026-07-28 (#3009 remedy 4):
#:     ``toolguide:rtk-search-tooling`` is REMOVED outright -- artefact, its
#:     245-line guide, its entry in the default charter pack's toolguide
#:     activations, and this repository's own activation. RTK will not be pushed
#:     to the userbase: it is difficult to set up correctly and can significantly
#:     affect test execution, so shipping an activated toolguide for it is a
#:     liability rather than an oversight to be wired.
#:     -1 node / +0 edges / -1 orphan. Composed: 305/757/32 - 1/0/1 = 304/757/31.
#:     It was one of the nine ``_ACTIVATED_BUT_UNREACHABLE`` entries below; the
#:     other eight are oversights and are wired rather than deleted, so this is
#:     the only member that leaves by deletion. The node carried no edges in
#:     either direction (verified: its sole graph appearance was its own node
#:     line), so nothing else in the graph moves.
#: (7) Same ruling, the other half of #3009 remedy 4: the eight remaining
#:     ``_ACTIVATED_BUT_UNREACHABLE`` artefacts are WIRED via
#:     ``_CURATED_ARTIFACT_EDGES``. The charter activated them while the graph
#:     gave them no inbound edge, so cascade reached none of them -- the same
#:     failure WP09 fixed once (entry 5), with no edge at all rather than an
#:     unfollowed relation. +0 nodes / +7 edges / -8 orphans.
#:     Seven new edges de-orphan seven targets; the EIGHTH artefact,
#:     ``directive:DIRECTIVE_035``, leaves the orphan set without an edge of its
#:     own by becoming the SOURCE of one (``_orphan_urns`` counts incidence, so a
#:     first outbound edge de-orphans just as an inbound one does). That is why
#:     the orphan delta is -8 while the edge delta is +7.
#:     Composed: 304/757/31 - 0/-7/+8 -> 304/764/23.
#:     Each edge follows an existing (source_kind -> target_kind, relation)
#:     pattern in the shipped graph; ``requires`` where the source mandates the
#:     target, ``suggests`` where it recommends. ``paradigm:atomic-design`` is
#:     deliberately NOT wired -- see ``_ACTIVATED_BUT_UNREACHABLE``.
_EXPECTED_NODE_COUNT = 304
_EXPECTED_EDGE_COUNT = 764

# ---------------------------------------------------------------------------
# Orphan MEMBERSHIP, not an orphan count
# ---------------------------------------------------------------------------
# This was ``_EXPECTED_ORPHAN_COUNT = 32`` -- a bare cardinality with the
# delta-only ledger above as its sole explanation. A count cannot distinguish
# "32 known-acceptable orphans" from "32 unexamined orphans", and they were the
# second kind: nine of them are artefacts the charter has ACTIVATED, which the
# count read as settled for as long as the number stayed at 32. Naming the
# members makes a new orphan announce itself by URN instead of nudging an
# integer, and makes the unacceptable ones impossible to file under the same
# heading as the acceptable ones.
#
# The four sets below partition the orphan set by *why* each node has no edge.
# Three are legitimate; the fourth is a tracked defect that must shrink to
# empty. Deliberately NOT redefining the metric: ``_orphan_urns`` still counts
# edge INCIDENCE, exactly as before (the stricter traversability measures in
# issue #3009 move a golden count repo-wide and are a separate mission).

#: Built-in mission step contracts. ``mission_step_contract.graph.yaml`` ships
#: ``edges: []`` by construction (ledger entry 2): a contract is resolved by the
#: ``(mission_type, action)`` join at pre-review activation, never by graph
#: traversal, so it has no edge to carry. 17 shipped = documentation 7 +
#: research 5 + software-dev 5.
_EDGELESS_BY_CONSTRUCTION: frozenset[str] = frozenset(
    {
        f"mission_step_contract:{contract}"
        for contract in (
            "documentation/accept",
            "documentation/audit",
            "documentation/design",
            "documentation/discover",
            "documentation/generate",
            "documentation/publish",
            "documentation/validate",
            "research/gathering",
            "research/methodology",
            "research/output",
            "research/scoping",
            "research/synthesis",
            "software-dev/implement",
            "software-dev/plan",
            "software-dev/review",
            "software-dev/specify",
            "software-dev/tasks",
        )
    }
)

#: Nodes a landed mission registered before anything cross-references them.
#: Each is explained by a numbered entry in the ledger above; an orphan here is
#: expected to leave the set when the follow-up mission wires it, not to sit
#: here indefinitely.
_AWAITING_REFERENCES: frozenset[str] = frozenset(
    {
        # Ledger (glossary-pack-doctrine-kind-01KY30SW): Mission A ships the
        # pack node with zero outbound refs; its enforcement fields stay inert
        # until Mission B.
        "glossary_pack:spec-kitty-core",
        # Ledger (3): the first shipped doctrine ASSET; ``asset.graph.yaml``
        # ships ``edges: []``. Wired by the hand-authored overlay -- see
        # _ORPHANS_RESOLVED_BY_OVERLAY.
        "asset:common-docs-structural-lint",
        # Ledger (4): promoted out of ``toolguides/`` into the ``built-in``
        # pack layer by ADR 2026-07-26-2, which made it a node for the first
        # time. Nothing references it yet.
        "toolguide:powershell-syntax",
        # Ledger (doctrine-tension-edges-01KY1WPC WP03): a plain built-in
        # directive whose only edges are the hand-authored
        # ``reconciles_tension`` ones the extractor cannot mint. Wired by the
        # overlay -- see _ORPHANS_RESOLVED_BY_OVERLAY.
        "directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
    }
)

#: The human operator is a participant, not a doctrine artefact anything
#: delegates to or resolves through. No traversal should ever reach it, so
#: zero incident edges is the correct shape rather than a gap.
_NOT_A_TRAVERSAL_TARGET: frozenset[str] = frozenset({"agent_profile:human-in-charge"})

#: **Tracked defect -- issue #3009. This set must only ever SHRINK.**
#: Every URN here is ACTIVATED in ``.kittify/config.yaml`` yet has no edge at
#: all, so ``charter activate --cascade`` pulls in nothing for it, deactivation
#: frees nothing, and no action's context resolution can surface it. The
#: charter says these are live doctrine; the DRG says they reach nobody.
#: ``procedure:red-main-release-discipline`` is the procedure behind charter
#: standing order #9; ``tactic:occurrence-classification-workflow`` is the
#: workflow behind DIRECTIVE_035 -- and DIRECTIVE_035 is itself on this list.
#:
#: This is the same failure WP09 fixed once for
#: ``procedure:onboard-external-agent-to-pack`` (there: an edge typed
#: ``applies``, which no traversal follows; here: no edge at all).
#:
#: Note the count: issue #3009 reports NINE. It is ten. The issue's matcher
#: compares a node's bare id against the ``activated_*`` lists, which works for
#: every kind except ``directive`` -- directive URNs are ``directive:
#: DIRECTIVE_035`` while the charter activates the file slug
#: ``035-bulk-edit-occurrence-classification``, so no directive could ever
#: match. Fixing an artefact here removes its line; nothing may be added
#: without an issue reference.
#:
#: RESOLVED 2026-07-28 (operator ruling, landing pass for PR #3007). Of the ten:
#: ``toolguide:rtk-search-tooling`` was DELETED (ledger entry 6) and eight were
#: WIRED via ``_CURATED_ARTIFACT_EDGES`` (ledger entry 7) -- seven targets plus
#: ``directive:DIRECTIVE_035``, which leaves this set by becoming an edge SOURCE
#: rather than by gaining an inbound edge. ``paradigm:atomic-design`` is the only
#: survivor: it is frontend-interface-specific and no shipped doctrine artefact is
#: a defensible source, so wiring it would mean inventing a relationship rather
#: than recording one. It stays enrolled and visible pending an operator ruling.
_ACTIVATED_BUT_UNREACHABLE: frozenset[str] = frozenset(
    {
        "paradigm:atomic-design",
    }
)

#: Every node a PURE ``generate_graph`` run leaves incident to no edge.
#: 17 + 4 + 1 + 1 = 23. The retired ``_EXPECTED_ORPHAN_COUNT`` pinned 32; the
#: difference is ledger entries (6) and (7) -- one deletion and eight wirings --
#: and is now a consequence of the membership rather than the whole contract.
_INTENTIONAL_ORPHANS: frozenset[str] = (
    _EDGELESS_BY_CONSTRUCTION
    | _AWAITING_REFERENCES
    | _NOT_A_TRAVERSAL_TARGET
    | _ACTIVATED_BUT_UNREACHABLE
)

#: The pure-extractor figure (32) and the shipped-graph figure (30) differ by
#: exactly these two, and by nothing else: the hand-authored overlay
#: (``doctrine.drg.migration.hand_authored_overlay``) carries edges the
#: extractor has no frontmatter mechanism to mint, and they land on these nodes.
#: Naming them keeps the two figures related by a stated cause instead of by two
#: independent magic numbers that could drift apart unnoticed.
_ORPHANS_RESOLVED_BY_OVERLAY: frozenset[str] = frozenset(
    {
        "asset:common-docs-structural-lint",
        "directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
    }
)

#: Orphans that survive into the graph an operator actually loads.
_SHIPPED_ORPHANS: frozenset[str] = _INTENTIONAL_ORPHANS - _ORPHANS_RESOLVED_BY_OVERLAY

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


def _describe_orphan_drift(measured: set[str], expected: frozenset[str]) -> str:
    """Render an orphan-set mismatch as the two directions a reader must act on.

    The whole point of replacing the golden count: a failure must name the node,
    and say whether something newly lost its edges or newly gained one.
    """
    appeared = sorted(measured - expected)
    resolved = sorted(expected - measured)
    lines: list[str] = []
    if appeared:
        lines.append(
            "NEW orphans -- these nodes are incident to no edge and nothing "
            "declares that acceptable:\n"
            + "\n".join(f"    + {urn}" for urn in appeared)
            + "\n  Either give the node an edge a traversal follows, or add it to "
            "the bucket that explains why it has none."
        )
    if resolved:
        lines.append(
            "NO LONGER orphans -- these are still declared as edge-less:\n"
            + "\n".join(f"    - {urn}" for urn in resolved)
            + "\n  Drop them from the declaration; if one left "
            "_ACTIVATED_BUT_UNREACHABLE, note the fix on issue #3009."
        )
    return "orphan membership drifted.\n  " + "\n  ".join(lines)


def _charter_activated_urns() -> set[str]:
    """Return every ``<kind>:<id>`` the project charter currently activates.

    Directives are the reason this needs a mapping rather than a bare id
    comparison: a directive node's URN carries its ``code``
    (``directive:DIRECTIVE_035``) while ``.kittify/config.yaml`` activates the
    file slug (``035-bulk-edit-occurrence-classification``).
    """
    import yaml

    config = yaml.safe_load((_REPO_ROOT / ".kittify" / "config.yaml").read_text())
    kind_for_key = {
        "activated_directives": "directive",
        "activated_tactics": "tactic",
        "activated_toolguides": "toolguide",
        "activated_procedures": "procedure",
        "activated_paradigms": "paradigm",
        "activated_styleguides": "styleguide",
    }
    slug_to_code: dict[str, str] = {}
    for path in (DOCTRINE_ROOT / "directives" / "built-in").glob("*.directive.yaml"):
        loaded = yaml.safe_load(path.read_text())
        code = loaded.get("id") if isinstance(loaded, dict) else None
        if code:
            slug_to_code[path.name.removesuffix(".directive.yaml")] = str(code)
    assert slug_to_code, (
        "no directive slug->id mapping was built, so every directive would "
        "silently fail to match an activation entry -- which is the exact "
        "blind spot that made issue #3009 report nine instead of ten"
    )

    urns: set[str] = set()
    for key, kind in kind_for_key.items():
        for entry in config.get(key) or []:
            identifier = str(entry)
            if kind == "directive":
                identifier = slug_to_code.get(identifier, identifier)
            urns.add(f"{kind}:{identifier}")
    return urns


@pytest.mark.doctrine
class TestDRGZeroDelta:
    """The projection re-point leaves the shipped DRG graph unchanged (NFR-002)."""

    def test_regenerated_graph_matches_baseline_counts(self, tmp_path: Path) -> None:
        graph = generate_graph(DOCTRINE_ROOT, tmp_path / "graph.yaml")

        assert len(graph.nodes) == _EXPECTED_NODE_COUNT  # golden-count: cardinality-is-contract
        assert len(graph.edges) == _EXPECTED_EDGE_COUNT  # golden-count: cardinality-is-contract

        orphans = _orphan_urns(graph.nodes, graph.edges)
        assert orphans == _INTENTIONAL_ORPHANS, _describe_orphan_drift(
            orphans, _INTENTIONAL_ORPHANS
        )

    def test_shipped_graph_orphans_are_the_pure_set_minus_the_overlay(self) -> None:
        """The two figures (pure 32, shipped 30) differ by a stated cause.

        Asserting each against its own constant would let them drift apart while
        both stayed green. Here the shipped set is *derived* from the pure set,
        so an overlay edge that stops landing reds with the node's name.
        """
        shipped = load_built_in_graph()
        orphans = _orphan_urns(shipped.nodes, shipped.edges)
        assert orphans == _SHIPPED_ORPHANS, _describe_orphan_drift(
            orphans, _SHIPPED_ORPHANS
        )

    def test_the_overlay_really_does_wire_the_nodes_it_is_credited_with(self) -> None:
        """Floor for the derivation above.

        If ``_ORPHANS_RESOLVED_BY_OVERLAY`` named a node the overlay does not
        actually wire, the subtraction would still produce a self-consistent
        pair of sets. This pins the cause, not just the arithmetic.
        """
        assert _INTENTIONAL_ORPHANS >= _ORPHANS_RESOLVED_BY_OVERLAY
        assert not (_ORPHANS_RESOLVED_BY_OVERLAY & _SHIPPED_ORPHANS)

        overlay_targets: set[str] = set()
        for edge in HAND_AUTHORED_EDGES:
            overlay_targets.add(edge.source)
            overlay_targets.add(edge.target)
        assert overlay_targets >= _ORPHANS_RESOLVED_BY_OVERLAY, (
            "these nodes are credited to the hand-authored overlay but no "
            "overlay edge touches them: "
            f"{sorted(_ORPHANS_RESOLVED_BY_OVERLAY - overlay_targets)}"
        )

    def test_the_orphan_partition_is_disjoint_and_total(self) -> None:
        """The four ``why`` sets must partition the orphan set exactly.

        Without this an entry could sit in two buckets (or in none while the
        union still matched), which would let the tracked-defect set be
        understated while every other assertion stayed green.
        """
        parts = (
            _EDGELESS_BY_CONSTRUCTION,
            _AWAITING_REFERENCES,
            _NOT_A_TRAVERSAL_TARGET,
            _ACTIVATED_BUT_UNREACHABLE,
        )
        assert sum(len(part) for part in parts) == len(_INTENTIONAL_ORPHANS), (
            "the orphan buckets overlap -- a URN is filed under two reasons"
        )

    def test_activated_but_unreachable_orphans_are_really_activated(self) -> None:
        """Floor for the tracked-defect set (#3009).

        A set that merely *claims* ten artefacts are charter-activated would
        keep this defect visible after the charter stopped activating them --
        or hide it if an entry were quietly dropped. Read the real charter
        config and compare, resolving directive URNs through their file slug
        (``directive:DIRECTIVE_035`` is activated as
        ``035-bulk-edit-occurrence-classification``), which is precisely the
        mapping issue #3009's own matcher lacks.
        """
        activated = _charter_activated_urns()
        assert activated >= _ACTIVATED_BUT_UNREACHABLE, (
            "these are filed as activated-yet-orphaned but the charter no "
            "longer activates them -- move them to another bucket: "
            f"{sorted(_ACTIVATED_BUT_UNREACHABLE - activated)}"
        )
        strays = (_INTENTIONAL_ORPHANS & activated) - _ACTIVATED_BUT_UNREACHABLE
        assert not strays, (
            "these orphans are charter-ACTIVATED but are filed under an "
            f"'acceptable' reason: {sorted(strays)}. Activating them cascades "
            "to nothing -- add them to _ACTIVATED_BUT_UNREACHABLE and #3009."
        )

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
