"""Rewrite legacy ``opposed_by`` entries in a downstream/org-pack into DRG edges.

FR-015 (contract: ``kitty-specs/doctrine-tension-edges-01KY1WPC/contracts/
migrate-opposed-by.md``). This module is the escape hatch for downstream /
org-pack doctrine content that still authors the legacy ``opposed_by``
(``Contradiction``) field once ``opposed_by`` is dropped from
``additionalProperties: false`` on the ``directive``/``tactic``/``paradigm``
schemas (mission ``doctrine-tension-edges-01KY1WPC`` WP03). Without this tool
an org pack that still authors ``opposed_by`` would only see a schema
validation error pointing at the symptom, not the fix.

This module is fully additive: it operates on an *external* pack directory
the operator points it at (``--pack PATH``) and never touches this repo's
own built-in doctrine content (that migration is WP02/WP03's job, landing on
different files). It only needs the relation vocabulary WP01 already
introduced (``Relation.IN_TENSION_WITH`` / ``RECONCILES_TENSION`` /
``REJECTS`` and ``NodeKind.ANTI_PATTERN``) to exist.

Classification heuristic
-------------------------
Each ``opposed_by`` entry is a mapping ``{type, id, reason}`` naming another
artifact the source directive/tactic/paradigm "opposes". Per D1/D2
(research.md) there is no purely mechanical signal in the *prose* that
distinguishes a tension-style entry from an anti-pattern-rejection-style
entry in general -- classifying by keyword-sniffing the ``reason`` text
would be a guess dressed up as precision. Instead this module asks a single,
structural, mechanically-checkable question:

    Does an artifact file of the declared ``type`` and ``id`` actually
    exist elsewhere in the pack?

- **Yes** -- the target is a first-class artifact of equal standing: a
  genuine peer rule that competes with the source on the same decision,
  never itself a "wrong" idea to be rejected. This is exactly the shape of
  a *tension* (D1): both sides remain valid; neither supersedes the other.
  The entry is rewritten to a symmetric ``in_tension_with`` edge,
  canonicalized with the lexicographically-smaller URN as ``source`` (C-002,
  mirroring WP02) so a tension pair only ever has one canonical direction.

- **No** -- the target has no artifact of its own anywhere in the pack. By
  construction it cannot be a competing rule; there is no rule there to
  compete with. It is a *label for a bad practice*, referenced only in
  order to be rejected. The entry is rewritten to a directional ``rejects``
  edge from the source artifact to a new (or reused) ``anti_pattern:<id>``
  node (creating the node, marked ``kind: anti_pattern``, the first time it
  is targeted -- mirrors WP02's node shape).

This heuristic was validated against every ``opposed_by`` entry in this
repo's own built-in doctrine content (the reference corpus WP03 is about to
retire): the two tension-style entries (``DIRECTIVE_024`` <-> ``DIRECTIVE_025``,
and the tactic <-> ``DIRECTIVE_025`` pair) both resolve to real artifact
files; all eight anti-pattern-rejection entries (e.g. ``brownfield-onboarding``
-> ``big-ball-of-mud``) resolve to none.

**Unclassifiable entries (T036)**: if the declared ``type``/``id`` pair does
NOT resolve to a file under the declared type, but the *same* ``id`` DOES
exist under a *different* artifact type elsewhere in the pack, the
structural signal is self-contradictory -- is this a mistyped peer
reference, or a coincidentally-named anti-pattern? This module refuses to
guess: it records the entry as unclassifiable, naming the source file, the
entry, and the conflicting match, rather than silently picking a relation.
The same happens for a structurally malformed entry (missing/unknown
``type``, missing/empty ``id``). Callers (the CLI layer) surface these as a
clear, actionable diagnostic and a non-zero exit -- never a raw Pydantic
validation traceback.

Precedent / conventions reused
-------------------------------
Modelled on :mod:`specify_cli.migration.backfill_identity`'s
scan-and-report shape (a pure function returns a structured result; the CLI
layer formats it) and reuses the core DRG models from
:mod:`doctrine.drg.models` (``DRGGraph``, ``DRGNode``, ``DRGEdge``,
``NodeKind``, ``Relation``) rather than inventing a parallel schema. New
edges/nodes are written into per-kind ``<kind>.graph.yaml`` fragment files
at the pack root (``directive.graph.yaml`` / ``tactic.graph.yaml`` /
``paradigm.graph.yaml``), mirroring both WP02's authoring surface (the
built-in doctrine tree's own ``src/doctrine/<kind>.graph.yaml`` fragments)
and this repo's existing convention that an edge is filed under the graph
fragment matching its (possibly canonicalized) ``source`` URN's kind -- e.g.
``paradigm.graph.yaml`` already carries ``paradigm -> directive`` ``requires``
edges today.

All functions are safe to call repeatedly: once every ``opposed_by`` entry
has been rewritten and removed, a subsequent run finds nothing left to scan
and performs no writes (idempotent, NFR "safe to run against an
already-clean pack").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from charter.drg import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

#: Artifact type -> filename suffix used to discover source YAML files.
_ARTIFACT_SUFFIXES: dict[str, str] = {
    "directive": ".directive.yaml",
    "tactic": ".tactic.yaml",
    "paradigm": ".paradigm.yaml",
}

#: Artifact type -> per-kind DRG graph fragment filename at the pack root.
_GRAPH_FILENAMES: dict[str, str] = {
    "directive": "directive.graph.yaml",
    "tactic": "tactic.graph.yaml",
    "paradigm": "paradigm.graph.yaml",
}

_GENERATED_BY = "rewrite-opposed-by-v1"


def _make_yaml() -> YAML:
    """Return a ruamel.yaml instance configured for round-trip editing."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=2, offset=0)
    return y


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RewrittenEntry:
    """One ``opposed_by`` entry that was (or, in dry-run, would be) rewritten."""

    source_file: Path
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation: str  # "in_tension_with" | "rejects"
    reason: str | None = None
    created_anti_pattern_node: bool = False


