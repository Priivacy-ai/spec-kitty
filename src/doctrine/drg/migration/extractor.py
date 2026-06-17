"""Extract inline reference fields from built-in doctrine into DRG nodes + edges.

Public API:
    extract_artifact_edges(doctrine_root) -> (nodes, edges)
    extract_action_edges(doctrine_root)   -> (nodes, edges)
    generate_graph(doctrine_root, output_path) -> DRGGraph
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from doctrine.drg.migration.calibrator import calibrate_surfaces
from doctrine.drg.migration.id_normalizer import artifact_to_urn
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.validator import assert_valid

SPECIFICATION_BY_EXAMPLE = "paradigm:specification-by-example"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_yaml = YAML(typ="safe")

# ---------------------------------------------------------------------------
# T027: Path-string reference resolver for styleguide / toolguide ``references``
# ---------------------------------------------------------------------------

#: Ordered list of (compiled-pattern, kind) pairs.  Each pattern captures the
#: filename stem (without kind extension and without any subdirectory prefix) in
#: group 1.  The ``(?:.+/)?`` non-capturing optional subdir fragment ensures that
#: both flat paths (``built-in/foo.tactic.yaml``) and paths rooted under a
#: subdirectory (``built-in/testing/foo.tactic.yaml``) resolve to the same stem.
#:
#: Only **built-in** artifact directories are covered; ``_proposed`` profiles and
#: non-artifact files (README, glossary YAML, URLs) will not match any pattern
#: and therefore return ``None`` from :func:`_resolve_path_ref`.
_PATH_KIND_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"src/doctrine/tactics/built-in/(?:.+/)?([^/]+)\.tactic\.yaml$"
        ),
        "tactic",
    ),
    (
        re.compile(
            r"src/doctrine/paradigms/built-in/(?:.+/)?([^/]+)\.paradigm\.yaml$"
        ),
        "paradigm",
    ),
    (
        re.compile(
            r"src/doctrine/directives/built-in/(?:.+/)?([^/]+)\.directive\.yaml$"
        ),
        "directive",
    ),
    (
        re.compile(
            r"src/doctrine/styleguides/built-in/(?:.+/)?([^/]+)\.styleguide\.yaml$"
        ),
        "styleguide",
    ),
    (
        re.compile(
            r"src/doctrine/toolguides/built-in/(?:.+/)?([^/]+)\.toolguide\.yaml$"
        ),
        "toolguide",
    ),
    (
        re.compile(
            r"src/doctrine/procedures/built-in/(?:.+/)?([^/]+)\.procedure\.yaml$"
        ),
        "procedure",
    ),
    (
        re.compile(
            r"src/doctrine/agent_profiles/built-in/(?:.+/)?([^/]+)\.agent\.yaml$"
        ),
        "agent_profile",
    ),
]


def _resolve_path_ref(path_str: str) -> tuple[str, str] | None:
    """Return ``(kind, raw_id)`` for a raw path-string reference, or ``None``.

    Styleguide and toolguide ``references`` fields carry plain file paths such as
    ``src/doctrine/tactics/built-in/tdd-red-green-refactor.tactic.yaml``.  This
    helper maps such a path to the canonical ``(kind, raw_id)`` pair that
    :func:`doctrine.drg.migration.id_normalizer.artifact_to_urn` can resolve into
    a full URN.

    Only **built-in** artifact paths under ``src/doctrine/`` are matched; URLs,
    glossary files, ADR documents, ``_proposed`` profiles, and any other path that
    does not match one of the recognised patterns return ``None`` (fail-closed per
    NFR-003 — never silently infer identity from an unrecognised path).

    Args:
        path_str: A raw path string from a styleguide or toolguide ``references``
            list entry.

    Returns:
        ``(kind, raw_id)`` where *raw_id* is the filename stem (stripped of any
        subdirectory prefix and kind extension).  For directives the caller must
        pass *raw_id* through
        :func:`doctrine.drg.migration.id_normalizer.artifact_to_urn` for
        ``DIRECTIVE_NNN`` normalisation.  Returns ``None`` if the path does not
        match any known pattern.
    """
    for pattern, kind in _PATH_KIND_PATTERNS:
        m = pattern.search(path_str)
        if m:
            return kind, m.group(1)
    return None

_KIND_MAP: dict[str, NodeKind] = {
    "directive": NodeKind.DIRECTIVE,
    "tactic": NodeKind.TACTIC,
    "paradigm": NodeKind.PARADIGM,
    "styleguide": NodeKind.STYLEGUIDE,
    "toolguide": NodeKind.TOOLGUIDE,
    "procedure": NodeKind.PROCEDURE,
    "agent_profile": NodeKind.AGENT_PROFILE,
    "template": NodeKind.TEMPLATE,
    "action": NodeKind.ACTION,
}

# Reference types that are NOT DRG node kinds (skipped during extraction).
_SKIP_REF_TYPES: frozenset[str] = frozenset()

_CURATED_ARTIFACT_EDGES: tuple[tuple[str, str, Relation], ...] = (
    # WP06/WP07 (FR-001/FR-028 hard cutover): built-in profile lineage is now
    # authored directly as DRG ``specializes_from`` edges. The legacy
    # ``specializes-from`` profile field has been retired (and is rejected by the
    # profile model), so these edges are the single source of lineage truth.
    (
        "agent_profile:python-pedro",
        "agent_profile:implementer-ivan",
        Relation.SPECIALIZES_FROM,
    ),
    (
        "agent_profile:java-jenny",
        "agent_profile:implementer-ivan",
        Relation.SPECIALIZES_FROM,
    ),
    (
        "agent_profile:node-norris",
        "agent_profile:implementer-ivan",
        Relation.SPECIALIZES_FROM,
    ),
    (
        "agent_profile:frontend-freddy",
        "agent_profile:implementer-ivan",
        Relation.SPECIALIZES_FROM,
    ),
    (
        SPECIFICATION_BY_EXAMPLE,
        "tactic:acceptance-test-first",
        Relation.REQUIRES,
    ),
    (
        SPECIFICATION_BY_EXAMPLE,
        "tactic:atdd-adversarial-acceptance",
        Relation.REQUIRES,
    ),
    (
        SPECIFICATION_BY_EXAMPLE,
        "tactic:usage-examples-sync",
        Relation.REQUIRES,
    ),
    (
        "directive:DIRECTIVE_040",
        "tactic:five-paradigm-parallel-debugging",
        Relation.REQUIRES,
    ),
    (
        "directive:DIRECTIVE_037",
        "tactic:usage-examples-sync",
        Relation.REQUIRES,
    ),
    (
        "directive:DIRECTIVE_001",
        "tactic:paula-patterns-architecture-scout-review",
        Relation.REQUIRES,
    ),
    (
        "directive:DIRECTIVE_003",
        "tactic:traceable-decisions",
        Relation.REQUIRES,
    ),
    (
        "agent_profile:doctrine-daphne",
        "procedure:onboard-external-agent-to-pack",
        Relation.APPLIES,
    ),
)


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


def _relation_for_procedure_ref_type(ref_type: str) -> Relation:
    """Map procedure references to relations.

    Procedures orchestrate required operational artifacts. Template/style/tool
    references remain advisory.
    """
    if ref_type in {"directive", "tactic", "procedure"}:
        return Relation.REQUIRES
    return Relation.SUGGESTS


def _kind_for_type(ref_type: str) -> NodeKind | None:
    """Map a reference ``type`` string to a NodeKind, or ``None`` if skipped."""
    if ref_type in _SKIP_REF_TYPES:
        return None
    return _KIND_MAP.get(ref_type)


def _add_ref_edge(
    *,
    nodes_by_urn: dict[str, DRGNode],
    add_edge: Any,
    source: str,
    ref_type: str,
    ref_id: str,
    relation: Relation,
    when: str | None = None,
    reason: str | None = None,
) -> None:
    tgt_kind = _kind_for_type(ref_type)
    if tgt_kind is None:
        return
    tgt_urn = artifact_to_urn(ref_type, ref_id)
    _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
    add_edge(
        DRGEdge(
            source=source,
            target=tgt_urn,
            relation=relation,
            when=when,
            reason=reason,
        )
    )


def _merge_edge_metadata(existing: DRGEdge, incoming: DRGEdge) -> DRGEdge:
    """Preserve deterministic edge metadata when duplicate triples are found."""
    updates: dict[str, str] = {}
    if existing.when is None and incoming.when is not None:
        updates["when"] = incoming.when
    if existing.reason is None and incoming.reason is not None:
        updates["reason"] = incoming.reason
    if not updates:
        return existing
    return existing.model_copy(update=updates)


# ---------------------------------------------------------------------------
# T012: Artifact walker (directives, tactics, paradigms, procedures)
# ---------------------------------------------------------------------------


def extract_artifact_edges(  # noqa: C901
    doctrine_root: Path,
) -> tuple[list[DRGNode], list[DRGEdge]]:
    """Walk built-in directives, tactics, paradigms, and procedures; return (nodes, edges).

    Every inline reference field is converted to a typed DRG edge.
    Nodes are deduplicated by URN.
    """
    nodes_by_urn: dict[str, DRGNode] = {}
    edges_by_triple: dict[tuple[str, str, str], DRGEdge] = {}

    def _add_edge(edge: DRGEdge) -> None:
        triple = (edge.source, edge.target, edge.relation.value)
        if triple in edges_by_triple:
            edges_by_triple[triple] = _merge_edge_metadata(
                edges_by_triple[triple], edge
            )
        else:
            edges_by_triple[triple] = edge

    # --- Directives ---
    directives_dir = doctrine_root / "directives" / "built-in"
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
    tactics_dir = doctrine_root / "tactics" / "built-in"
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
    paradigms_dir = doctrine_root / "paradigms" / "built-in"
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

            for ref in data.get("references", []) or []:
                ref_type = ref.get("type", "")
                ref_id = ref.get("id", "")
                if not ref_type or not ref_id:
                    continue
                _add_ref_edge(
                    nodes_by_urn=nodes_by_urn,
                    add_edge=_add_edge,
                    source=src_urn,
                    ref_type=ref_type,
                    ref_id=ref_id,
                    relation=_relation_for_procedure_ref_type(ref_type),
                    when=ref.get("when"),
                    reason=ref.get("reason"),
                )

    # --- Procedures ---
    procedures_dir = doctrine_root / "procedures" / "built-in"
    if procedures_dir.is_dir():
        for path in sorted(procedures_dir.glob("*.procedure.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            procedure_id = data.get("id", "")
            procedure_name = data.get("name", "")
            src_urn = artifact_to_urn("procedure", procedure_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.PROCEDURE, procedure_name)

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
                        relation=_relation_for_procedure_ref_type(ref_type),
                    )
                )

    # --- Agent profiles ---
    profiles_dir = doctrine_root / "agent_profiles" / "built-in"
    if profiles_dir.is_dir():
        for path in sorted(profiles_dir.glob("*.agent.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            profile_id = data.get("profile-id", "")
            if not profile_id:
                continue
            src_urn = artifact_to_urn("agent_profile", profile_id)
            label = data.get("name", "")
            _ensure_node(nodes_by_urn, src_urn, NodeKind.AGENT_PROFILE, label or None)

            context_sources = data.get("context-sources", {}) or {}
            for directive_id in context_sources.get("directives", []) or []:
                _add_ref_edge(
                    nodes_by_urn=nodes_by_urn,
                    add_edge=_add_edge,
                    source=src_urn,
                    ref_type="directive",
                    ref_id=str(directive_id),
                    relation=Relation.REQUIRES,
                )
            for ref in data.get("tactic-references", []) or []:
                ref_id = ref.get("id", "")
                if not ref_id:
                    continue
                _add_ref_edge(
                    nodes_by_urn=nodes_by_urn,
                    add_edge=_add_edge,
                    source=src_urn,
                    ref_type="tactic",
                    ref_id=ref_id,
                    relation=Relation.REQUIRES,
                    reason=ref.get("rationale"),
                )

    # --- Styleguides (T027) ---
    # Styleguide ``references`` is a plain ``list[str]`` of file paths — NOT the
    # structured ``{type, id}`` form used by tactics/directives.  Use
    # :func:`_resolve_path_ref` to map each path to a (kind, raw_id) pair.
    styleguides_dir = doctrine_root / "styleguides" / "built-in"
    if styleguides_dir.is_dir():
        for path in sorted(styleguides_dir.rglob("*.styleguide.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            sg_id: str = data.get("id", "")
            sg_title: str = data.get("title", "")
            if not sg_id:
                continue
            src_urn = artifact_to_urn("styleguide", sg_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.STYLEGUIDE, sg_title or None)

            for ref_raw in data.get("references", []) or []:
                if not isinstance(ref_raw, str):
                    continue
                resolved = _resolve_path_ref(ref_raw)
                if resolved is None:
                    continue  # URL, glossary path, or unrecognised pattern — skip
                ref_kind, ref_id = resolved
                tgt_kind = _KIND_MAP.get(ref_kind)
                if tgt_kind is None:
                    continue
                tgt_urn = artifact_to_urn(ref_kind, ref_id)
                _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.SUGGESTS,
                    )
                )

    # --- Toolguides (T028) ---
    # Toolguides may now carry a ``references`` field (additive schema change per
    # DIRECTIVE_018 — see toolguide.schema.yaml).  Like styleguides, the field is
    # a ``list[str]`` of file paths resolved via :func:`_resolve_path_ref`.
    toolguides_dir = doctrine_root / "toolguides" / "built-in"
    if toolguides_dir.is_dir():
        for path in sorted(toolguides_dir.rglob("*.toolguide.yaml")):
            data = _load_yaml(path)
            if data is None:
                continue
            tg_id: str = data.get("id", "")
            tg_title: str = data.get("title", "")
            if not tg_id:
                continue
            src_urn = artifact_to_urn("toolguide", tg_id)
            _ensure_node(nodes_by_urn, src_urn, NodeKind.TOOLGUIDE, tg_title or None)

            for ref_raw in data.get("references", []) or []:
                if not isinstance(ref_raw, str):
                    continue
                resolved = _resolve_path_ref(ref_raw)
                if resolved is None:
                    continue
                ref_kind, ref_id = resolved
                tgt_kind = _KIND_MAP.get(ref_kind)
                if tgt_kind is None:
                    continue
                tgt_urn = artifact_to_urn(ref_kind, ref_id)
                _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
                _add_edge(
                    DRGEdge(
                        source=src_urn,
                        target=tgt_urn,
                        relation=Relation.SUGGESTS,
                    )
                )

    for source, target, relation in _CURATED_ARTIFACT_EDGES:
        source_kind = source.split(":", 1)[0]
        target_kind = target.split(":", 1)[0]
        _ensure_node(nodes_by_urn, source, _KIND_MAP[source_kind])
        _ensure_node(nodes_by_urn, target, _KIND_MAP[target_kind])
        _add_edge(DRGEdge(source=source, target=target, relation=relation))

    return list(nodes_by_urn.values()), list(edges_by_triple.values())


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
            ("paradigms", "paradigm"),
            ("styleguides", "styleguide"),
            ("toolguides", "toolguide"),
            ("procedures", "procedure"),
            ("agent_profiles", "agent_profile"),
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


def _discover_built_in_artifact_nodes(
    doctrine_root: Path,
    nodes_by_urn: dict[str, DRGNode],
) -> None:
    """Scan built-in directories for artifacts not yet tracked as nodes.

    This catches styleguides, toolguides, procedures, and agent profiles that
    are referenced in edges but were not walked as part of the primary
    extraction passes.
    """
    # ``rglob`` is used so that artifacts in subdirectories (e.g. toolguides under
    # ``system_tools/``, styleguides under ``writing/``) are always discovered.
    # Each (subdir, kind, node_kind) triple maps to a ``rglob`` pattern; the
    # previous ``glob`` form missed files in second-level subdirectories.
    scan_dirs: list[tuple[str, str, NodeKind]] = [
        ("styleguides/built-in", "styleguide", NodeKind.STYLEGUIDE),
        ("toolguides/built-in", "toolguide", NodeKind.TOOLGUIDE),
        ("procedures/built-in", "procedure", NodeKind.PROCEDURE),
        ("agent_profiles/built-in", "agent_profile", NodeKind.AGENT_PROFILE),
    ]
    for subdir, kind, node_kind in scan_dirs:
        built_in_dir = doctrine_root / subdir
        if not built_in_dir.is_dir():
            continue
        glob_pattern = "*.agent.yaml" if kind == "agent_profile" else f"*.{kind}.yaml"
        id_key = "profile-id" if kind == "agent_profile" else "id"
        for path in sorted(built_in_dir.rglob(glob_pattern)):
            data = _load_yaml(path)
            if data is None:
                continue
            artifact_id: str = data.get(id_key, "")
            label: str = data.get("name", data.get("title", ""))
            if not artifact_id:
                continue
            urn = artifact_to_urn(kind, artifact_id)
            _ensure_node(nodes_by_urn, urn, node_kind, label or None)


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

    # Step 4: Discover built-in artifacts not yet tracked
    _discover_built_in_artifact_nodes(doctrine_root, nodes_by_urn)

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
    yaml_writer.width = 4096
    # Sort keys at the top level for deterministic output
    with output_path.open("w") as fh:
        yaml_writer.dump(data, fh)


def _node_to_dict(node: DRGNode) -> dict[str, Any]:
    d: dict[str, Any] = {"urn": node.urn, "kind": node.kind.value}
    if node.label is not None:
        d["label"] = node.label.strip()
    return d


def _edge_to_dict(edge: DRGEdge) -> dict[str, Any]:
    d: dict[str, Any] = {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation.value,
    }
    if edge.when is not None:
        d["when"] = edge.when.strip()
    if edge.reason is not None:
        d["reason"] = edge.reason.strip()
    return d
