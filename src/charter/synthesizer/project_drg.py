"""Project-level DRG overlay writer.

Thin composer over ``src/doctrine/drg`` primitives (KD-1 rule: no reusable
graph logic here — push any generic graph logic to ``src/doctrine/drg/``
instead).

Public API:

- ``emit_project_layer(targets, adapter_outputs, spec_kitty_version,
                       shipped_drg) -> DRGGraph``
  Builds a ``DRGGraph`` for the project-local overlay.  Raises
  ``ProjectDRGValidationError`` on additive-only violations (FR-020 / EC-6).

- ``persist(graph, staging_dir, guard)``
  Serializes the graph to ``staging_dir/doctrine/graph.yaml`` via the supplied
  ``PathGuard``.  The promote step (WP03) will ``os.replace`` this file to
  ``.kittify/doctrine/graph.yaml``.

See data-model.md §E-5 for the overlay discipline.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ruamel.yaml import YAML

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation

from .errors import ProjectDRGValidationError
from .path_guard import PathGuard
from .request import SynthesisTarget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KIND_TO_NODE_KIND: dict[str, NodeKind] = {
    "directive": NodeKind.DIRECTIVE,
    "tactic": NodeKind.TACTIC,
    "styleguide": NodeKind.STYLEGUIDE,
}


def _node_kind_for(kind: str) -> NodeKind:
    try:
        return _KIND_TO_NODE_KIND[kind]
    except KeyError:
        raise ValueError(f"Unsupported artifact kind: {kind!r}") from None


def _serialize_graph(graph: DRGGraph) -> str:
    """Return a canonical YAML string for *graph* with sorted keys."""
    # Build a plain dict with sorted keys for deterministic serialization.
    nodes_data: list[dict[str, object]] = []
    for node in graph.nodes:
        nd: dict[str, object] = {"kind": str(node.kind), "urn": node.urn}
        if node.label is not None:
            nd["label"] = node.label
        nodes_data.append(nd)

    edges_data: list[dict[str, object]] = []
    for edge in graph.edges:
        ed: dict[str, object] = {
            "relation": str(edge.relation),
            "source": edge.source,
            "target": edge.target,
        }
        if edge.when is not None:
            ed["when"] = edge.when
        if edge.reason is not None:
            ed["reason"] = edge.reason
        edges_data.append(ed)

    payload: dict[str, object] = {
        "schema_version": graph.schema_version,
        "generated_at": graph.generated_at,
        "generated_by": graph.generated_by,
        "nodes": nodes_data,
        "edges": edges_data,
    }

    yaml = YAML()
    yaml.default_flow_style = False
    buf = io.StringIO()
    yaml.dump(payload, buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_project_layer(
    targets: Sequence[SynthesisTarget],
    spec_kitty_version: str,
    shipped_drg: DRGGraph,
) -> DRGGraph:
    """Build an additive project-layer ``DRGGraph`` from *targets*.

    One node is emitted per target; edges are derived from each target's
    ``source_urns`` (direction: project node ``derived_from``/``requires``
    the source URN per existing DRG conventions).

    FR-020 / EC-6 additive-only enforcement:

    * A target whose URN is already present in ``shipped_drg.nodes`` raises
      ``ProjectDRGValidationError`` — synthesized artifacts carry *new* URNs;
      they do not shadow shipped URNs.
    * Any ``(source, target, relation)`` triple that already exists in
      ``shipped_drg.edges`` raises ``ProjectDRGValidationError`` — no
      duplicate edges allowed.

    Args:
        targets: Ordered sequence of ``SynthesisTarget`` objects to emit.
        spec_kitty_version: Version string embedded in ``generated_by``.
        shipped_drg: The shipped-layer ``DRGGraph`` used for additive-only
            checks.  **Not mutated.**

    Returns:
        A new ``DRGGraph`` representing the project overlay.  The caller
        (typically ``validation_gate.validate``) is responsible for running
        ``merge_layers`` + ``validate_graph`` before persisting.

    Raises:
        ProjectDRGValidationError: If any additive-only invariant is violated.
    """
    now_iso = datetime.now(UTC).isoformat(timespec="seconds")
    generated_by = f"spec-kitty charter synthesize {spec_kitty_version}"

    # Build indexes for additive-only checks.
    shipped_node_urns: frozenset[str] = frozenset(n.urn for n in shipped_drg.nodes)
    shipped_edge_triples: frozenset[tuple[str, str, str]] = frozenset(
        (e.source, e.target, e.relation.value) for e in shipped_drg.edges
    )

    nodes: list[DRGNode] = []
    edges: list[DRGEdge] = []
    seen_urns: set[str] = set()  # tracks overlay-internal duplicates

    for target in targets:
        urn = target.urn

        # FR-020 / EC-6: reject URNs that collide with shipped nodes.
        if urn in shipped_node_urns:
            raise ProjectDRGValidationError(
                errors=(
                    f"Additive-only violation (FR-020 / EC-6): URN '{urn}' "
                    f"already exists in the shipped DRG layer.  Synthesized "
                    f"artifacts must carry new URNs disjoint from shipped nodes.",
                ),
                merged_graph_summary=(
                    f"shipped_nodes={len(shipped_drg.nodes)}, "
                    f"colliding_urn={urn!r}"
                ),
            )

        # Overlay-internal duplicate guard.
        if urn in seen_urns:
            raise ProjectDRGValidationError(
                errors=(
                    f"Duplicate project-layer URN '{urn}': each target must "
                    f"produce a distinct URN within one synthesis run.",
                ),
                merged_graph_summary=(
                    f"colliding_urn={urn!r}"
                ),
            )
        seen_urns.add(urn)

        node = DRGNode(
            urn=urn,
            kind=_node_kind_for(target.kind),
            label=target.title,
        )
        nodes.append(node)

        # Derive edges from source_urns: project node *derived_from* (or
        # *requires* for directives) the upstream shipped/project URN.
        for source_urn in target.source_urns:
            relation = (
                Relation.REQUIRES if target.kind == "directive"
                else Relation.APPLIES
            )
            triple = (urn, source_urn, relation.value)

            # FR-020: reject edges whose triple already exists in shipped.
            if triple in shipped_edge_triples:
                raise ProjectDRGValidationError(
                    errors=(
                        f"Duplicate edge (FR-020 / EC-6): triple "
                        f"({urn!r} --{relation.value}--> {source_urn!r}) "
                        f"already exists in the shipped DRG layer.",
                    ),
                    merged_graph_summary=(
                        f"colliding_edge=({urn} --{relation.value}--> {source_urn})"
                    ),
                )

            edge = DRGEdge(
                source=urn,
                target=source_urn,
                relation=relation,
                reason=f"Derived from synthesis target {target.slug!r}",
            )
            edges.append(edge)

    return DRGGraph(
        schema_version="1.0",
        generated_at=now_iso,
        generated_by=generated_by,
        nodes=nodes,
        edges=edges,
    )


def persist(
    graph: DRGGraph,
    staging_dir: Path,
    guard: PathGuard,
) -> None:
    """Serialize *graph* to ``staging_dir/doctrine/graph.yaml`` via *guard*.

    The promote step (WP03) will atomically move this file to
    ``.kittify/doctrine/graph.yaml``.

    Args:
        graph: The project overlay ``DRGGraph`` to write.
        staging_dir: Root of the staging area (must be within the PathGuard
            allowlist).
        guard: ``PathGuard`` instance that governs all writes.
    """
    doctrine_dir = staging_dir / "doctrine"
    guard.mkdir(doctrine_dir, caller="project_drg.persist")
    graph_path = doctrine_dir / "graph.yaml"
    guard.write_text(graph_path, _serialize_graph(graph), caller="project_drg.persist")


__all__ = ["emit_project_layer", "persist"]
