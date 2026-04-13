"""Extract inline reference fields from shipped doctrine into DRG nodes + edges.

Public API:
    extract_artifact_edges(doctrine_root) -> (nodes, edges)
    extract_action_edges(doctrine_root)   -> (nodes, edges)
    generate_graph(doctrine_root, output_path) -> DRGGraph
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from doctrine.drg.migration.calibrator import calibrate_surfaces
from doctrine.drg.migration.id_normalizer import artifact_to_urn
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import assert_valid


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_yaml = YAML(typ="safe")

_KIND_MAP: dict[str, NodeKind] = {
    "directive": NodeKind.DIRECTIVE,
    "tactic": NodeKind.TACTIC,
    "paradigm": NodeKind.PARADIGM,
    "styleguide": NodeKind.STYLEGUIDE,
    "toolguide": NodeKind.TOOLGUIDE,
    "procedure": NodeKind.PROCEDURE,
    "agent_profile": NodeKind.AGENT_PROFILE,
    "action": NodeKind.ACTION,
}

# Reference types that are NOT DRG node kinds (skipped during extraction).
_SKIP_REF_TYPES: frozenset[str] = frozenset({"template"})


def _ensure_node(
    nodes_by_urn: dict[str, DRGNode],
    urn: str,
    kind: NodeKind,
    label: str | None = None,
) -> None:
    """Register a node if not already tracked."""
    if urn not in nodes_by_urn:
        nodes_by_urn[urn] = DRGNode(urn=urn, kind=kind, label=label)
    elif label and nodes_by_urn[urn].label is None:
        nodes_by_urn[urn] = nodes_by_urn[urn].model_copy(update={"label": label})


def _load_yaml(path: Path) -> dict[str, Any] | None:
    data: Any = _yaml.load(path)
    if isinstance(data, dict):
        return data
    return None


def _relation_for_ref_type(ref_type: str) -> Relation:
    """Map a reference ``type`` field to a DRG relation.

    Directives get ``requires``; most others get ``suggests``.
    """
    if ref_type == "directive":
        return Relation.REQUIRES
    return Relation.SUGGESTS


def _kind_for_type(ref_type: str) -> NodeKind | None:
    """Map a reference ``type`` string to a NodeKind, or ``None`` if skipped."""
    if ref_type in _SKIP_REF_TYPES:
        return None
    return _KIND_MAP.get(ref_type)


# ---------------------------------------------------------------------------
# T012: Artifact walker (directives, tactics, paradigms)
# ---------------------------------------------------------------------------


def extract_artifact_edges(
    doctrine_root: Path,
) -> tuple[list[DRGNode], list[DRGEdge]]:
    """Walk shipped directives, tactics, and paradigms; return (nodes, edges).

    Every inline reference field is converted to a typed DRG edge.
    Nodes are deduplicated by URN.
    """
    nodes_by_urn: dict[str, DRGNode] = {}
    edges: list[DRGEdge] = []
    seen_triples: set[tuple[str, str, str]] = set()

    def _add_edge(edge: DRGEdge) -> None:
        triple = (edge.source, edge.target, edge.relation.value)
        if triple not in seen_triples:
            seen_triples.add(triple)
            edges.append(edge)

    # --- Directives ---
    directives_dir = doctrine_root / "directives" / "shipped"
    if directives_dir.is_dir():
        for path in sorted(directives_dir.glob("*.directive.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            directive_id: str = data.get("id", "")
            title: str = data.get("title", "")
            src_urn = artifact_to_urn("directive", directive_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.DIRECTIVE, title)

            # tactic_refs
            for tactic_id in data.get("tactic_refs", []) or []:
                tgt_urn = artifact_to_urn("tactic", tactic_id)
                _ensure_node(nodes_by_urn, tgt_urn, NodeKind.TACTIC)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.REQUIRES,
                    )
                )

            # references (top-level list of {type, id, when?})
            for ref in data.get("references", []) or []:
                ref_type: str = ref.get("type", "")
                ref_id: str = ref.get("id", "")
                if not ref_type or not ref_id:
                    continue
                tgt_kind = _kind_for_type(ref_type)
                if tgt_kind is None:
                    continue  # skip non-DRG types (e.g. template)
                tgt_urn = artifact_to_urn(ref_type, ref_id)
                _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=_relation_for_ref_type(ref_type),
                        when=ref.get("when"),
                    )
                )

            # opposed_by
            for opp in data.get("opposed_by", []) or []:
                opp_type: str = opp.get("type", "")
                opp_id: str = opp.get("id", "")
                if not opp_type or not opp_id:
                    continue
                opp_kind = _kind_for_type(opp_type)
                if opp_kind is None:
                    continue
                tgt_urn = artifact_to_urn(opp_type, opp_id)
                _ensure_node(nodes_by_urn, tgt_urn, opp_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.REPLACES,
                        reason=opp.get("reason"),
                    )
                )

    # --- Tactics ---
    tactics_dir = doctrine_root / "tactics" / "shipped"
    if tactics_dir.is_dir():
        # Include top-level *.tactic.yaml and any in subdirectories
        tactic_files = sorted(tactics_dir.rglob("*.tactic.yaml"))
        for path in tactic_files:
            data = _load_yaml(path)
            if data is None:
                continue
            tactic_id = data.get("id", "")
            tactic_name: str = data.get("name", "")
            src_urn = artifact_to_urn("tactic", tactic_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.TACTIC, tactic_name)

            # top-level references
            for ref in data.get("references", []) or []:
                ref_type = ref.get("type", "")
                ref_id = ref.get("id", "")
                if not ref_type or not ref_id:
                    continue
                tgt_kind = _kind_for_type(ref_type)
                if tgt_kind is None:
                    continue
                tgt_urn = artifact_to_urn(ref_type, ref_id)
                _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.SUGGESTS,
                        when=ref.get("when"),
                    )
                )

            # step-level references
            for step in data.get("steps", []) or []:
                for ref in step.get("references", []) or []:
                    ref_type = ref.get("type", "")
                    ref_id = ref.get("id", "")
                    if not ref_type or not ref_id:
                        continue
                    tgt_kind = _kind_for_type(ref_type)
                    if tgt_kind is None:
                        continue
                    tgt_urn = artifact_to_urn(ref_type, ref_id)
                    _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
                    _add_edge(
                        DRGEdge(
                            source=src_urn,
                            target=tgt_urn,
                            relation=Relation.SUGGESTS,
                            when=ref.get("when"),
                        )
                    )

    # --- Paradigms ---
    paradigms_dir = doctrine_root / "paradigms" / "shipped"
    if paradigms_dir.is_dir():
        for path in sorted(paradigms_dir.glob("*.paradigm.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            paradigm_id: str = data.get("id", "")
            paradigm_name: str = data.get("name", "")
            src_urn = artifact_to_urn("paradigm", paradigm_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.PARADIGM, paradigm_name)

            # tactic_refs
            for tactic_id in data.get("tactic_refs", []) or []:
                tgt_urn = artifact_to_urn("tactic", tactic_id)
                _ensure_node(nodes_by_urn, tgt_urn, NodeKind.TACTIC)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.REQUIRES,
                    )
                )

            # directive_refs
            for dir_id in data.get("directive_refs", []) or []:
                tgt_urn = artifact_to_urn("directive", dir_id)
                _ensure_node(nodes_by_urn, tgt_urn, NodeKind.DIRECTIVE)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.REQUIRES,
                    )
                )

            # opposed_by
            for opp in data.get("opposed_by", []) or []:
                opp_type = opp.get("type", "")
                opp_id = opp.get("id", "")
                if not opp_type or not opp_id:
                    continue
                opp_kind = _kind_for_type(opp_type)
                if opp_kind is None:
                    continue
                tgt_urn = artifact_to_urn(opp_type, opp_id)
                _ensure_node(nodes_by_urn, tgt_urn, opp_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.REPLACES,
                        reason=opp.get("reason"),
                    )
                )

    return list(nodes_by_urn.values()), edges


# ---------------------------------------------------------------------------
# T013: Action index walker
# ---------------------------------------------------------------------------


def extract_action_edges(
    doctrine_root: Path,
) -> tuple[list[DRGNode], list[DRGEdge]]:
    """Walk action index files and return action nodes + scope edges."""
    nodes_by_urn: dict[str, DRGNode] = {}
    edges: list[DRGEdge] = []
    seen_triples: set[tuple[str, str, str]] = set()

    def _add_edge(edge: DRGEdge) -> None:
        triple = (edge.source, edge.target, edge.relation.value)
        if triple not in seen_triples:
            seen_triples.add(triple)
            edges.append(edge)

    missions_dir = doctrine_root / "missions"
    if not missions_dir.is_dir():
        return [], []

    for index_path in sorted(missions_dir.rglob("actions/*/index.yaml")):
        data = _load_yaml(index_path)
        if data is None:
            continue

        action_name: str = data.get("action", index_path.parent.name)
        # Derive mission name from path: .../missions/<mission>/actions/<action>/index.yaml
        mission_name = index_path.parent.parent.parent.name
        action_urn = f"action:{mission_name}/{action_name}"
        _ensure_node(
            nodes_by_urn, action_urn, NodeKind.ACTION, action_name
        )

        # Map of field name -> artifact kind for scope edges
        scope_fields: list[tuple[str, str]] = [
            ("directives", "directive"),
            ("tactics", "tactic"),
            ("styleguides", "styleguide"),
            ("toolguides", "toolguide"),
            ("procedures", "procedure"),
        ]

        for field_name, kind in scope_fields:
            for raw_id in data.get(field_name, []) or []:
                tgt_urn = artifact_to_urn(kind, raw_id)
                _ensure_node(
                    nodes_by_urn, tgt_urn, _KIND_MAP.get(kind, NodeKind.GLOSSARY_SCOPE)
                )
                _add_edge(
                    DRGEdge(
                        source=action_urn,
                        target=tgt_urn,
                        relation=Relation.SCOPE,
                    )
                )

    return list(nodes_by_urn.values()), edges


# ---------------------------------------------------------------------------
# T016: Graph generator
# ---------------------------------------------------------------------------


def _discover_shipped_artifact_nodes(
    doctrine_root: Path,
    nodes_by_urn: dict[str, DRGNode],
) -> None:
    """Scan shipped directories for artifacts not yet tracked as nodes.

    This catches styleguides, toolguides, procedures, and agent profiles that
    are referenced in edges but were not walked as part of the primary
    extraction passes.
    """
    scan_dirs: list[tuple[str, str, NodeKind]] = [
        ("styleguides/shipped", "styleguide", NodeKind.STYLEGUIDE),
        ("toolguides/shipped", "toolguide", NodeKind.TOOLGUIDE),
        ("procedures/shipped", "procedure", NodeKind.PROCEDURE),
    ]
    for subdir, kind, node_kind in scan_dirs:
        shipped_dir = doctrine_root / subdir
        if not shipped_dir.is_dir():
            continue
        for path in sorted(shipped_dir.glob(f"*.{kind}.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            artifact_id: str = data.get("id", "")
            label: str = data.get("name", data.get("title", ""))
            if not artifact_id:
                continue
            urn = artifact_to_urn(kind, artifact_id)
            _ensure_node(nodes_by_urn, urn, node_kind, label or None)

    # Also scan writing subdirectory for styleguides
    writing_dir = doctrine_root / "styleguides" / "shipped" / "writing"
    if writing_dir.is_dir():
        for path in sorted(writing_dir.glob("*.styleguide.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            artifact_id = data.get("id", "")
            label = data.get("name", data.get("title", ""))
            if not artifact_id:
                continue
            urn = artifact_to_urn("styleguide", artifact_id)
            _ensure_node(nodes_by_urn, urn, NodeKind.STYLEGUIDE, label or None)


def generate_graph(
    doctrine_root: Path,
    output_path: Path,
    *,
    generated_at: str | None = None,
) -> DRGGraph:
    """Compose extraction + calibration into a validated ``graph.yaml``.

    Args:
        doctrine_root: Path to ``src/doctrine/``.
        output_path: Where to write the resulting YAML.
        generated_at: Optional fixed timestamp for deterministic output.
            If ``None``, ``"STATIC"`` is used so the output is always
            identical for the same input (idempotent).

    Returns:
        The validated ``DRGGraph`` instance.
    """
    # Step 1: Extract artifact nodes + edges
    artifact_nodes, artifact_edges = extract_artifact_edges(doctrine_root)

    # Step 2: Extract action nodes + edges
    action_nodes, action_edges = extract_action_edges(doctrine_root)

    # Step 3: Merge nodes (deduplicate by URN)
    nodes_by_urn: dict[str, DRGNode] = {}
    for node in artifact_nodes + action_nodes:
        _ensure_node(nodes_by_urn, node.urn, node.kind, node.label)

    # Step 4: Discover shipped artifacts not yet tracked
    _discover_shipped_artifact_nodes(doctrine_root, nodes_by_urn)

    # Step 5: Merge all edges
    all_edges = artifact_edges + action_edges

    # Step 6: Calibrate surfaces
    all_nodes_list = list(nodes_by_urn.values())
    calibrated_edges = calibrate_surfaces(all_nodes_list, all_edges)

    # Ensure any new calibration-target nodes exist
    all_urns = {n.urn for n in all_nodes_list}
    for edge in calibrated_edges:
        for urn in (edge.source, edge.target):
            if urn not in all_urns:
                # Infer kind from URN prefix
                prefix = urn.split(":", 1)[0]
                kind = _KIND_MAP.get(prefix)
                if kind is None:
                    continue  # unknown prefix -- should not happen
                _ensure_node(nodes_by_urn, urn, kind)
                all_urns.add(urn)

    # Step 7: Build graph with deterministic ordering
    ts = generated_at or "STATIC"
    sorted_nodes = sorted(nodes_by_urn.values(), key=lambda n: n.urn)
    sorted_edges = sorted(
        calibrated_edges,
        key=lambda e: (e.source, e.target, e.relation.value),
    )

    graph = DRGGraph(
        schema_version="1.0",
        generated_at=ts,
        generated_by="drg-migration-v1",
        nodes=sorted_nodes,
        edges=sorted_edges,
    )

    # Step 8: Validate
    assert_valid(graph)

    # Step 9: Write YAML
    _write_graph_yaml(graph, output_path)

    return graph


def _write_graph_yaml(graph: DRGGraph, output_path: Path) -> None:
    """Write the graph to *output_path* as sorted YAML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build plain dict for YAML serialisation (sorted keys for determinism)
    data: dict[str, Any] = {
        "schema_version": graph.schema_version,
        "generated_at": graph.generated_at,
        "generated_by": graph.generated_by,
        "nodes": [
            _node_to_dict(n)
            for n in graph.nodes
        ],
        "edges": [
            _edge_to_dict(e)
            for e in graph.edges
        ],
    }

    yaml_writer = YAML()
    yaml_writer.default_flow_style = False
    yaml_writer.allow_unicode = True
    # Sort keys at the top level for deterministic output
    with output_path.open("w") as fh:
        yaml_writer.dump(data, fh)


def _node_to_dict(node: DRGNode) -> dict[str, Any]:
    d: dict[str, Any] = {"urn": node.urn, "kind": node.kind.value}
    if node.label is not None:
        d["label"] = node.label
    return d


def _edge_to_dict(edge: DRGEdge) -> dict[str, Any]:
    d: dict[str, Any] = {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation.value,
    }
    if edge.when is not None:
        d["when"] = edge.when
    if edge.reason is not None:
        d["reason"] = edge.reason
    return d
