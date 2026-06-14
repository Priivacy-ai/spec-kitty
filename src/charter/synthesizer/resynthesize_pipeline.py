"""Bounded resynthesis pipeline — WP05 (T029).

Public entry point: ``run(request, adapter, topic) -> SynthesisManifest``

This module wraps the WP02 synthesis pipeline but scopes it to a single
structured topic selector (FR-011, FR-012).  It re-uses:
  - ``topic_resolver.resolve()``       — tier-1/2/3 selector resolution
  - ``synthesize_pipeline.run_all()``  — in-memory pipeline (WP02)
  - ``write_pipeline.promote()``       — staging/promote machinery (WP03)
  - ``manifest.load_yaml()``           — reads existing manifest (WP03)

Manifest rewrite semantics (FR-017):
  - Regenerated artifacts get fresh ``content_hash``, ``provenance_path``.
  - **Untouched artifacts** retain their prior ``content_hash`` and
    ``provenance_path`` unchanged.
  - A new ``run_id`` (ULID) is minted for the resynthesis run.
  - ``created_at`` is refreshed to the current UTC timestamp.

Zero-match (EC-4):
  If ``topic_resolver.resolve()`` returns a ``ResolvedTopic`` with an empty
  ``targets`` list (DRG-URN hit but no project artifact references it), this
  function returns the **current manifest unchanged** and emits a diagnostic
  result.  No writes occur; no model calls occur.

No-prior-manifest:
  If ``.kittify/charter/synthesis-manifest.yaml`` does not exist, a
  ``FileNotFoundError`` is raised immediately (before any model calls).

All filesystem writes go through ``PathGuard`` (FR-016).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doctrine.drg.loader import load_graph_or_dir
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode

from .artifact_naming import artifact_filename, doctrine_kind_subdir
from .manifest import (
    MANIFEST_PATH,
    ManifestArtifactEntry,
    SynthesisManifest,
    compute_manifest_hash,
    load_yaml as load_manifest,
)
from .request import SynthesisRequest, SynthesisTarget
from .synthesize_pipeline import ProvenanceEntry, _get_synthesizer_version, canonical_yaml
from .topic_resolver import ResolvedTopic, resolve as resolve_topic

_KITTIFY_DIRNAME = ".kittify"


# ---------------------------------------------------------------------------
# Manifest-rewrite helper (T029 option-b: owned here, not in write_pipeline)
# ---------------------------------------------------------------------------


def _new_ulid() -> str:
    """Generate a new ULID string (stdlib-only).

    Uses ``time.time_ns()`` for the 48-bit timestamp component and
    ``secrets.token_bytes(10)`` for the 80-bit randomness component.
    Encodes to the standard Crockford base-32 ULID alphabet.
    """
    import secrets
    import time

    # Crockford base-32 encoding alphabet
    _ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    ts_ms = time.time_ns() // 1_000_000  # 48-bit ms timestamp
    rand_bytes = secrets.token_bytes(10)  # 80-bit randomness

    # Encode 48-bit timestamp into 10 base-32 chars
    ts_part = ""
    v = ts_ms
    for _ in range(10):
        ts_part = _ALPHABET[v & 0x1F] + ts_part
        v >>= 5

    # Encode 80-bit random into 16 base-32 chars
    rand_int = int.from_bytes(rand_bytes, "big")
    rand_part = ""
    for _ in range(16):
        rand_part = _ALPHABET[rand_int & 0x1F] + rand_part
        rand_int >>= 5

    return ts_part + rand_part


def _rewrite_manifest(
    existing: SynthesisManifest,
    new_results: list[tuple[Mapping[str, Any], ProvenanceEntry]],
    run_id: str,
) -> SynthesisManifest:
    """Produce a new SynthesisManifest merging old entries with fresh ones.

    For each artifact in ``new_results``:
      - Compute a fresh ``content_hash`` and ``provenance_path``.
      - Replace (or insert) the corresponding entry in the manifest.

    For artifacts NOT in ``new_results``:
      - Retain the prior entry unchanged (prior ``content_hash``, etc.).

    Parameters
    ----------
    existing:
        The manifest loaded from disk before the resynthesis run.
    new_results:
        ``(body, ProvenanceEntry)`` tuples produced by the bounded pipeline.
    run_id:
        New ULID for this resynthesis run.

    Returns
    -------
    SynthesisManifest
        The merged manifest (not yet written to disk; caller does the write).
    """
    import hashlib
    from datetime import UTC, datetime

    # Build a key → new ManifestArtifactEntry dict for regenerated artifacts
    new_entries_by_key: dict[tuple[str, str], ManifestArtifactEntry] = {}
    new_adapter_ids: set[str] = set()
    new_adapter_versions: set[str] = set()

    for body, prov in new_results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug
        artifact_id: str | None = None
        if kind == "directive":
            artifact_id = prov.artifact_urn.split(":", 1)[1]

        filename = artifact_filename(kind, slug, artifact_id)
        yaml_bytes = canonical_yaml(body)
        content_hash = hashlib.sha256(yaml_bytes).hexdigest()  # noqa: TID251 - production raw SHA-256 owner

        rel_content = (
            f"{_KITTIFY_DIRNAME}/doctrine/{doctrine_kind_subdir(kind)}/{filename}"
        )
        rel_prov = f"{_KITTIFY_DIRNAME}/charter/provenance/{kind}-{slug}.yaml"

        new_entries_by_key[(kind, slug)] = ManifestArtifactEntry(
            kind=kind,
            slug=slug,
            path=rel_content,
            provenance_path=rel_prov,
            content_hash=content_hash,
        )
        new_adapter_ids.add(prov.adapter_id)
        new_adapter_versions.add(prov.adapter_version)

    # Merge: existing entries updated where regenerated, retained otherwise
    merged: list[ManifestArtifactEntry] = []
    existing_keys: set[tuple[str, str]] = set()
    for entry in existing.artifacts:
        key = (entry.kind, entry.slug)
        existing_keys.add(key)
        if key in new_entries_by_key:
            merged.append(new_entries_by_key[key])
        else:
            merged.append(entry)

    # Add genuinely new artifacts (not previously in the manifest)
    for raw_key, new_entry in new_entries_by_key.items():
        str_key: tuple[str, str] = (raw_key[0], raw_key[1])
        if str_key not in existing_keys:
            merged.append(new_entry)

    # Adapter identity (aggregate from new results; fall back to existing)
    if len(new_adapter_ids) == 1:
        primary_adapter_id = new_adapter_ids.pop()
        primary_adapter_version = new_adapter_versions.pop() if len(new_adapter_versions) == 1 else existing.adapter_version
    else:
        primary_adapter_id = existing.adapter_id
        primary_adapter_version = existing.adapter_version

    synthesizer_ver = _get_synthesizer_version()
    sorted_merged = sorted(merged, key=lambda e: (e.kind, e.slug))
    created_at = datetime.now(tz=UTC).isoformat()

    # Compute manifest_hash over all fields except manifest_hash itself.
    manifest_data_without_hash: dict[str, Any] = {
        "schema_version": "2",
        "mission_id": existing.mission_id,
        "created_at": created_at,
        "run_id": run_id,
        "adapter_id": primary_adapter_id,
        "adapter_version": primary_adapter_version,
        "synthesizer_version": synthesizer_ver,
        "artifacts": [e.model_dump(mode="python") for e in sorted_merged],
    }
    manifest_hash = compute_manifest_hash(manifest_data_without_hash)

    return SynthesisManifest(
        mission_id=existing.mission_id,
        created_at=created_at,
        run_id=run_id,
        adapter_id=primary_adapter_id,
        adapter_version=primary_adapter_version,
        synthesizer_version=synthesizer_ver,
        manifest_hash=manifest_hash,
        artifacts=sorted_merged,
    )


# ---------------------------------------------------------------------------
# Zero-match diagnostic result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResynthesisResult:
    """Result of a resynthesis run.

    Attributes
    ----------
    manifest:
        The (potentially updated) synthesis manifest.
    resolved_topic:
        The ``ResolvedTopic`` from the selector resolver.
    is_noop:
        ``True`` when EC-4 zero-match: DRG-URN resolved but no project-local
        artifact references it.  No writes occurred; no model calls occurred.
    diagnostic:
        Human-readable diagnostic message for no-op runs.
    """

    manifest: SynthesisManifest
    resolved_topic: ResolvedTopic
    is_noop: bool = False
    diagnostic: str = ""


# ---------------------------------------------------------------------------
# Bounded pipeline via full run_all + filter
# ---------------------------------------------------------------------------


def _run_bounded(
    request: SynthesisRequest,
    adapter: Any,
    target_slugs: frozenset[str],
) -> list[tuple[Mapping[str, Any], ProvenanceEntry]]:
    """Run the full synthesis pipeline and filter to only the bounded targets.

    Why this approach instead of calling adapter.generate() per target:
      The fixture adapter (and any deterministic adapter) computes a hash from
      the full ``SynthesisRequest`` envelope, including ``target.title``.  The
      title is not stored in provenance sidecars, so a target reconstructed
      from provenance would produce a different hash.  By running the full
      pipeline (which uses the original interview mapping to produce targets
      with their original titles) and filtering, we guarantee hash stability
      across synthesis and resynthesis runs.

    Parameters
    ----------
    request:
        The full SynthesisRequest with the original interview/doctrine/DRG
        snapshots.  ``request.target`` is a placeholder; actual targets come
        from the interview mapping inside ``run_all``.
    adapter:
        Adapter instance supporting ``generate()`` / ``generate_batch()``.
    target_slugs:
        Set of ``artifact_slug`` values to keep from the full pipeline output.
        All other targets are discarded (bounded contract).

    Returns
    -------
    list[tuple[Mapping, ProvenanceEntry]]
        One tuple per filtered target, in the order produced by ``run_all``.
    """
    from .synthesize_pipeline import run_all

    all_results = run_all(request, adapter=adapter)

    # Filter to only the slugs in the resolved target set
    return [
        (body, prov)
        for body, prov in all_results
        if prov.artifact_slug in target_slugs
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(
    request: SynthesisRequest,
    adapter: Any,
    topic: str,
    repo_root: Path | None = None,
    project_artifacts: Sequence[SynthesisTarget] | None = None,
    merged_drg: Mapping[str, Any] | None = None,
    interview_sections: Sequence[str] | None = None,
) -> ResynthesisResult:
    """Run the bounded resynthesis pipeline for a single topic selector.

    This function is the implementation of ``orchestrator.resynthesize()``.

    Flow:
        1. Load current manifest from ``.kittify/charter/synthesis-manifest.yaml``.
           If absent → raise ``FileNotFoundError``.
        2. Load all provenance sidecars → build lookup maps.
        3. Call ``topic_resolver.resolve(topic, ...)`` → ``ResolvedTopic``.
           Empty targets (EC-4) → return current manifest unchanged + diagnostic.
        4. Construct bounded ``SynthesisRequest`` objects for each target.
        5. Call ``synthesize_pipeline.run_all()`` → ``[(body, prov), ...]``.
        6. Build the authoritative merged manifest: regenerated entries get
           fresh hashes; untouched entries retain prior ``content_hash``
           (FR-017).
        7. Stage + promote bounded artifacts via WP03's
           ``write_pipeline.promote()``, passing the merged manifest so the
           manifest-last write is still the final commit marker.
        8. Return ``ResynthesisResult``.

    Parameters
    ----------
    request:
        The base ``SynthesisRequest`` providing interview/doctrine/DRG snapshots
        and the run context.  ``request.target`` is used as a sentinel; the
        actual target(s) are resolved from ``topic``.
    adapter:
        Adapter instance to use for generation.  Must support
        ``generate(SynthesisRequest)`` (and optionally ``generate_batch``).
    topic:
        Structured selector string (kind:slug | DRG URN | interview section).
    repo_root:
        Repository root path.  Defaults to ``Path.cwd()``.
    project_artifacts:
        Project-local SynthesisTarget objects for topic resolution.
        If None, loaded from provenance sidecars under
        ``.kittify/charter/provenance/``.
    merged_drg:
        The merged built-in+project DRG graph dict.  If None, loaded from
        ``.kittify/doctrine`` and the built-in DRG.
    interview_sections:
        Known interview section labels.  If None, inferred from
        ``request.interview_snapshot`` keys.

    Returns
    -------
    ResynthesisResult
        Contains the updated manifest, resolved topic, and no-op flag.

    Raises
    ------
    FileNotFoundError
        If no prior synthesis manifest exists.
    TopicSelectorUnresolvedError
        If ``topic`` cannot be resolved via any of the three tiers.
    """
    from . import write_pipeline as _write_pipeline  # noqa: PLC0415
    from .project_drg import emit_project_layer as _emit_project_layer  # noqa: PLC0415
    from .project_drg import persist as _persist_project_graph  # noqa: PLC0415
    from .staging import StagingDir as _StagingDir  # noqa: PLC0415
    from .validation_gate import validate as _validate_project_graph  # noqa: PLC0415
    from importlib.metadata import version as _pkg_version  # noqa: PLC0415
    _SPEC_KITTY_VERSION = _pkg_version("spec-kitty-cli")

    _repo_root = repo_root if repo_root is not None else Path.cwd()

    # ------------------------------------------------------------------
    # Step 1: Load existing manifest (fail-closed if absent)
    # ------------------------------------------------------------------
    manifest_path = _repo_root / MANIFEST_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No prior synthesis manifest found at '{manifest_path}'. "
            "Run 'spec-kitty charter synthesize' first to create a baseline, "
            "then use 'spec-kitty charter resynthesize --topic' for bounded updates."
        )
    existing_manifest = load_manifest(manifest_path)

    # ------------------------------------------------------------------
    # Step 2: Build provenance lookup maps
    # ------------------------------------------------------------------
    if project_artifacts is None:
        project_artifacts = _load_project_artifacts_from_provenance(_repo_root)

    if merged_drg is None:
        merged_drg = _load_merged_drg(_repo_root, request)

    if interview_sections is None:
        # Default: all top-level keys from the interview snapshot
        interview_sections = list(request.interview_snapshot.keys())

    # ------------------------------------------------------------------
    # Step 3: Resolve topic → ResolvedTopic
    # ------------------------------------------------------------------
    resolved = resolve_topic(
        raw=topic,
        project_artifacts=project_artifacts,
        merged_drg=merged_drg,
        interview_sections=interview_sections,
    )

    # EC-4 zero-match: no artifacts to regenerate — return unchanged manifest
    if not resolved.targets:
        return ResynthesisResult(
            manifest=existing_manifest,
            resolved_topic=resolved,
            is_noop=True,
            diagnostic=(
                f"Topic '{topic}' resolved to a DRG URN but no project-local "
                "artifacts reference it. No writes performed (EC-4)."
            ),
        )

    # ------------------------------------------------------------------
    # Step 4: Compute bounded target slugs + new run_id
    # ------------------------------------------------------------------
    run_id = _new_ulid()
    target_slugs = frozenset(t.slug for t in resolved.targets)

    # Construct a single full SynthesisRequest for the bounded pipeline.
    # We use request.target as a placeholder (run_all ignores it in favour
    # of the interview-mapping output); what matters is that the interview
    # snapshot, doctrine snapshot, and DRG snapshot match the original run.
    bounded_request = SynthesisRequest(
        target=request.target,  # placeholder — actual targets from interview mapping
        interview_snapshot=request.interview_snapshot,
        doctrine_snapshot=request.doctrine_snapshot,
        drg_snapshot=request.drg_snapshot,
        run_id=run_id,
        adapter_hints=request.adapter_hints,
        evidence=request.evidence,
    )

    # ------------------------------------------------------------------
    # Step 5: Run the full pipeline and filter to bounded targets
    # ------------------------------------------------------------------
    all_new_results = _run_bounded(bounded_request, adapter, target_slugs)

    # ------------------------------------------------------------------
    # Step 6: Build final merged manifest (FR-017: untouched entries retain
    # prior hash). It is passed into promote() so bounded resynthesis does not
    # write a temporary bounded-only manifest before the authoritative full
    # manifest.
    # ------------------------------------------------------------------
    new_manifest = _rewrite_manifest(existing_manifest, all_new_results, run_id)

    # ------------------------------------------------------------------
    # Step 7: Stage + promote bounded artifacts
    # ------------------------------------------------------------------
    built_in_drg = _built_in_drg_from_request(request)

    def _validation_callback(staged_dir: _StagingDir) -> None:
        updated_overlay = _emit_project_layer(
            targets=resolved.targets,
            spec_kitty_version=_SPEC_KITTY_VERSION,
            built_in_drg=built_in_drg,
        )
        existing_graph_dir = _repo_root / _KITTIFY_DIRNAME / "doctrine"
        project_graph = updated_overlay
        if existing_graph_dir.exists():
            project_graph = _merge_project_overlay(
                existing_overlay=load_graph_or_dir(existing_graph_dir),
                updated_overlay=updated_overlay,
            )
        _persist_project_graph(project_graph, staged_dir.root, staged_dir.guard)
        _validate_project_graph(staged_dir.root, built_in_drg)

    with _StagingDir.create(_repo_root, run_id) as staging_dir:
        written_manifest = _write_pipeline.promote(
            bounded_request,
            staging_dir,
            all_new_results,
            _validation_callback,
            repo_root=_repo_root,
            manifest_override=new_manifest,
        )

    # ------------------------------------------------------------------
    # Step 8: Return result
    # ------------------------------------------------------------------
    return ResynthesisResult(
        manifest=written_manifest,
        resolved_topic=resolved,
        is_noop=False,
        diagnostic="",
    )


# ---------------------------------------------------------------------------
# Internal helpers for loading project state
# ---------------------------------------------------------------------------


def _load_project_artifacts_from_provenance(
    repo_root: Path,
) -> list[SynthesisTarget]:
    """Load all project-local SynthesisTarget objects from provenance sidecars.

    Reads every ``.kittify/charter/provenance/*.yaml`` file and reconstructs
    a ``SynthesisTarget`` for each provenance entry.

    Returns an empty list if the provenance directory does not exist.
    """
    from .provenance import load_yaml as load_provenance  # noqa: PLC0415

    prov_dir = repo_root / _KITTIFY_DIRNAME / "charter" / "provenance"
    if not prov_dir.exists():
        return []

    graph_labels = _load_project_graph_labels(repo_root)
    targets: list[SynthesisTarget] = []
    for prov_file in sorted(prov_dir.glob("*.yaml")):
        try:
            prov = load_provenance(prov_file)
            artifact_id = prov.artifact_urn.split(":", 1)[1]
            artifact_urn = f"{prov.artifact_kind}:{artifact_id}"
            # Reconstruct a minimal SynthesisTarget from provenance data
            # (title is not stored in provenance; prefer the existing graph
            # label so bounded no-op resynthesis does not churn graph.yaml)
            target = SynthesisTarget(
                kind=prov.artifact_kind,
                slug=prov.artifact_slug,
                title=graph_labels.get(
                    artifact_urn,
                    prov.artifact_slug.replace("-", " ").title(),
                ),
                artifact_id=artifact_id,
                source_section=prov.source_section,
                source_urns=tuple(prov.source_urns),
            )
            targets.append(target)
        except Exception:  # noqa: BLE001, S112
            continue  # Skip malformed provenance files

    return targets


def _load_project_graph_labels(repo_root: Path) -> dict[str, str]:
    """Return existing project graph labels keyed by URN, best-effort."""
    project_graph_dir = repo_root / _KITTIFY_DIRNAME / "doctrine"
    if not project_graph_dir.exists():
        return {}
    try:
        graph = load_graph_or_dir(project_graph_dir)
    except Exception:  # noqa: BLE001
        return {}
    return {
        node.urn: node.label
        for node in graph.nodes
        if node.label is not None
    }


def _load_merged_drg(
    repo_root: Path,
    request: SynthesisRequest,
) -> Mapping[str, Any]:
    """Load the merged DRG graph: project overlay + built-in DRG snapshot.

    Falls back to ``request.drg_snapshot`` if no project graph file exists.
    """
    project_graph_dir = repo_root / _KITTIFY_DIRNAME / "doctrine"
    if not project_graph_dir.exists():
        return request.drg_snapshot

    try:
        project_graph_model = load_graph_or_dir(project_graph_dir)
    except Exception:  # noqa: BLE001
        return request.drg_snapshot
    project_graph = project_graph_model.model_dump(mode="json")

    # Merge: combine nodes from both graphs (project overlay + built-in snapshot)
    built_in_nodes = list(request.drg_snapshot.get("nodes", []))
    project_nodes = list(project_graph.get("nodes", []))
    built_in_edges = list(request.drg_snapshot.get("edges", []))
    project_edges = list(project_graph.get("edges", []))

    return {
        "nodes": built_in_nodes + project_nodes,
        "edges": built_in_edges + project_edges,
        "schema_version": project_graph.get("schema_version", "1"),
    }


def _built_in_drg_from_request(request: SynthesisRequest) -> DRGGraph:
    """Build the built-in-layer DRGGraph from the request snapshot."""
    snapshot = dict(request.drg_snapshot)
    snapshot.setdefault("nodes", [])
    snapshot.setdefault("edges", [])
    snapshot["schema_version"] = "1.0"
    snapshot.setdefault("generated_at", "1970-01-01T00:00:00+00:00")
    snapshot.setdefault("generated_by", "request.drg_snapshot")
    return DRGGraph.model_validate(snapshot)


def _merge_project_overlay(
    existing_overlay: DRGGraph,
    updated_overlay: DRGGraph,
) -> DRGGraph:
    """Replace only the resynthesized nodes/edges inside an existing overlay."""
    updated_urns = {node.urn for node in updated_overlay.nodes}
    updated_nodes_by_urn = {node.urn: node for node in updated_overlay.nodes}
    merged_nodes: list[DRGNode] = []
    for node in existing_overlay.nodes:
        replacement = updated_nodes_by_urn.pop(node.urn, None)
        merged_nodes.append(replacement if replacement is not None else node)
    merged_nodes.extend(updated_nodes_by_urn.values())

    updated_edges_by_source: dict[str, list[DRGEdge]] = {}
    for edge in updated_overlay.edges:
        updated_edges_by_source.setdefault(edge.source, []).append(edge)

    merged_edges: list[DRGEdge] = []
    inserted_sources: set[str] = set()
    for edge in existing_overlay.edges:
        if edge.source not in updated_urns:
            merged_edges.append(edge)
            continue
        if edge.source in inserted_sources:
            continue
        merged_edges.extend(updated_edges_by_source.get(edge.source, []))
        inserted_sources.add(edge.source)

    for source, edges in updated_edges_by_source.items():
        if source not in inserted_sources:
            merged_edges.extend(edges)

    return DRGGraph(
        schema_version=updated_overlay.schema_version,
        generated_at=updated_overlay.generated_at,
        generated_by=updated_overlay.generated_by,
        nodes=merged_nodes,
        edges=merged_edges,
    )


__all__ = [
    "ResynthesisResult",
    "run",
]
