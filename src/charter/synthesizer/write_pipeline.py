"""Stage-and-promote write pipeline — WP03 (T018).

Public entry point: ``promote(request, staging_dir, results, validation_callback)``

This module implements KD-2 (atomicity model):

    stage → validate → ordered-os.replace → manifest-last → wipe

Authority rule (KD-2): the live tree is authoritative IFF the synthesis
manifest (``.kittify/charter/synthesis-manifest.yaml``) is present AND all
listed ``content_hash`` values match on-disk artifact bytes.  A partial
promote (crash between promote start and manifest write) leaves the live tree
in an authored-but-no-manifest state → readers treat it as partial-and-
rerunable.

Step ordering (enforced by this module):
    1. Write every (body, provenance) pair into the staged subtrees.
    2. Call ``validation_callback(staging_dir)`` — raises → abort to .failed/.
    3. Ordered ``os.replace`` (via PathGuard) into final live trees.
    4. Write manifest last (the sole mutation after content os.replace calls).
    5. ``staging_dir.wipe()``.
    6. Return the manifest.

On any exception between step 3 and step 4 the staging dir is NOT wiped —
the ``StagingDir`` context manager in the caller routes it to ``.failed/``.

All filesystem writes go through ``PathGuard`` (FR-016).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from .artifact_naming import artifact_filename, doctrine_kind_subdir
from .errors import NeutralityGateViolation, StagingPromoteError
from .evidence import EvidenceBundle
from .manifest import (
    MANIFEST_PATH,
    ManifestArtifactEntry,
    SynthesisManifest,
    dump_yaml as dump_manifest,
)
from .provenance import dump_yaml as dump_provenance, provenance_path_for
from .request import SynthesisRequest
from .staging import StagingDir
from .synthesize_pipeline import ProvenanceEntry, _get_synthesizer_version, canonical_yaml


# ---------------------------------------------------------------------------
# Typed staged-artifact entry (WP02 — Charter Contract Cleanup Tranche 1)
# ---------------------------------------------------------------------------
#
# ``StagedArtifact`` is the typed entry returned by ``compute_written_artifacts``
# below. It is the single source of truth for the ``written_artifacts`` array
# emitted by ``charter synthesize --json`` (FR-003), and powers the byte-equal
# dry-run / non-dry-run path-parity guarantee (FR-004).
#
# Shape mirrors the ``WrittenArtifact`` contract from
# ``contracts/synthesis-envelope.schema.json``:
#
#   * ``path``        — repo-relative POSIX path that the live tree will (or
#                       did) carry. Computed from the same helpers
#                       ``promote()`` uses below — see ``_artifact_filename``
#                       and ``_doctrine_kind_subdir`` — so dry-run and
#                       non-dry-run agree byte-for-byte.
#   * ``kind``        — doctrine kind (``directive`` / ``tactic`` / ``styleguide``)
#                       lifted directly from ``ProvenanceEntry.artifact_kind``.
#   * ``slug``        — slug component lifted from ``ProvenanceEntry.artifact_slug``.
#   * ``artifact_id`` — concrete artifact identifier extracted from
#                       ``ProvenanceEntry.artifact_urn``. ``None`` for kinds
#                       that do not carry a URN-encoded id (tactic, styleguide).
#                       The CLI surface MUST NOT expose the placeholder
#                       ``PROJECT_000``; it is rejected here as well so a
#                       missing-provenance regression cannot silently leak.
#
# The dataclass is frozen so callers cannot mutate provenance after the fact.
# Adding fields here is safe (additive); removing/renaming would break the
# CLI envelope shape and is out of scope.


@dataclass(frozen=True)
class StagedArtifact:
    """Typed provenance entry for a single staged-or-promoted doctrine artifact.

    Sourced from ``(body, ProvenanceEntry)`` results returned by
    ``synthesize_pipeline.run_all``; never reconstructed from ``kind:slug``
    selectors. Used by both dry-run and non-dry-run code paths so that
    ``written_artifacts[*].path`` is byte-equal across the two modes
    (FR-004).
    """

    path: str
    """Repo-relative POSIX path (e.g. ``.kittify/doctrine/directives/001-foo.directive.yaml``)."""

    kind: str
    """Doctrine kind: ``directive`` | ``tactic`` | ``styleguide``."""

    slug: str
    """Slug component used in the artifact filename."""

    artifact_id: str | None
    """Concrete artifact identifier (e.g. ``PROJECT_001``) or ``None``."""


def _artifact_id_from_provenance(prov: ProvenanceEntry) -> str | None:
    """Lift the concrete artifact_id from a ``ProvenanceEntry``.

    ``stage_and_validate``, ``promote``, and dry-run envelope projection all
    call this helper so malformed directive provenance cannot silently fall
    back to a ``000`` path. Returns ``None`` for kinds that do not carry a
    URN-encoded id (tactic, styleguide).
    """
    if prov.artifact_kind != "directive":
        return None
    prefix, separator, artifact_id = prov.artifact_urn.partition(":")
    if prefix != "directive" or separator != ":" or not artifact_id:
        raise ValueError(
            "Directive provenance must carry artifact_urn='directive:<artifact_id>'"
        )
    if artifact_id == "PROJECT_000":
        raise ValueError("Directive provenance must not surface PROJECT_000")
    return artifact_id


def compute_written_artifacts(
    results: list[tuple[Mapping[str, Any], ProvenanceEntry]],
    repo_root: Path,
) -> list[StagedArtifact]:
    """Project ``(body, ProvenanceEntry)`` results into typed staged-artifact entries.

    Pure function (no I/O). Uses the same path computation as ``promote()`` so
    a dry-run and a real-run produce byte-equal ``path`` values (FR-004).

    Parameters
    ----------
    results:
        The output of ``synthesize_pipeline.run_all``.
    repo_root:
        Project root used to resolve repo-relative paths (POSIX style).

    Returns
    -------
    list[StagedArtifact]
        One entry per result, in the order ``run_all`` produced them. Empty
        list when there are no results.
    """
    entries: list[StagedArtifact] = []
    for _body, prov in results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug
        artifact_id = _artifact_id_from_provenance(prov)
        filename = artifact_filename(kind, slug, artifact_id)
        live_path = (
            repo_root
            / ".kittify"
            / "doctrine"
            / doctrine_kind_subdir(kind)
            / filename
        )
        rel_path = live_path.relative_to(repo_root).as_posix()
        entries.append(
            StagedArtifact(
                path=rel_path,
                kind=kind,
                slug=slug,
                artifact_id=artifact_id,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Filename helpers (data-model §E-2 "Filename rule")
# ---------------------------------------------------------------------------


def _artifact_filename(kind: str, slug: str, artifact_id: str | None = None) -> str:
    """Return the repository-glob-matching filename for an artifact.

    - directive: ``<NNN>-<slug>.directive.yaml``
      where ``<NNN>`` is the numeric segment of ``artifact_id``
      (e.g. ``PROJECT_001`` → ``001``).
    - tactic:    ``<slug>.tactic.yaml``
    - styleguide: ``<slug>.styleguide.yaml``
    """
    return artifact_filename(kind, slug, artifact_id)


def _doctrine_kind_subdir(kind: str) -> str:
    """Return the doctrine subdirectory name for a given artifact kind."""
    return doctrine_kind_subdir(kind)


def _compute_content_hash(yaml_bytes: bytes) -> str:
    """SHA-256 hex digest of artifact YAML bytes (matches synthesize_pipeline)."""
    return hashlib.sha256(yaml_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Neutrality gate helpers
# ---------------------------------------------------------------------------


def _is_generic_scoped(
    target_kind: str,  # noqa: ARG001 — reserved for future kind-level rules
    target_slug: str,
    evidence: EvidenceBundle | None,
) -> bool:
    """Return True if this artifact slot should be checked for language-specific bias.

    An artifact is generic-scoped when there is no code-signals scope_tag
    or when the artifact slug does not contain the scope_tag as a component.
    Conservative default: if evidence is absent, all artifacts are generic-scoped.

    Scope determination rules:
    - No evidence / no code_signals → generic (lint it)
    - scope_tag == "unknown" → generic (lint it)
    - scope_tag IS a substring of slug → language-scoped (skip lint)
    - scope_tag NOT in slug → generic (lint it)

    Example: scope_tag="python", slug="python-style-guide" → language-scoped (False)
    Example: scope_tag="python", slug="testing-philosophy" → generic (True)
    """
    if evidence is None or evidence.code_signals is None:
        return True  # no scope info → assume generic, apply lint

    scope_tag = evidence.code_signals.scope_tag
    if scope_tag == "unknown":
        return True

    # A language-scoped artifact slug typically contains the scope_tag as a component.
    # e.g. "python-style-guide" contains "python"; "testing-philosophy" does not.
    return scope_tag not in target_slug


def _run_neutrality_gate(
    staging_dir: StagingDir,
    results: list[tuple[Any, ProvenanceEntry]],
    evidence: EvidenceBundle | None,
) -> None:
    """Scan generic-scoped staged artifacts for language bias.

    Iterates over all (body, provenance) results. For each artifact that is
    generic-scoped (per ``_is_generic_scoped``), runs ``run_neutrality_lint``
    on the staged content file. If any banned term is found, raises
    ``NeutralityGateViolation`` immediately without promoting.

    The staging directory is NOT wiped on gate failure — the caller's context
    manager routes it to ``.failed/`` for operator inspection (KD-2, FR-011).

    Parameters
    ----------
    staging_dir:
        The active staging directory (pre-promote state).
    results:
        All ``(body, ProvenanceEntry)`` pairs from ``run_all()``.
    evidence:
        EvidenceBundle from the synthesis request, used to determine scope_tag.
    """
    from charter.neutrality.lint import run_neutrality_lint

    for _body, prov in results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug

        if not _is_generic_scoped(kind, slug, evidence):
            # Language-scoped artifact — language-specific terms are expected here.
            continue

        # Determine the staged content path for this specific artifact.
        # The artifact_id is embedded in the URN for directives.
        artifact_id = _artifact_id_from_provenance(prov)
        filename = _artifact_filename(kind, slug, artifact_id)
        staged_path = staging_dir.path_for_content(kind, filename)

        if not staged_path.exists():
            # Staged file missing — skip (shouldn't happen in normal flow).
            continue

        # Scan only this specific staged file, treating the staging root as repo_root
        # so that _repo_relative_string produces stable paths.
        lint_result = run_neutrality_lint(
            repo_root=staging_dir.root,
            scan_roots=[staged_path],
        )

        # Gate only on actual banned-term hits — not on stale allowlist entries.
        # Stale entries are expected when scanning staged files against the default
        # allowlist (which references repo-relative paths that don't exist in staging).
        if lint_result.hits:
            # Collect up to 5 hit matches for the error message.
            terms = tuple(hit.match for hit in lint_result.hits[:5])
            raise NeutralityGateViolation(
                artifact_urn=prov.artifact_urn,
                detected_terms=terms,
                staging_dir=staging_dir.root,
            )


def stage_and_validate(
    request: SynthesisRequest,
    staging_dir: StagingDir,
    results: list[tuple[Mapping[str, Any], ProvenanceEntry]],
    validation_callback: Callable[[StagingDir], None],
) -> list[str]:
    """Write staged files and run the full pre-promote validation stack.

    This is the truthful implementation for CLI ``--dry-run``: all artifact
    bodies and provenance sidecars are materialized in the staging tree, the
    project DRG overlay is emitted via ``validation_callback``, and the
    neutrality gate scans the exact staged bytes that a real promote would use.

    No live-tree ``os.replace`` calls occur here.

    Returns
    -------
    list[str]
        Stable ``kind:slug`` selectors for the staged artifact set.
    """
    staged_artifacts: list[str] = []

    for body, prov in results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug
        artifact_id = _artifact_id_from_provenance(prov)

        filename = _artifact_filename(kind, slug, artifact_id)
        yaml_bytes = canonical_yaml(body)

        staged_content_path = staging_dir.path_for_content(kind, filename)
        staging_dir.guard.write_bytes(
            staged_content_path,
            yaml_bytes,
            caller="write_pipeline.stage_and_validate[content]",
        )

        staged_prov_path = staging_dir.path_for_provenance(kind, slug)
        dump_provenance(prov, staged_prov_path, staging_dir.guard)
        staged_artifacts.append(f"{kind}:{slug}")

    validation_callback(staging_dir)
    _run_neutrality_gate(staging_dir, results, request.evidence)
    return staged_artifacts


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def promote(
    request: SynthesisRequest,
    staging_dir: StagingDir,
    results: list[tuple[Mapping[str, Any], ProvenanceEntry]],
    validation_callback: Callable[[StagingDir], None],
    repo_root: Path | None = None,
    mission_id: str | None = None,
) -> SynthesisManifest:
    """Execute the full stage-and-promote pipeline for a synthesis run.

    Parameters
    ----------
    request:
        The ``SynthesisRequest`` envelope (for ``run_id`` and adapter info).
    staging_dir:
        Pre-created staging directory (see ``StagingDir.create``).
    results:
        List of ``(body, ProvenanceEntry)`` tuples from ``run_all()``.
    validation_callback:
        Callable invoked with the staged tree *before* promote.  WP04 wires
        its DRG + schema validation gate here.  A raised exception aborts and
        routes to ``staging_dir.commit_to_failed()``.
    repo_root:
        Repository root path.  Defaults to the grandparent of the staging
        dir's root (inferred from ``staging_dir.root``).
    mission_id:
        Optional ULID to record in the manifest for audit purposes.

    Returns
    -------
    SynthesisManifest
        The written manifest (manifest-last commit marker).

    Raises
    ------
    StagingPromoteError
        If any ``os.replace`` call or the manifest write fails.
    """
    if repo_root is None:
        # staging_dir.root == .kittify/charter/.staging/<run_id>
        # → repo_root == staging_dir.root.parent.parent.parent.parent
        repo_root = staging_dir.root.parent.parent.parent.parent

    guard = staging_dir.guard
    run_id = staging_dir.run_id

    # ------------------------------------------------------------------
    # Step 1: write every (body, provenance) pair into the staged subtrees
    # ------------------------------------------------------------------
    staged_items: list[tuple[str, str, str, str, bytes]] = []
    # Each item: (kind, slug, artifact_filename, artifact_id, yaml_bytes)

    for body, prov in results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug

        # Infer artifact_id from the provenance URN for directive filename
        artifact_id = _artifact_id_from_provenance(prov)

        filename = _artifact_filename(kind, slug, artifact_id)
        yaml_bytes = canonical_yaml(body)

        # Write content into staged doctrine tree
        staged_content_path = staging_dir.path_for_content(kind, filename)
        guard.write_bytes(staged_content_path, yaml_bytes, caller="write_pipeline.promote[content]")

        # Write provenance sidecar into staged charter tree
        staged_prov_path = staging_dir.path_for_provenance(kind, slug)
        dump_provenance(prov, staged_prov_path, guard)

        staged_items.append((kind, slug, filename, artifact_id or slug, yaml_bytes))

    # ------------------------------------------------------------------
    # Step 2: validation callback (WP04 wires DRG + schema validation here)
    # ------------------------------------------------------------------
    try:
        validation_callback(staging_dir)
    except Exception as exc:
        staging_dir.commit_to_failed(f"Validation failed: {exc}")
        raise

    # ------------------------------------------------------------------
    # Step 2b: neutrality lint gate (FR-011, FR-012)
    #
    # Runs AFTER validation and BEFORE the first os.replace call.
    # Scans generic-scoped staged artifacts for language-specific bias.
    # On NeutralityGateViolation the staging dir is NOT wiped — the
    # StagingDir context manager in the caller routes it to .failed/.
    # ------------------------------------------------------------------
    _run_neutrality_gate(staging_dir, results, request.evidence)

    # ------------------------------------------------------------------
    # Step 3: ordered os.replace into final live trees
    # ------------------------------------------------------------------
    # Ensure destination directories exist.
    for kind_subdir in ("directives", "tactics", "styleguides"):
        guard.mkdir(
            repo_root / ".kittify" / "doctrine" / kind_subdir,
            caller="write_pipeline.promote[mkdir-doctrine]",
        )

    guard.mkdir(
        repo_root / ".kittify" / "charter" / "provenance",
        caller="write_pipeline.promote[mkdir-provenance]",
    )

    try:
        manifest_entries: list[ManifestArtifactEntry] = []

        for body, prov in results:
            kind = prov.artifact_kind
            slug = prov.artifact_slug

            artifact_id_ = _artifact_id_from_provenance(prov)

            filename = _artifact_filename(kind, slug, artifact_id_)
            yaml_bytes = canonical_yaml(body)
            content_hash = _compute_content_hash(yaml_bytes)

            # Content: staging → .kittify/doctrine/<kind-subdir>/<filename>
            staged_content = staging_dir.path_for_content(kind, filename)
            live_content = repo_root / ".kittify" / "doctrine" / _doctrine_kind_subdir(kind) / filename
            guard.replace(staged_content, live_content, caller="write_pipeline.promote[content-replace]")

            # Provenance: staging → .kittify/charter/provenance/<kind>-<slug>.yaml
            staged_prov = staging_dir.path_for_provenance(kind, slug)
            live_prov = repo_root / ".kittify" / "charter" / "provenance" / f"{kind}-{slug}.yaml"
            guard.replace(staged_prov, live_prov, caller="write_pipeline.promote[prov-replace]")

            rel_content = str(live_content.relative_to(repo_root))
            rel_prov = provenance_path_for(kind, slug)

            manifest_entries.append(
                ManifestArtifactEntry(
                    kind=kind,
                    slug=slug,
                    path=rel_content,
                    provenance_path=rel_prov,
                    content_hash=content_hash,
                )
            )

        # Check for a staged DRG overlay graph and promote it
        staged_graph = staging_dir.root / "doctrine" / "graph.yaml"
        if staged_graph.exists():
            live_graph = repo_root / ".kittify" / "doctrine" / "graph.yaml"
            guard.replace(staged_graph, live_graph, caller="write_pipeline.promote[graph-replace]")

    except Exception as exc:
        # Do NOT wipe staging — let the caller (StagingDir context manager) route
        # to .failed/.  Manifest has NOT been written → partial-and-rerunable state.
        raise StagingPromoteError(
            run_id=run_id,
            staging_dir=str(staging_dir.root),
            cause=str(exc),
        ) from exc

    # ------------------------------------------------------------------
    # Step 4: manifest last — the authoritative commit marker (KD-2)
    # ------------------------------------------------------------------
    # Determine primary adapter id/version (aggregate from provenance).
    adapter_ids = {prov.adapter_id for _, prov in results}
    adapter_versions = {prov.adapter_version for _, prov in results}
    primary_adapter_id = adapter_ids.pop() if len(adapter_ids) == 1 else ""
    primary_adapter_version = adapter_versions.pop() if len(adapter_versions) == 1 else ""

    synthesizer_ver = _get_synthesizer_version()
    sorted_artifacts = sorted(manifest_entries, key=lambda e: (e.kind, e.slug))

    # Build the manifest data dict without manifest_hash first, then hash it.
    # canonical_yaml() returns bytes — do NOT call .encode() on its result.
    manifest_data_without_hash: dict[str, Any] = {
        "schema_version": "2",
        "mission_id": mission_id,
        "created_at": datetime.now(tz=UTC).isoformat(),
        "run_id": run_id,
        "adapter_id": primary_adapter_id,
        "adapter_version": primary_adapter_version,
        "synthesizer_version": synthesizer_ver,
        "artifacts": [e.model_dump(mode="python") for e in sorted_artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(manifest_data_without_hash)).hexdigest()

    manifest = SynthesisManifest(
        mission_id=mission_id,
        created_at=manifest_data_without_hash["created_at"],
        run_id=run_id,
        adapter_id=primary_adapter_id,
        adapter_version=primary_adapter_version,
        synthesizer_version=synthesizer_ver,
        manifest_hash=manifest_hash,
        artifacts=sorted_artifacts,
    )

    try:
        manifest_path = repo_root / MANIFEST_PATH
        guard.mkdir(manifest_path.parent, caller="write_pipeline.promote[mkdir-manifest]")
        dump_manifest(manifest, manifest_path, guard)
    except Exception as exc:
        # Manifest write failed — staging NOT wiped; partial state preserved.
        raise StagingPromoteError(
            run_id=run_id,
            staging_dir=str(staging_dir.root),
            cause=f"manifest write failed: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # Step 5: wipe staging dir (only on full success)
    # ------------------------------------------------------------------
    staging_dir.wipe()

    # ------------------------------------------------------------------
    # Step 6: return manifest
    # ------------------------------------------------------------------
    return manifest


__all__ = [
    "promote",
    "stage_and_validate",
    "compute_written_artifacts",
    "StagedArtifact",
    "_is_generic_scoped",
    "_run_neutrality_gate",
]
