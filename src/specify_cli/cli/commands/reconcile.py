"""``spec-kitty reconcile`` — CLI surface + stable library API for the reconciler.

This module is WP04: it exposes the pure WP03
:class:`~specify_cli.dossier.reconciler.DossierReconciler` as

  (a) a supported CLI operation — ``spec-kitty reconcile --mission <slug>`` —
      that exits ``0`` on proven PARITY and non-zero on DIVERGENCE/ERROR,
      NAMING the differing artifact(s) so CI/automation can gate on it
      (FR-007, NFR-004), with a ``--json`` machine surface; and

  (b) a narrow, stable library API — :func:`reconcile_mission_dossier` — that
      import-history (spec-kitty#2262) binds to in order to gate materialization
      on a *contract* (the WP03 :class:`ReconciliationResult`), never on
      reconciler internals.

Authority boundary (C-001): the hash + compare logic lives in WP01
(:func:`compute_dossier_snapshot_hash`) and WP03 (``DossierReconciler``). This
module only *wraps* them — it rebuilds the source projection by indexing the
mission directory on disk, loads the recorded snapshot, and hands both
projections to the reconciler. It never re-implements hashing or comparison.

Fail-closed (C-005, FR-006): every I/O precondition failure (no project root,
mission dir absent, no recorded snapshot, indexing error) is surfaced as an
explicit ERROR :class:`ReconciliationResult` — a value whose truthiness is
``False`` — never a raised exception into the gate and never a default parity.

The re-exports below (:class:`ReconciliationResult`,
:class:`ReconciliationStatus`, :class:`ArtifactDivergence`) let #2262 import the
whole gating contract from this one module.

See: kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md (FR-007, NFR-002).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from specify_cli.cli.console import console
from specify_cli.core.paths import locate_project_root
from specify_cli.dossier.reconciler import (
    ArtifactDivergence,
    DossierReconciler,
    ReconciliationResult,
    ReconciliationStatus,
)
from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission

# The stable public surface #2262 consumes from this module. Keeping the WP03
# result types re-exported here means the consumer binds to ONE import site.
#
# `reconcile_mission_dossier` is the library entrypoint #2262 will call. It is
# defined and importable now, but deliberately NOT listed in __all__ yet: the
# dead-symbol arch gate requires every __all__ symbol to have a cross-module
# importer, and its only consumer (#2262) does not exist in-tree yet. #2262
# adds it back to __all__ when it wires the gate. Import it directly until then:
#     from specify_cli.cli.commands.reconcile import reconcile_mission_dossier
__all__ = [
    "reconcile",
    "ReconciliationResult",
    "ReconciliationStatus",
    "ArtifactDivergence",
]

# Exit codes — divergence and error MUST be non-zero so CI/automation can gate.
_EXIT_PARITY = 0
_EXIT_DIVERGENCE = 1
_EXIT_ERROR = 2

# The dossier pipeline's own default (see sync/dossier_pipeline.py); mission_type
# only affects manifest-driven *missing* detection, never a present artifact's
# content hash — and the projection below is present-only, so this default is
# safe for the parity comparison regardless of the mission's real type.
_DEFAULT_MISSION_TYPE = "software-dev"


def _present_projection(artifacts: object) -> list[tuple[str, str | None]]:
    """Project present artifacts to canonical ``(path, content_hash)`` entries.

    Present-only, so both the freshly-rebuilt source and the recorded snapshot
    are projected symmetrically (an added/removed file surfaces as a NAMED
    divergence, a byte change as a content mismatch). This is the exact input
    shape WP01's canonical hash consumes.
    """
    entries: list[tuple[str, str | None]] = []
    for artifact in artifacts:  # type: ignore[attr-defined]
        if getattr(artifact, "is_present", False):
            entries.append((artifact.relative_path, artifact.content_hash_sha256))
    return entries


def reconcile_mission_dossier(
    mission_slug: str,
    *,
    repo_root: Path | None = None,
    mission_type: str = _DEFAULT_MISSION_TYPE,
    reconciler: DossierReconciler | None = None,
) -> ReconciliationResult:
    """Rebuild a mission dossier from source and reconcile it against the record.

    This is the **stable library API** import-history (spec-kitty#2262) gates
    materialization on (FR-007). It is intentionally narrow: it returns the WP03
    :class:`ReconciliationResult` and nothing else, so the consumer depends on a
    contract rather than on reconciler internals.

    Behaviour:
      - Rebuild the *source* projection by indexing the mission directory
        (present artifacts, content-addressed via WP01's hashing).
      - Load the *recorded* snapshot and project its present artifacts.
      - Hand both projections to the WP03 reconciler (C-001: it owns the hash +
        compare) and return its structured result.

    Fail-closed (C-005, FR-006): a missing project root / mission directory /
    recorded snapshot, or any indexing failure, returns an ERROR result (falsy
    truthiness) — never a raised exception and never a default parity.

    Args:
        mission_slug: The mission whose dossier is reconciled.
        repo_root: Project root; resolved via :func:`locate_project_root` when
            omitted.
        mission_type: Mission type used for indexing (default matches the sync
            dossier pipeline). Does not affect the present-only parity input.
        reconciler: Optional :class:`DossierReconciler` (defaults to a fresh one
            over WP01's canonical hash) — injectable purely for testing.

    Returns:
        A WP03 :class:`ReconciliationResult` (PARITY / DIVERGENCE / ERROR).
    """
    reconciler = reconciler or DossierReconciler()

    root = repo_root or locate_project_root()
    if root is None:
        return ReconciliationResult(
            status=ReconciliationStatus.ERROR,
            error="not in a spec-kitty project (no project root resolved)",
        )

    feature_dir = candidate_feature_dir_for_mission(root, mission_slug)
    if not feature_dir.exists():
        return ReconciliationResult(
            status=ReconciliationStatus.ERROR,
            error=f"mission dossier not found: {mission_slug}",
        )

    # Load the recorded snapshot FIRST: with no record there is nothing to
    # reconcile against, and fabricating a pass would violate fail-closed.
    try:
        from specify_cli.dossier.snapshot import load_snapshot

        recorded_snapshot = load_snapshot(feature_dir, mission_slug)
    except Exception as exc:  # noqa: BLE001 - fail-closed: any load failure is an ERROR
        return ReconciliationResult(
            status=ReconciliationStatus.ERROR,
            error=f"could not load recorded snapshot for {mission_slug}: {exc}",
        )
    if recorded_snapshot is None:
        return ReconciliationResult(
            status=ReconciliationStatus.ERROR,
            error=f"no recorded snapshot to reconcile against for {mission_slug}",
        )

    # Rebuild the source projection from disk (FR-004, via WP01-hashed indexing).
    try:
        from specify_cli.dossier.indexer import Indexer
        from specify_cli.dossier.manifest import ManifestRegistry

        dossier = Indexer(ManifestRegistry()).index_feature(feature_dir, mission_type)
    except Exception as exc:  # noqa: BLE001 - fail-closed: any rebuild failure is an ERROR
        return ReconciliationResult(
            status=ReconciliationStatus.ERROR,
            error=f"could not rebuild dossier from source for {mission_slug}: {exc}",
        )

    source_projection = _present_projection(dossier.artifacts)
    recorded_projection = [
        (str(summary.get("relative_path", "")), summary.get("content_hash_sha256")) for summary in recorded_snapshot.artifact_summaries if summary.get("is_present")
    ]

    # WP03 owns hashing + comparison (C-001). We never pass the snapshot's stored
    # parity_hash: it is the legacy concat-of-hashes form, not WP01's canonical
    # snapshot hash — the reconciler recomputes the recorded projection's hash.
    return reconciler.reconcile(source_projection, recorded_projection)


def _divergence_payload(divergence: ArtifactDivergence) -> dict[str, Any]:
    """Serialize one named artifact divergence for the ``--json`` surface."""
    return {
        "artifact_path": divergence.artifact_path,
        "kind": divergence.kind.value,
        "source_hash": divergence.source_hash,
        "recorded_hash": divergence.recorded_hash,
    }


def _result_payload(mission_slug: str, result: ReconciliationResult) -> dict[str, Any]:
    """Serialize a full reconciliation result for the ``--json`` surface."""
    return {
        "mission": mission_slug,
        "status": result.status.value,
        "rebuilt_hash": result.rebuilt_hash,
        "recorded_hash": result.recorded_hash,
        "differing_artifacts": [_divergence_payload(d) for d in result.differing_artifacts],
        "error": result.error,
    }


def _render_human(mission_slug: str, result: ReconciliationResult) -> None:
    """Render a human-readable reconciliation report to the console."""
    if result.is_parity:
        console.print(f"[green]PARITY[/green] {mission_slug} — dossier matches the recorded snapshot")
        return

    if result.is_divergence:
        console.print(f"[red]DIVERGENCE[/red] {mission_slug} — {len(result.differing_artifacts)} artifact(s) differ:")
        for divergence in result.differing_artifacts:
            console.print(f"  [red]•[/red] {divergence.artifact_path} ({divergence.kind.value})")
        return

    console.print(f"[red]ERROR[/red] {mission_slug} — {result.error or 'reconciliation could not complete'}")


def _exit_code(result: ReconciliationResult) -> int:
    """Map a reconciliation status to a process exit code (divergence≠0)."""
    if result.is_parity:
        return _EXIT_PARITY
    if result.is_divergence:
        return _EXIT_DIVERGENCE
    return _EXIT_ERROR


def reconcile(
    mission: Annotated[
        str,
        typer.Option("--mission", help="Mission slug to reconcile against its recorded snapshot"),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a machine-readable JSON result"),
    ] = False,
) -> None:
    """Reconcile a mission dossier against its recorded snapshot.

    Rebuilds the dossier from source, compares it to the recorded snapshot via
    the canonical reconciler, and reports the outcome. Exit status is the gate:

    - ``0`` — PARITY (dossier proven identical to the record).
    - ``1`` — DIVERGENCE (hashes differ; every differing artifact is NAMED).
    - ``2`` — ERROR (could not compute/compare — fail-closed, never a pass).

    Examples::

        spec-kitty reconcile --mission my-mission-01ABCD
        spec-kitty reconcile --mission my-mission-01ABCD --json
    """
    result = reconcile_mission_dossier(mission)

    if json_output:
        console.print_json(json.dumps(_result_payload(mission, result), indent=2))
    else:
        _render_human(mission, result)

    raise typer.Exit(_exit_code(result))
