"""Enumerable registry of DRG content hand-authored directly in the shipped
``src/doctrine/*.graph.yaml`` fragments (mission doctrine-tension-edges-01KY1WPC
WP02) that the extractor cannot derive from built-in artifact frontmatter.

Why this exists
----------------

The extractor (:mod:`doctrine.drg.migration.extractor`) walks built-in
artifact YAML and mints DRG nodes/edges from their inline reference fields
(``tactic_refs``, ``references``, etc.). WP02 of this mission hand-authored
three new DRG relations (``in_tension_with``, ``reconciles_tension``,
``rejects``) plus six ``anti_pattern`` nodes directly into the graph
fragments. Per ADR 2026-07-18-1 / constraint C-005 ("edge-authored, not
field-derived"), the extractor has **no frontmatter mechanism** that could
ever mint these -- they are authored content, not migrated content, and a
pure regeneration will never reproduce them. That is by design, not drift.

Two consumers depend on this registry so a pure extractor regeneration never
silently regresses (or perpetually misreports staleness on) the hand-authored
content:

1. ``spec-kitty doctrine regenerate-graph`` (:mod:`specify_cli.cli.commands.doctrine`)
   -- both its ``--check`` freshness comparison and its write path must merge
   this overlay in, or running the command for real would overwrite
   ``src/doctrine/*.graph.yaml`` with a version that has silently dropped
   every hand-authored tension/reconciliation/rejection edge and anti-pattern
   node, and ``--check`` alone would report "stale" forever even when nothing
   is actually stale.
2. The doctrine test suite's shipped-graph freshness/equality canaries
   (``tests/doctrine/drg/migration/test_extractor.py``,
   ``test_extractor_projection.py``, ``test_path_ref_resolver.py``,
   ``tests/doctrine/drg/test_graph_sharding_equality.py``,
   ``test_sharding_silent_degrade.py``) -- each compares a pure extractor
   regeneration against the committed shipped graph and must merge this
   overlay into its "expected" side.

Any discrepancy beyond exactly this enumerated overlay is still a genuine
freshness failure. Growing this list is a deliberate, reviewed edit -- it
should only change in lockstep with a new hand-authored edge/node landing in
one of the ``*.graph.yaml`` fragments, never as a reflex "make the check
pass" change.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import assert_valid

# ---------------------------------------------------------------------------
# The six anti-pattern/smell nodes authored in src/doctrine/anti_pattern.graph.yaml
# (WP02 T009). None of these are ever an edge *source* (rejects edges terminate
# at them), so they carry no outgoing edges of their own.
# ---------------------------------------------------------------------------

HAND_AUTHORED_NODES: tuple[DRGNode, ...] = (
    DRGNode(
        urn="anti_pattern:anemic-domain-model",
        kind=NodeKind.ANTI_PATTERN,
        label="Anemic Domain Model",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:big-ball-of-mud",
        kind=NodeKind.ANTI_PATTERN,
        label="Big Ball of Mud",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:big-upfront-design",
        kind=NodeKind.ANTI_PATTERN,
        label="Big Upfront Design",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:code-is-the-documentation",
        kind=NodeKind.ANTI_PATTERN,
        label="Code Is the Documentation",
        tags=["smell"],
    ),
    DRGNode(
        urn="anti_pattern:database-driven-design",
        kind=NodeKind.ANTI_PATTERN,
        label="Database-Driven Design",
        tags=["anti-pattern"],
    ),
    DRGNode(
        urn="anti_pattern:single-diagram-architecture",
        kind=NodeKind.ANTI_PATTERN,
        label="Single-Diagram Architecture",
        tags=["smell"],
    ),
)

# ---------------------------------------------------------------------------
# The 2 in_tension_with + 3 reconciles_tension + 8 rejects edges authored in
# src/doctrine/{directive,paradigm}.graph.yaml (WP02 T007/T008/T010/T011),
# migrated from the retired contradiction-declaration field (WP03).
# Reason text copied verbatim from the committed fragments.
# ---------------------------------------------------------------------------

HAND_AUTHORED_EDGES: tuple[DRGEdge, ...] = (
    DRGEdge(
        source="directive:DIRECTIVE_024",
        target="directive:DIRECTIVE_025",
        relation=Relation.IN_TENSION_WITH,
        reason=(
            "Locality of Change bounds new work to the minimum scope the goal "
            "requires; Boy Scout Rule endorses opportunistic improvement of "
            "touched areas, which can justify expanding a change beyond that "
            "boundary. Both remain valid, co-activatable rules -- the tension "
            "is resolved per-change by keeping adjacent campsite cleaning "
            "inside the touched area while deferring genuinely broad refactors "
            "with an explicit rationale, not by retiring either rule. See "
            "directive:RECONCILE_CHANGE_SCOPE_TENSIONS."
        ),
    ),
    DRGEdge(
        source="directive:DIRECTIVE_025",
        target="tactic:change-apply-smallest-viable-diff",
        relation=Relation.IN_TENSION_WITH,
        reason=(
            "The Boy Scout Rule encourages leaving touched code better than "
            "found, which can justify changes beyond the smallest viable diff "
            "the tactic prescribes. Both remain valid, co-activatable rules -- "
            "apply smallest-viable-diff discipline for goal delivery, and fold "
            "in only the touched-area fixes Boy Scout Rule requires, deferring "
            "broader opportunistic improvement to an explicit task. See "
            "directive:RECONCILE_CHANGE_SCOPE_TENSIONS."
        ),
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="directive:DIRECTIVE_024",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="directive:DIRECTIVE_025",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
        target="tactic:change-apply-smallest-viable-diff",
        relation=Relation.RECONCILES_TENSION,
    ),
    DRGEdge(
        source="paradigm:brownfield-onboarding",
        target="anti_pattern:big-ball-of-mud",
        relation=Relation.REJECTS,
        reason=(
            "A Big Ball of Mud is the failure mode brownfield onboarding is "
            "built to interrupt. Where Big Ball of Mud lets coupling and "
            "concepts leak without investigation, brownfield onboarding "
            "insists that the leaks be mapped and named before they are "
            "either preserved or removed."
        ),
    ),
    DRGEdge(
        source="paradigm:brownfield-onboarding",
        target="anti_pattern:big-upfront-design",
        relation=Relation.REJECTS,
        reason=(
            "Big Upfront Design assumes the right structure can be derived "
            "from first principles before contact with the existing system. "
            "Brownfield onboarding inverts the priority: the existing system "
            "is the primary evidence, and design proposals must be grounded "
            "in what the codebase, its history, and its SMEs already encode."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:big-upfront-design",
        relation=Relation.REJECTS,
        reason=(
            "Big Upfront Design attempts to specify every architectural "
            "detail before implementation begins. C4 incremental detail "
            "modeling favours progressive discovery -- start with a context "
            "diagram and add lower levels only when they earn their keep."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:code-is-the-documentation",
        relation=Relation.REJECTS,
        reason=(
            "Relying solely on source code as documentation forces every "
            "stakeholder -- including non-technical sponsors -- to read code "
            "to understand system boundaries. C4 provides visual abstractions "
            "that make architecture accessible without requiring code "
            "literacy."
        ),
    ),
    DRGEdge(
        source="paradigm:c4-incremental-detail-modeling",
        target="anti_pattern:single-diagram-architecture",
        relation=Relation.REJECTS,
        reason=(
            "A single all-in-one architecture diagram conflates audiences and "
            "abstraction levels, producing a poster that nobody can review in "
            "a reasonable time. C4 explicitly separates concerns into "
            "distinct levels."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:anemic-domain-model",
        relation=Relation.REJECTS,
        reason=(
            "Anemic Domain Models strip behaviour from domain objects, "
            "reducing them to data bags with external procedural services. "
            "This defeats the purpose of a rich, expressive domain model and "
            "scatters invariant enforcement across service layers."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:big-ball-of-mud",
        relation=Relation.REJECTS,
        reason=(
            "A Big Ball of Mud architecture has no explicit context "
            "boundaries or ubiquitous language. Concepts leak across "
            "modules, coupling grows unchecked, and model integrity becomes "
            "impossible to maintain."
        ),
    ),
    DRGEdge(
        source="paradigm:domain-driven-design",
        target="anti_pattern:database-driven-design",
        relation=Relation.REJECTS,
        reason=(
            "Starting from a database schema and generating code around it "
            "inverts the DDD priority: the domain model should drive "
            "persistence, not the other way around. Schema-first thinking "
            "produces models shaped by storage constraints rather than "
            "business rules."
        ),
    ),
    # -----------------------------------------------------------------------
    # The 4 requires edges wiring the common-docs artifacts to the shipped
    # structural-lint asset (mission ship-structural-lint-as-asset). The lint
    # is now the first built-in ASSET (asset:common-docs-structural-lint); the
    # directive, styleguide, and both curation/scaffold tactics NAME it in
    # prose as the gate that enforces them. The extractor has no frontmatter
    # mechanism to mint an edge to an asset, so these are authored directly in
    # the graph fragments. REQUIRES (not suggests): activating any of these
    # artifacts pulls the shipped lint asset in as a mandatory prerequisite —
    # it is the charter-activate-cascade deployment hook that lands the lint
    # blob — and it de-orphans the asset (an un-linked asset that everything
    # references is the un-navigable state the asset kind exists to fix).
    # -----------------------------------------------------------------------
    DRGEdge(
        source="directive:DIRECTIVE_042",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "DIRECTIVE_042 names the common-docs structural lint as the live "
            "mechanical gate that enforces it; activating the directive "
            "requires the shipped lint asset to be present."
        ),
    ),
    DRGEdge(
        source="styleguide:common-docs",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs styleguide's tooling rows and quality_test name "
            "the structural lint as their enforcing gate, and its "
            "structural_lint_config: block is the policy the asset loads; "
            "activating the styleguide requires the shipped lint asset."
        ),
    ),
    DRGEdge(
        source="tactic:common-docs-curation",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs curation tactic directs the agent to run the "
            "structural lint as one of the live gates; activating the tactic "
            "requires the shipped lint asset."
        ),
    ),
    DRGEdge(
        source="tactic:common-docs-scaffold",
        target="asset:common-docs-structural-lint",
        relation=Relation.REQUIRES,
        reason=(
            "The common-docs scaffold tactic relies on the structural lint's "
            "index_completeness check to enforce section-index scaffolding; "
            "activating the tactic requires the shipped lint asset."
        ),
    ),
)


def hand_authored_node_urns() -> frozenset[str]:
    """URNs of every node that exists only because it was hand-authored."""
    return frozenset(n.urn for n in HAND_AUTHORED_NODES)


def hand_authored_edge_keys() -> frozenset[tuple[str, str, str]]:
    """``(source, target, relation)`` triples for every hand-authored edge."""
    return frozenset((e.source, e.target, e.relation.value) for e in HAND_AUTHORED_EDGES)


def merge_hand_authored_overlay(graph: DRGGraph) -> DRGGraph:
    """Return a new graph = *graph* plus the enumerated hand-authored overlay.

    Re-sorts nodes/edges identically to ``generate_graph``'s own canonical
    ordering (nodes by URN; edges by ``(source, target, relation)``) and
    re-validates the result, so the returned graph is exactly what a
    "pure extraction + the known hand-authored additions" reference should
    look like.
    """
    nodes_by_urn: dict[str, DRGNode] = {n.urn: n for n in graph.nodes}
    for node in HAND_AUTHORED_NODES:
        nodes_by_urn[node.urn] = node

    edges_by_triple: dict[tuple[str, str, str], DRGEdge] = {
        (e.source, e.target, e.relation.value): e for e in graph.edges
    }
    for edge in HAND_AUTHORED_EDGES:
        edges_by_triple[(edge.source, edge.target, edge.relation.value)] = edge

    merged = DRGGraph(
        schema_version=graph.schema_version,
        generated_at=graph.generated_at,
        generated_by=graph.generated_by,
        nodes=sorted(nodes_by_urn.values(), key=lambda n: n.urn),
        edges=sorted(
            edges_by_triple.values(),
            key=lambda e: (e.source, e.target, e.relation.value),
        ),
    )
    assert_valid(merged)
    return merged


def generate_reference_graph_with_overlay(doctrine_root: Path) -> DRGGraph:
    """The in-memory freshness/equality reference: pure extraction + overlay.

    Regenerates *doctrine_root* into a throw-away scratch directory (never
    read back), then merges in :data:`HAND_AUTHORED_NODES` /
    :data:`HAND_AUTHORED_EDGES`. This is the non-vacuous reference every
    shipped-graph comparison should use now that the extractor is no longer
    the sole source of shipped content (WP02/WP03).
    """
    from doctrine.drg.migration.extractor import generate_graph

    with tempfile.TemporaryDirectory() as scratch:
        pure = generate_graph(doctrine_root, Path(scratch) / "graph.yaml")
    return merge_hand_authored_overlay(pure)


def write_reference_graph_with_overlay(doctrine_root: Path, output_path: Path) -> DRGGraph:
    """Like :func:`generate_reference_graph_with_overlay`, but also writes the
    merged reference as per-kind fragments beside *output_path* (via the
    extractor's own canonical writer), so it is byte-comparable against the
    committed shipped graph.
    """
    from doctrine.drg.migration.extractor import _write_graph_yaml

    merged = generate_reference_graph_with_overlay(doctrine_root)
    _write_graph_yaml(merged, output_path)
    return merged
