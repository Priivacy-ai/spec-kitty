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
import re
from collections.abc import Callable, Mapping
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

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
from .synthesize_pipeline import ProvenanceEntry, canonical_yaml


# ---------------------------------------------------------------------------
# Filename helpers (data-model §E-2 "Filename rule")
# ---------------------------------------------------------------------------

_DIRECTIVE_NUM_RE = re.compile(r"[A-Z]+_(\d+)")


def _artifact_filename(kind: str, slug: str, artifact_id: str | None = None) -> str:
    """Return the repository-glob-matching filename for an artifact.

    - directive: ``<NNN>-<slug>.directive.yaml``
      where ``<NNN>`` is the numeric segment of ``artifact_id``
      (e.g. ``PROJECT_001`` → ``001``).
    - tactic:    ``<slug>.tactic.yaml``
    - styleguide: ``<slug>.styleguide.yaml``
    """
    if kind == "directive":
        nnn = "000"
        if artifact_id:
            m = _DIRECTIVE_NUM_RE.search(artifact_id)
            if m:
                nnn = m.group(1).zfill(3)
        return f"{nnn}-{slug}.directive.yaml"
    elif kind == "tactic":
        return f"{slug}.tactic.yaml"
    elif kind == "styleguide":
        return f"{slug}.styleguide.yaml"
    else:
        raise ValueError(f"Unknown artifact kind: {kind!r}")


def _doctrine_kind_subdir(kind: str) -> str:
    """Return the doctrine subdirectory name for a given artifact kind."""
    return {
        "directive": "directives",
        "tactic": "tactics",
        "styleguide": "styleguides",
    }[kind]


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
        artifact_id: str | None = None
        if kind == "directive":
            artifact_id = prov.artifact_urn.split(":", 1)[1]
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
        artifact_id: str | None = None
        if kind == "directive":
            # artifact_urn is "directive:<artifact_id>" for directives
            artifact_id = prov.artifact_urn.split(":", 1)[1]

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

            artifact_id_: str | None = None
            if kind == "directive":
                artifact_id_ = prov.artifact_urn.split(":", 1)[1]

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

    manifest = SynthesisManifest(
        mission_id=mission_id,
        created_at=datetime.now(tz=UTC).isoformat(),
        run_id=run_id,
        adapter_id=primary_adapter_id,
        adapter_version=primary_adapter_version,
        artifacts=sorted(manifest_entries, key=lambda e: (e.kind, e.slug)),
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


__all__ = ["promote", "_is_generic_scoped", "_run_neutrality_gate"]
