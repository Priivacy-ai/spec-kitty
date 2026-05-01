"""Graph-level validation beyond what Pydantic field validators catch.

Checks:
- Dangling edge references (source/target not in node URNs)
- Duplicate edges (same source + target + relation triple)
- Cycles in the ``requires`` subgraph (DFS-based)
"""

from __future__ import annotations

from collections import defaultdict

from doctrine.drg.models import DRGGraph, Relation


class DRGValidationError(Exception):
    """Raised by :func:`assert_valid` when graph integrity checks fail."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s): {'; '.join(errors)}")


def validate_graph(graph: DRGGraph) -> list[str]:
    """Return a list of error messages (empty means valid).

    Checks performed:
    1. Dangling references -- every edge source/target must exist in nodes.
    2. Duplicate edges -- ``(source, target, relation)`` must be unique.
    3. Cycles in ``requires`` edges -- the requires subgraph must be a DAG.
    """
    errors: list[str] = []
    urns = graph.node_urns()

    # -- 1. Dangling references ---------------------------------------------
    for edge in graph.edges:
        if edge.source not in urns:
            errors.append(f"Dangling source: edge ({edge.source} --{edge.relation}--> {edge.target}) references non-existent node {edge.source!r}")
        if edge.target not in urns:
            errors.append(f"Dangling target: edge ({edge.source} --{edge.relation}--> {edge.target}) references non-existent node {edge.target!r}")

    # -- 2. Duplicate edges --------------------------------------------------
    seen_triples: set[tuple[str, str, str]] = set()
    for edge in graph.edges:
        triple = (edge.source, edge.target, edge.relation.value)
        if triple in seen_triples:
            errors.append(f"Duplicate edge: ({edge.source} --{edge.relation}--> {edge.target})")
        seen_triples.add(triple)

    # -- 3. Cycles in requires subgraph (DFS) --------------------------------
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
                errors.append(f"Cycle in requires: {' -> '.join(cycle)}")
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


def assert_valid(graph: DRGGraph) -> None:
    """Raise :class:`DRGValidationError` if the graph has integrity errors."""
    errors = validate_graph(graph)
    if errors:
        raise DRGValidationError(errors)
