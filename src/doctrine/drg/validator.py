"""Graph-level validation beyond what Pydantic field validators catch.

Checks:
- Dangling edge references (source/target not in node URNs)
- Duplicate edges (same source + target + relation triple)
- Cycles in the ``requires`` subgraph (DFS-based)
- Symmetric profile-edge integrity (lineage/delegation edges, #1755)
"""

from __future__ import annotations

from collections import defaultdict

from doctrine.drg.models import DRGGraph, NodeKind, Relation

#: Relations whose *both* endpoints must be ``agent_profile`` nodes. Lineage
#: (``specializes_from``) and runtime delegation (``delegates_to``) are the two
#: profile-to-profile relations; an edge of either kind that touches a
#: non-profile node (or a missing node) is a structural defect regardless of
#: which endpoint declared it (#1755 — the former asymmetric blind spot).
_PROFILE_EDGE_RELATIONS: frozenset[Relation] = frozenset(
    {Relation.SPECIALIZES_FROM, Relation.DELEGATES_TO}
)


class DRGValidationError(Exception):
    """Raised by :func:`assert_valid` when graph integrity checks fail."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s): {'; '.join(errors)}")


def validate_profile_edges(graph: DRGGraph) -> list[str]:
    """Validate profile-to-profile edges symmetrically (#1755).

    Lineage (``specializes_from``) and delegation (``delegates_to``) edges are
    profile-to-profile relations. Historically only the *outgoing* direction
    was exercised at resolution time (``edges_from`` on the declaring child),
    so a malformed edge declared *at* a profile but pointing at a non-profile
    target -- or a lineage cycle -- could slip through unnoticed. This check
    scans both directions so the defect is detected irrespective of which
    endpoint authored the edge:

    1. **Endpoint-kind integrity** -- both ``source`` and ``target`` of a
       profile edge must resolve to ``agent_profile`` nodes. Each endpoint is
       inspected independently (the symmetric part): a profile-edge whose
       *target* is a tactic is just as invalid as one whose *source* is.
    2. **Lineage acyclicity** -- the ``specializes_from`` subgraph must be a
       DAG. ``requires`` cycles are caught elsewhere; lineage needs its own
       check because the relation differs and a profile chain that loops back
       on itself would otherwise wedge ancestor resolution.

    Dangling references are reported by :func:`validate_graph`; this function
    only classifies endpoints it can resolve so the two checks never
    double-report the same missing-node defect.

    Returns a list of human-readable error messages (empty means valid).
    """
    errors: list[str] = []
    kind_by_urn = {n.urn: n.kind for n in graph.nodes}

    # -- 1. Endpoint-kind integrity (symmetric: inspect both endpoints) ------
    for edge in graph.edges:
        if edge.relation not in _PROFILE_EDGE_RELATIONS:
            continue
        for endpoint_name, urn in (("source", edge.source), ("target", edge.target)):
            kind = kind_by_urn.get(urn)
            if kind is None:
                continue  # missing node -> reported as dangling by validate_graph
            if kind is not NodeKind.AGENT_PROFILE:
                errors.append(
                    f"Profile-edge {endpoint_name} must be an agent_profile: "
                    f"edge ({edge.source} --{edge.relation.value}--> {edge.target}) "
                    f"has {endpoint_name} {urn!r} of kind {kind.value!r}"
                )

    # -- 2. Lineage acyclicity (specializes_from must be a DAG) --------------
    lineage_adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.relation == Relation.SPECIALIZES_FROM:
            lineage_adj[edge.source].append(edge.target)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)

    def _dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in lineage_adj.get(node, []):
            if color[neighbor] == GRAY:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                errors.append(
                    f"Cycle in specializes_from lineage: {' -> '.join(cycle)}"
                )
            elif color[neighbor] == WHITE:
                _dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    lineage_nodes = set(lineage_adj.keys())
    for targets in lineage_adj.values():
        lineage_nodes.update(targets)
    for node in sorted(lineage_nodes):
        if color[node] == WHITE:
            _dfs(node, [])

    return errors


def _validate_dangling_references(graph: DRGGraph) -> list[str]:
    """Return errors for edges whose source/target is not a known node."""
    errors: list[str] = []
    urns = graph.node_urns()
    for edge in graph.edges:
        if edge.source not in urns:
            errors.append(
                f"Dangling source: edge ({edge.source} --{edge.relation}--> "
                f"{edge.target}) references non-existent node {edge.source!r}"
            )
        if edge.target not in urns:
            errors.append(
                f"Dangling target: edge ({edge.source} --{edge.relation}--> "
                f"{edge.target}) references non-existent node {edge.target!r}"
            )
    return errors


def _validate_duplicate_edges(graph: DRGGraph) -> list[str]:
    """Return errors for repeated ``(source, target, relation)`` triples."""
    errors: list[str] = []
    seen_triples: set[tuple[str, str, str]] = set()
    for edge in graph.edges:
        triple = (edge.source, edge.target, edge.relation.value)
        if triple in seen_triples:
            errors.append(
                f"Duplicate edge: ({edge.source} --{edge.relation}--> "
                f"{edge.target})"
            )
        seen_triples.add(triple)
    return errors


def _validate_requires_cycles(graph: DRGGraph) -> list[str]:
    """Return errors for cycles in the ``requires`` subgraph (DFS)."""
    errors: list[str] = []
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.relation == Relation.REQUIRES:
            adj[edge.source].append(edge.target)

    # Standard DFS cycle detection with WHITE/GRAY/BLACK coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)  # default WHITE

    def _dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in adj.get(node, []):
            if color[neighbor] == GRAY:
                # Found a back edge -- extract the cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                errors.append(
                    f"Cycle in requires: {' -> '.join(cycle)}"
                )
            elif color[neighbor] == WHITE:
                _dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    # Visit all nodes that participate in requires edges
    all_requires_nodes = set(adj.keys())
    for targets in adj.values():
        all_requires_nodes.update(targets)

    for node in sorted(all_requires_nodes):
        if color[node] == WHITE:
            _dfs(node, [])
    return errors


def validate_graph(graph: DRGGraph) -> list[str]:
    """Return a list of error messages (empty means valid).

    Checks performed:
    1. Dangling references -- every edge source/target must exist in nodes.
    2. Duplicate edges -- ``(source, target, relation)`` must be unique.
    3. Cycles in ``requires`` edges -- the requires subgraph must be a DAG.
    4. Symmetric profile-edge integrity -- lineage/delegation edges connect
       agent_profile nodes in both directions and lineage is acyclic (#1755).
    """
    errors: list[str] = []
    errors.extend(_validate_dangling_references(graph))
    errors.extend(_validate_duplicate_edges(graph))
    errors.extend(_validate_requires_cycles(graph))
    # -- 4. Symmetric profile-edge integrity (#1755) ------------------------
    errors.extend(validate_profile_edges(graph))
    return errors


def assert_valid(graph: DRGGraph) -> None:
    """Raise :class:`DRGValidationError` if the graph has integrity errors."""
    errors = validate_graph(graph)
    if errors:
        raise DRGValidationError(errors)