@dataclass
class UnclassifiableEntry:
    """An ``opposed_by`` entry this module refuses to guess a relation for."""

    source_file: Path
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    message: str


@dataclass
class RewriteResult:
    """Structured outcome of a :func:`rewrite_opposed_by_pack` run."""

    pack_root: Path
    dry_run: bool
    rewritten: list[RewrittenEntry] = field(default_factory=list)
    unclassifiable: list[UnclassifiableEntry] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """``True`` when any entry could not be unambiguously classified."""
        return bool(self.unclassifiable)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _discover_source_files(pack_root: Path) -> list[tuple[Path, str]]:
    """Return every ``*.<type>.yaml`` source file under *pack_root*.

    Recursive (``rglob``) so both a flat pack layout (``<pack_root>/
    directives/foo.directive.yaml``) and a nested built-in-style layout
    (``<pack_root>/directives/built-in/foo.directive.yaml``) are discovered.
    """
    files: list[tuple[Path, str]] = []
    for artifact_type, suffix in _ARTIFACT_SUFFIXES.items():
        for path in sorted(pack_root.rglob(f"*{suffix}")):
            files.append((path, artifact_type))
    return files


def _build_artifact_registry(pack_root: Path) -> dict[tuple[str, str], Path]:
    """Return a ``{(type, id): path}`` map of every real artifact in the pack.

    Keyed by the artifact's own ``id`` field content (not its filename) so
    the classification heuristic is robust to naming-convention differences
    between packs.
    """
    registry: dict[tuple[str, str], Path] = {}
    yaml_rt = _make_yaml()
    for path, artifact_type in _discover_source_files(pack_root):
        try:
            data = yaml_rt.load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 -- best-effort registry build
            logger.warning("Skipping unreadable artifact file %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            continue
        art_id = data.get("id")
        if isinstance(art_id, str) and art_id:
            registry[(artifact_type, art_id)] = path
    return registry


# ---------------------------------------------------------------------------
# Classification (T036: unclassifiable-entry diagnostic)
# ---------------------------------------------------------------------------


def _classify_entry(
    *,
    source_type: str,
    source_id: str,
    source_file: Path,
    entry: Any,
    registry: dict[tuple[str, str], Path],
) -> RewrittenEntry | UnclassifiableEntry:
    """Classify a single ``opposed_by`` entry as tension-style or rejection-style.

    Returns a :class:`RewrittenEntry` (successfully classified) or an
    :class:`UnclassifiableEntry` (T036 diagnostic case) -- never raises.
    """
    if not isinstance(entry, dict):
        return UnclassifiableEntry(
            source_file=source_file,
            source_type=source_type,
            source_id=source_id,
            target_type="",
            target_id="",
            message=(
                f"{source_file}: opposed_by entry on {source_type}:{source_id} "
                f"is not a mapping ({entry!r}); expected {{type, id, reason}}. "
                "Fix the entry manually and re-run "
                "`spec-kitty migrate rewrite-opposed-by`."
            ),
        )

    target_type = entry.get("type")
    target_id = entry.get("id")
    reason = entry.get("reason")

    if target_type not in _ARTIFACT_SUFFIXES or not isinstance(target_id, str) or not target_id:
        return UnclassifiableEntry(
            source_file=source_file,
            source_type=source_type,
            source_id=source_id,
            target_type=str(target_type),
            target_id=str(target_id) if target_id is not None else "",
            message=(
                f"{source_file}: opposed_by entry on {source_type}:{source_id} "
                f"has an invalid or missing type/id ({entry!r}); expected "
                f"'type' in {sorted(_ARTIFACT_SUFFIXES)} and a non-empty "
                "'id'. Fix the entry manually and re-run "
                "`spec-kitty migrate rewrite-opposed-by`."
            ),
        )

    resolved_as_declared = (target_type, target_id) in registry
    conflicting_type = next(
        (
            other_type
            for other_type in _ARTIFACT_SUFFIXES
            if other_type != target_type and (other_type, target_id) in registry
        ),
        None,
    )

    if conflicting_type is not None:
        return UnclassifiableEntry(
            source_file=source_file,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            message=(
                f"{source_file}: opposed_by target {target_type}:{target_id} "
                f"(from {source_type}:{source_id}) is ambiguous -- "
                + (
                    f"id {target_id!r} also exists as a {conflicting_type} "
                    "artifact in this pack"
                    if resolved_as_declared
                    else (
                        f"no {target_type} artifact named {target_id!r} exists, "
                        f"but a {conflicting_type} artifact with that id does"
                    )
                )
                + ". Unclear whether this is a mistyped peer reference or a "
                "coincidentally-named anti-pattern -- resolve manually "
                "(fix the declared type, or rename one of the two artifacts) "
                "before re-running `spec-kitty migrate rewrite-opposed-by`."
            ),
        )

    relation = "in_tension_with" if resolved_as_declared else "rejects"
    return RewrittenEntry(
        source_file=source_file,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relation=relation,
        reason=reason if isinstance(reason, str) else None,
    )


# ---------------------------------------------------------------------------
# Graph fragment I/O
# ---------------------------------------------------------------------------


def _load_graph(pack_root: Path, artifact_type: str) -> DRGGraph:
    """Load ``<pack_root>/<artifact_type>.graph.yaml``, or a fresh empty graph."""
    path = pack_root / _GRAPH_FILENAMES[artifact_type]
    if not path.exists():
        return DRGGraph(
            schema_version="1.0",
            generated_at=datetime.now(UTC).isoformat(),
            generated_by=_GENERATED_BY,
            nodes=[],
            edges=[],
        )
    yaml_safe = YAML(typ="safe")
    data = yaml_safe.load(path.read_text(encoding="utf-8")) or {}
    return DRGGraph.model_validate(data)


def _node_to_dict(node: DRGNode) -> dict[str, Any]:
    out: dict[str, Any] = {"urn": node.urn, "kind": node.kind.value}
    if node.label is not None:
        out["label"] = node.label
    if node.tags:
        out["tags"] = list(node.tags)
    return out


def _edge_to_dict(edge: DRGEdge) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation.value,
    }
    if edge.reason:
        out["reason"] = edge.reason
    if edge.when:
        out["when"] = edge.when
    return out


