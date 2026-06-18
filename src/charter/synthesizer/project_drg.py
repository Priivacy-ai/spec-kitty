"""Project-level DRG overlay writer.

Thin composer over ``src/doctrine/drg`` primitives (KD-1 rule: no reusable
graph logic here — push any generic graph logic to ``src/doctrine/drg/``
instead).

Public API:

- ``emit_project_layer(targets, adapter_outputs, spec_kitty_version,
                       built_in_drg) -> DRGGraph``
  Builds a ``DRGGraph`` for the project-local overlay.  Raises
  ``ProjectDRGValidationError`` on additive-only violations (FR-020 / EC-6).

- ``persist(graph, staging_dir, guard)``
  Serializes the graph under ``staging_dir/doctrine`` via the supplied
  ``PathGuard``. The promote step (WP03) will move this file to the live
  project doctrine directory.

See data-model.md §E-5 for the overlay discipline.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ruamel.yaml import YAML

from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation

from charter.synthesizer._constants import GRAPH_FILENAME as _GRAPH_FILENAME

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
    built_in_drg: DRGGraph,
) -> DRGGraph:
    """Build an additive project-layer ``DRGGraph`` from *targets*.

    One node is emitted per target; edges are derived from each target's
    ``source_urns`` (direction: project node ``derived_from``/``requires``
    the source URN per existing DRG conventions).

    FR-020 / EC-6 additive-only enforcement:

    * A target whose URN is already present in ``built_in_drg.nodes`` raises
      ``ProjectDRGValidationError`` — synthesized artifacts carry *new* URNs;
      they do not shadow built-in URNs.
    * Any ``(source, target, relation)`` triple that already exists in
      ``built_in_drg.edges`` raises ``ProjectDRGValidationError`` — no
      duplicate edges allowed.

    Args:
        targets: Ordered sequence of ``SynthesisTarget`` objects to emit.
        spec_kitty_version: Version string embedded in ``generated_by``.
        built_in_drg: The built-in-layer ``DRGGraph`` used for additive-only
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
    built_in_node_urns: frozenset[str] = frozenset(n.urn for n in built_in_drg.nodes)
    built_in_edge_triples: frozenset[tuple[str, str, str]] = frozenset(
        (e.source, e.target, e.relation.value) for e in built_in_drg.edges
    )

    nodes: list[DRGNode] = []
    edges: list[DRGEdge] = []
    seen_urns: set[str] = set()  # tracks overlay-internal duplicates

    for target in targets:
        urn = target.urn

        # FR-020 / EC-6: reject URNs that collide with built-in nodes.
        if urn in built_in_node_urns:
            raise ProjectDRGValidationError(
                errors=(
                    f"Additive-only violation (FR-020 / EC-6): URN '{urn}' "
                    f"already exists in the built-in DRG layer.  Synthesized "
                    f"artifacts must carry new URNs disjoint from built-in nodes.",
                ),
                merged_graph_summary=(
                    f"built_in_nodes={len(built_in_drg.nodes)}, "
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
        # *requires* for directives) the upstream built-in/project URN.
        for source_urn in target.source_urns:
            relation = (
                Relation.REQUIRES if target.kind == "directive"
                else Relation.APPLIES
            )
            triple = (urn, source_urn, relation.value)

            # FR-020: reject edges whose triple already exists in built-in.
            if triple in built_in_edge_triples:
                raise ProjectDRGValidationError(
                    errors=(
                        f"Duplicate edge (FR-020 / EC-6): triple "
                        f"({urn!r} --{relation.value}--> {source_urn!r}) "
                        f"already exists in the built-in DRG layer.",
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


def apply_post_condition(
    repo_root: Path,
    *,
    has_project_graph: bool,
) -> None:
    """Enforce the FR-009 post-condition on the live ``.kittify/`` tree.

    After ``write_pipeline.promote`` returns, exactly one of two states must
    hold:

    1. ``has_project_graph=True``  -> ``.kittify/doctrine/graph.yaml`` exists
       and the synthesis manifest records ``built_in_only=False`` (default).
       No-op: ``promote`` already wrote both files in that case.
    2. ``has_project_graph=False`` -> no live ``graph.yaml`` is present and
       the synthesis manifest records ``built_in_only=True``.  This function
       performs the two mutations atomically from the caller's perspective:
       it unlinks any pre-existing ``.kittify/doctrine/graph.yaml`` and
       rewrites the manifest with ``built_in_only=True`` via temp-file +
       atomic ``os.replace``.

    Atomicity guarantee
    -------------------
    The manifest rewrite is staged to a sibling temp file and renamed via
    ``os.replace`` (POSIX atomic rename) inside the same ``try`` block as
    the ``graph.yaml`` unlink.  An exception between the unlink and the
    replace leaves the manifest unchanged on disk; the in-memory mutation
    is not visible.  An exception inside the manifest write surfaces with
    both the previous manifest (untouched on disk) and the unlink already
    applied — operators MAY observe a missing ``graph.yaml`` plus an
    out-of-date manifest, but never a half-written manifest, never the
    forbidden ``built_in_only=True + graph.yaml present`` conflict state.

    Args:
        repo_root: Repository root containing ``.kittify/``.
        has_project_graph: True when synthesis emitted a project DRG; False
            when synthesis produced no project artifacts and the result is
            built-in-only.
    """
    import io  # noqa: PLC0415 — local import keeps module-level surface small
    import os  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    from .manifest import (  # noqa: PLC0415
        MANIFEST_PATH,
        SynthesisManifest,
        compute_manifest_hash,
        dump_yaml,
        load_yaml,
    )
    from .path_guard import PathGuard  # noqa: PLC0415

    manifest_path = repo_root / MANIFEST_PATH
    graph_path = repo_root / ".kittify" / "doctrine" / _GRAPH_FILENAME

    if not manifest_path.exists():
        # Synthesizer must have already written the manifest. Defensive: if
        # the caller invokes this before promote completes, do nothing.
        return

    manifest = load_yaml(manifest_path)
    desired_built_in_only = not has_project_graph

    # Fast path: nothing to mutate.
    if manifest.built_in_only == desired_built_in_only and not (
        desired_built_in_only and graph_path.exists()
    ):
        return

    # Build the post-condition manifest (immutable Pydantic model -> copy).
    manifest_hash = compute_manifest_hash(
        manifest.model_copy(
            update={
                "built_in_only": desired_built_in_only,
                "manifest_hash": "0" * 64,
            }
        )
    )
    new_manifest = SynthesisManifest(
        schema_version=manifest.schema_version,
        mission_id=manifest.mission_id,
        created_at=manifest.created_at,
        run_id=manifest.run_id,
        adapter_id=manifest.adapter_id,
        adapter_version=manifest.adapter_version,
        synthesizer_version=manifest.synthesizer_version,
        manifest_hash=manifest_hash,
        artifacts=list(manifest.artifacts),
        built_in_only=desired_built_in_only,
    )

    # All writes go through PathGuard (R-10). The tmp file is a sibling of
    # ``manifest_path`` (same ``.kittify/charter/`` directory, which is in
    # the default allowlist), so both the staging write and the atomic
    # ``replace`` are sanctioned.
    guard = PathGuard(repo_root=repo_root)
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=manifest_path.name + ".",
        suffix=".tmp",
        dir=str(manifest_path.parent),
    )
    os.close(fd)
    tmp_path = Path(tmp_path_str)

    try:
        from ruamel.yaml import YAML  # noqa: PLC0415

        yaml = YAML()
        yaml.default_flow_style = False
        data = new_manifest.model_dump(mode="python")
        # Serialise via an in-memory buffer so the on-disk write flows
        # through ``guard.write_text`` instead of a raw ``open(..., "w")``.
        buffer = io.StringIO()
        yaml.dump(data, buffer)
        guard.write_text(tmp_path, buffer.getvalue(), caller="project_drg.apply_post_condition")

        # Atomic mutations: delete stale graph and atomically replace the
        # manifest. POSIX guarantees the ``replace`` is atomic; if the
        # unlink succeeds but the replace fails the manifest is unchanged
        # on disk -- never half-written. The unlink stays IN PLACE within this
        # guarded sequence (FR-007); only the bare expression is consolidated
        # into the shared helper.
        if desired_built_in_only:
            from .graph_residue import unlink_stale_project_graph  # noqa: PLC0415

            unlink_stale_project_graph(graph_path.parent)
        guard.replace(tmp_path, manifest_path, caller="project_drg.apply_post_condition")
    except Exception:
        # Clean up the staged temp file on failure.
        import contextlib  # noqa: PLC0415

        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise

    # Keep dump_yaml available so callers can detect we've consumed it; the
    # explicit import above also ensures Pydantic validation runs on the
    # round-trip when load_yaml is later invoked by readers.
    _ = dump_yaml  # noqa: F841 — silence linter about unused import alias


def persist(
    graph: DRGGraph,
    staging_dir: Path,
    guard: PathGuard,
) -> None:
    """Serialize *graph* under the staged doctrine directory via *guard*.

    The promote step (WP03) will atomically move this file to the live project
    doctrine directory.

    Args:
        graph: The project overlay ``DRGGraph`` to write.
        staging_dir: Root of the staging area (must be within the PathGuard
            allowlist).
        guard: ``PathGuard`` instance that governs all writes.
    """
    doctrine_dir = staging_dir / "doctrine"
    guard.mkdir(doctrine_dir, caller="project_drg.persist")
    graph_path = doctrine_dir / _GRAPH_FILENAME
    guard.write_text(graph_path, _serialize_graph(graph), caller="project_drg.persist")


__all__ = ["apply_post_condition", "emit_project_layer", "persist"]
