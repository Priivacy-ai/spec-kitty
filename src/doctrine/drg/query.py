"""DRG graph query primitives -- pure graph traversal, no charter semantics.

Provides :func:`walk_edges` for generic BFS edge traversal,
:func:`resolve_context` for the multi-step action context resolution
algorithm, and :func:`resolve_transitive_refs` as a bucketed wrapper
over :func:`walk_edges` for the charter resolver/compiler cutover.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from doctrine.drg.models import DRGGraph, NodeKind, Relation


@dataclass(frozen=True)
class ResolvedContext:
    """Result of resolving governance context from the DRG.

    Attributes:
        artifact_urns: All resolved artifact URNs (directives, tactics,
            styleguides, toolguides, etc.) reachable from the action node.
        glossary_scopes: Glossary scope URNs reachable via ``vocabulary``
            edges from the resolved artifacts.
    """

    artifact_urns: frozenset[str]
    glossary_scopes: frozenset[str]


def walk_edges(
    graph: DRGGraph,
    start_urns: set[str],
    relations: set[Relation],
    max_depth: int | None = None,
) -> set[str]:
    """BFS traversal following only edges matching *relations*.

    Args:
        graph: The DRG graph to walk.
        start_urns: Seed URNs to start from.
        relations: Only follow edges whose relation is in this set.
        max_depth: Maximum number of hops from any start node.
            ``None`` means walk until exhausted (transitive closure).

    Returns:
        Set of all visited node URNs (including start nodes that exist
        in the graph).
    """
    if not start_urns:
        return set()

    # Pre-compute adjacency for the requested relations
    adj: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.relation in relations:
            adj.setdefault(edge.source, []).append(edge.target)

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    for urn in start_urns:
        visited.add(urn)
        queue.append((urn, 0))

    while queue:
        current, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))

    return visited


def resolve_context(
    graph: DRGGraph,
    action_urn: str,
    depth: int = 2,
) -> ResolvedContext:
    """Resolve governance context for an action by walking the DRG.

    The algorithm:

    1. **Scope** -- walk ``scope`` edges from *action_urn* (depth 1) to
       find directly scoped artifacts.
    2. **Requires** -- walk ``requires`` edges from scoped artifacts
       transitively (no depth limit) to find hard dependencies.
    3. **Suggests** -- walk ``suggests`` edges from scoped artifacts up
       to *depth* hops to find soft recommendations.
    4. **Vocabulary** -- walk ``vocabulary`` edges from all resolved nodes
       (depth 1) to find glossary scopes.

    Args:
        graph: Merged DRG graph.
        action_urn: URN of the action node (e.g.
            ``"action:software-dev/implement"``).
        depth: Maximum hops for ``suggests`` edges. Also controls
            extended artifact inclusion.

    Returns:
        :class:`ResolvedContext` with artifact and glossary URNs.
    """
    # Step 1: scope edges (depth 1) from action node
    scoped = walk_edges(graph, {action_urn}, {Relation.SCOPE}, max_depth=1)
    # Remove the action node itself -- we only want the scoped artifacts
    scoped_artifacts = scoped - {action_urn}

    # Step 2: requires edges transitively from scoped artifacts
    required = walk_edges(graph, scoped_artifacts, {Relation.REQUIRES}, max_depth=None)

    # Step 3: suggests edges from scoped artifacts to depth hops
    suggested = walk_edges(graph, scoped_artifacts, {Relation.SUGGESTS}, max_depth=depth)

    # Combine all artifact URNs
    all_artifacts = scoped_artifacts | required | suggested

    # Step 4: vocabulary edges (depth 1) from all resolved nodes
    vocab_walk = walk_edges(graph, all_artifacts, {Relation.VOCABULARY}, max_depth=1)
    glossary_scopes = vocab_walk - all_artifacts

    return ResolvedContext(
        artifact_urns=frozenset(all_artifacts),
        glossary_scopes=frozenset(glossary_scopes),
    )


@dataclass(frozen=True)
class ResolveTransitiveRefsResult:
    """Transitive closure of doctrine artifacts reachable from a set of starting URNs,
    bucketed by :class:`NodeKind`.

    Field values are bare IDs (URN without the ``"<kind>:"`` prefix), preserving the
    legacy-compatible field shape for callers during the
    Phase 1 cutover (see WP03 in
    ``kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/``).

    Each per-kind list is returned sorted lexicographically so that downstream
    rendering is deterministic.
    """

    directives: list[str] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    paradigms: list[str] = field(default_factory=list)
    styleguides: list[str] = field(default_factory=list)
    toolguides: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    agent_profiles: list[str] = field(default_factory=list)
    # Edges whose target URN was not found in the graph, stored as
    # ``(source_urn, target_urn)``. Always ``[]`` when the input graph has
    # passed :func:`doctrine.drg.validator.assert_valid`, since the validator
    # rejects dangling targets at load time.
    unresolved: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """``True`` when all referenced artifacts were resolved (legacy-symmetric)."""
        return len(self.unresolved) == 0


def resolve_transitive_refs(
    graph: DRGGraph,
    *,
    start_urns: set[str],
    relations: set[Relation],
    max_depth: int | None = None,
) -> ResolveTransitiveRefsResult:
    """Walk ``relations`` edges from ``start_urns``, bucketing reachable nodes by kind.

    Thin wrapper over :func:`walk_edges` that groups the flat result set by
    :class:`NodeKind` and strips the URN prefix from each per-kind list.
    Designed as a behavior-equivalent replacement for the legacy charter
    transitive resolver during the Phase 1 cutover
    (``kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6``).

    Args:
        graph: The DRG graph to walk. The graph MUST already have passed
            :func:`doctrine.drg.validator.assert_valid`; this function does
            not re-validate.
        start_urns: Seed URNs (e.g. ``"directive:001-architectural-integrity-standard"``).
            Start URNs whose node is absent from ``graph`` are recorded in
            ``unresolved`` rather than raising.
        relations: Set of :class:`Relation` values to follow. For legacy
            parity with the charter resolver/compiler, callers pass
            ``{Relation.REQUIRES, Relation.SUGGESTS}``.
        max_depth: Forwarded to :func:`walk_edges`. ``None`` means transitive
            closure.

    Returns:
        :class:`ResolveTransitiveRefsResult` with per-kind bucketed bare IDs.
        Each per-kind list is sorted lexicographically.

    Raises:
        Nothing. ``requires`` cycles are rejected at load time by
        :func:`assert_valid`; cycles in other relation kinds are benign
        under BFS-with-visited-set inside :func:`walk_edges`.
    """
    visited_urns = walk_edges(
        graph,
        start_urns=start_urns,
        relations=relations,
        max_depth=max_depth,
    )

    buckets: dict[NodeKind, list[str]] = {k: [] for k in NodeKind}
    unresolved: list[tuple[str, str]] = []

    for urn in visited_urns:
        node = graph.get_node(urn)
        if node is None:
            # Defensive: assert_valid should prevent dangling URNs in a
            # validated graph. If one slips through (including an unknown
            # start URN), record it with itself as both source and target.
            unresolved.append((urn, urn))
            continue
        # Strip "<kind>:" prefix from the URN when writing into the bucket.
        bare_id = urn.split(":", 1)[1] if ":" in urn else urn
        buckets[node.kind].append(bare_id)

    for kind in NodeKind:
        buckets[kind].sort()
    unresolved.sort()

    return ResolveTransitiveRefsResult(
        directives=buckets[NodeKind.DIRECTIVE],
        tactics=buckets[NodeKind.TACTIC],
        paradigms=buckets[NodeKind.PARADIGM],
        styleguides=buckets[NodeKind.STYLEGUIDE],
        toolguides=buckets[NodeKind.TOOLGUIDE],
        procedures=buckets[NodeKind.PROCEDURE],
        agent_profiles=buckets[NodeKind.AGENT_PROFILE],
        unresolved=unresolved,
    )