def _write_graph(pack_root: Path, artifact_type: str, graph: DRGGraph) -> None:
    """Write *graph* to ``<pack_root>/<artifact_type>.graph.yaml``."""
    path = pack_root / _GRAPH_FILENAMES[artifact_type]
    payload: dict[str, Any] = {
        "schema_version": graph.schema_version,
        "generated_at": graph.generated_at,
        "generated_by": graph.generated_by,
        "nodes": [_node_to_dict(n) for n in graph.nodes],
        "edges": [_edge_to_dict(e) for e in graph.edges],
    }
    yaml_rt = _make_yaml()
    with path.open("w", encoding="utf-8") as fh:
        yaml_rt.dump(payload, fh)


def _edge_exists(graph: DRGGraph, edge: DRGEdge) -> bool:
    return any(
        e.source == edge.source and e.target == edge.target and e.relation == edge.relation
        for e in graph.edges
    )


def _apply_entry_to_graphs(graphs: dict[str, DRGGraph], entry: RewrittenEntry) -> None:
    """Append the edge (and, for ``rejects``, the anti-pattern node) for *entry*.

    Filed under the graph fragment matching the edge's (possibly
    canonicalized) ``source`` URN kind -- mirrors this repo's existing
    convention that e.g. ``paradigm -> directive`` edges live in
    ``paradigm.graph.yaml``, not ``directive.graph.yaml``.
    """
    source_urn = f"{entry.source_type}:{entry.source_id}"

    if entry.relation == "rejects":
        target_urn = f"anti_pattern:{entry.target_id}"
        graph = graphs[entry.source_type]
        if not any(n.urn == target_urn for n in graph.nodes):
            graph.nodes.append(
                DRGNode(urn=target_urn, kind=NodeKind.ANTI_PATTERN, tags=["anti-pattern"])
            )
            entry.created_anti_pattern_node = True
        edge = DRGEdge(
            source=source_urn, target=target_urn, relation=Relation.REJECTS, reason=entry.reason
        )
        if not _edge_exists(graph, edge):
            graph.edges.append(edge)
        return

    # in_tension_with -- symmetric; C-002 canonical single edge, lex-smaller
    # URN as source (mirrors WP02).
    target_urn = f"{entry.target_type}:{entry.target_id}"
    if source_urn <= target_urn:
        edge_source, edge_target = source_urn, target_urn
    else:
        edge_source, edge_target = target_urn, source_urn
    edge_kind = edge_source.split(":", 1)[0]
    graph = graphs[edge_kind]
    edge = DRGEdge(
        source=edge_source,
        target=edge_target,
        relation=Relation.IN_TENSION_WITH,
        reason=entry.reason,
    )
    if not _edge_exists(graph, edge):
        graph.edges.append(edge)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def rewrite_opposed_by_pack(pack_root: Path, *, dry_run: bool = False) -> RewriteResult:
    """Scan *pack_root* for ``opposed_by`` entries and rewrite them to DRG edges.

    Idempotent: once every entry has been rewritten and its ``opposed_by``
    key removed, a subsequent call finds nothing to do and writes nothing.

    A source file with one or more unclassifiable entries (T036) is left
    entirely untouched (its ``opposed_by`` key is NOT removed, and none of
    its entries are rewritten) so the pack never ends up in a
    partially-migrated, silently-lossy state -- the operator fixes the
    flagged entry and re-runs.

    Args:
        pack_root: Absolute path to the target pack's root directory.
        dry_run: When ``True``, compute the result without writing anything.

    Returns:
        A :class:`RewriteResult` describing what was (or would be) rewritten,
        plus any unclassifiable entries.
    """
    result = RewriteResult(pack_root=pack_root, dry_run=dry_run)
    registry = _build_artifact_registry(pack_root)

    graphs: dict[str, DRGGraph] = {
        artifact_type: _load_graph(pack_root, artifact_type) for artifact_type in _ARTIFACT_SUFFIXES
    }
    touched_kinds: set[str] = set()
    yaml_rt = _make_yaml()

    for source_file, source_type in _discover_source_files(pack_root):
        text = source_file.read_text(encoding="utf-8")
        data = yaml_rt.load(text)
        if not isinstance(data, dict):
            continue
        opposed_by = data.get("opposed_by")
        if not opposed_by:
            continue
        source_id = data.get("id")
        if not isinstance(source_id, str) or not source_id:
            result.unclassifiable.append(
                UnclassifiableEntry(
                    source_file=source_file,
                    source_type=source_type,
                    source_id="",
                    target_type="",
                    target_id="",
                    message=(
                        f"{source_file}: has an opposed_by block but no usable "
                        "top-level 'id' field; cannot build the source URN for "
                        "any edge. Fix the artifact's id and re-run "
                        "`spec-kitty migrate rewrite-opposed-by`."
                    ),
                )
            )
            continue

        classifications = [
            _classify_entry(
                source_type=source_type,
                source_id=source_id,
                source_file=source_file,
                entry=entry,
                registry=registry,
            )
            for entry in opposed_by
        ]
        unclassifiable = [c for c in classifications if isinstance(c, UnclassifiableEntry)]
        if unclassifiable:
            result.unclassifiable.extend(unclassifiable)
            continue

        rewritten = [c for c in classifications if isinstance(c, RewrittenEntry)]
        for entry in rewritten:
            _apply_entry_to_graphs(graphs, entry)
            if entry.relation == "rejects":
                touched_kinds.add(entry.source_type)
            else:
                canonical_source = min(
                    f"{entry.source_type}:{entry.source_id}",
                    f"{entry.target_type}:{entry.target_id}",
                )
                touched_kinds.add(canonical_source.split(":", 1)[0])
        result.rewritten.extend(rewritten)

        if not dry_run and rewritten:
            del data["opposed_by"]
            with source_file.open("w", encoding="utf-8") as fh:
                yaml_rt.dump(data, fh)

    if not dry_run:
        for artifact_type in sorted(touched_kinds):
            _write_graph(pack_root, artifact_type, graphs[artifact_type])

    return result
