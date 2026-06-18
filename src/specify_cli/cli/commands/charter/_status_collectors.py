"""Status-collection helpers extracted from ``charter status`` (WP06 split).

These helpers are pure data collectors — they build dicts the command body
serialises to JSON or renders to the console. Kept in their own module so
``status.py`` stays under the 500-line WP06 budget.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import METADATA_FILENAME
from specify_cli.cli.commands.charter._common import (
    _display_path,
    _resolve_charter_path,
)
from specify_cli.cli.commands.charter._synthesis import _collect_evidence_result


def _normalize_last_sync(value: Any) -> str | None:
    """Coerce a metadata timestamp to a JSON-safe ISO string (FR-005).

    ``YAML(typ="safe")`` parses an *unquoted* ISO timestamp in ``metadata.yaml``
    to a ``datetime``/``date`` object, which is not JSON-serializable and
    crashed ``charter status --json`` (``Object of type datetime is not JSON
    serializable``). Normalize to an ISO 8601 string at the collector boundary
    so the payload carries a stable string-typed ``last_sync`` contract.

    ``datetime`` is a subclass of ``date``, so the single ``isinstance`` check
    covers both. Already-string (quoted) timestamps and ``None`` pass through
    unchanged.
    """
    if value is None:
        return None
    if isinstance(value, date):  # covers datetime (date subclass) and date
        return value.isoformat()
    return str(value)


def _collect_charter_sync_status(repo_root: Path) -> dict[str, Any]:
    """Read charter sync status without writing to disk.

    FR-010 / C-IC07: this is a read-only status collector. It MUST NOT call
    ``ensure_charter_bundle_fresh`` (which writes the charter bundle) or
    ``GlossaryEntityPageRenderer.generate_all()`` (which writes entity pages).
    Staleness is determined read-only via ``is_stale``; the canonical root is
    derived read-only as ``repo_root`` (no regeneration required to obtain it).
    """
    try:
        from charter.hasher import is_stale

        # Read-only root derivation: use repo_root directly (no write side-effect).
        # The write commands (charter sync / charter generate) legitimately call
        # ensure_charter_bundle_fresh; the status READ path does not.
        canonical_root = repo_root
        charter_path = _resolve_charter_path(canonical_root)
        output_dir = charter_path.parent
        metadata_path = output_dir / METADATA_FILENAME

        stale, current_hash, stored_hash = is_stale(charter_path, metadata_path)

        files_info: list[dict[str, str | bool | float]] = []
        for filename in [
            "governance.yaml",
            "directives.yaml",
            METADATA_FILENAME,
            "references.yaml",
        ]:
            file_path = output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                size_kb = size / 1024
                files_info.append(
                    {"name": filename, "exists": True, "size_kb": size_kb}
                )
            else:
                files_info.append(
                    {"name": filename, "exists": False, "size_kb": 0.0}
                )

        library_count = (
            len(list((output_dir / "library").glob("*.md")))
            if (output_dir / "library").exists()
            else 0
        )

        last_sync = None
        if metadata_path.exists():
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")
            metadata = yaml.load(metadata_path.read_text(encoding="utf-8")) or {}
            if isinstance(metadata, dict):
                last_sync = _normalize_last_sync(
                    metadata.get("timestamp_utc") or metadata.get("extracted_at")
                )

        return {
            "available": True,
            "charter_path": _display_path(charter_path, canonical_root),
            "status": "stale" if stale else "synced",
            "current_hash": current_hash,
            "stored_hash": stored_hash,
            "last_sync": last_sync,
            "library_docs": library_count,
            "files": files_info,
        }
    except TaskCliError as exc:
        return {
            "available": False,
            "error": str(exc),
        }


def _collect_governance_reference_status(repo_root: Path) -> dict[str, Any]:
    """Collect charter-declared supporting governance doc diagnostics."""
    try:
        from charter.governance_references import collect_governance_reference_status
        from charter.sync import load_governance_config

        governance = load_governance_config(repo_root)
        statuses = collect_governance_reference_status(
            repo_root,
            governance.doctrine.governance_references,
        )
    except Exception as exc:  # noqa: BLE001 - status diagnostics must degrade
        return {
            "available": False,
            "references": [],
            "warnings": [f"Could not inspect governance references: {exc}"],
        }

    warnings = [status.warning for status in statuses if status.warning]
    return {
        "available": True,
        "references": [status.to_dict() for status in statuses],
        "warnings": warnings,
    }


def _collect_generated_input_status(repo_root: Path) -> dict[str, Any]:
    input_root = repo_root / ".kittify" / "charter" / "generated"
    counts = {
        "directive": len(list((input_root / "directives").glob("*.yaml"))),
        "tactic": len(list((input_root / "tactics").glob("*.yaml"))),
        "styleguide": len(list((input_root / "styleguides").glob("*.yaml"))),
    }
    return {
        "path": _display_path(input_root, repo_root),
        "exists": input_root.exists(),
        "counts": counts,
        "total": sum(counts.values()),
    }


def _collect_manifest_status(repo_root: Path) -> tuple[dict[str, Any], Any | None]:
    from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml, verify

    manifest_path = repo_root / MANIFEST_PATH
    doctrine_root = repo_root / ".kittify" / "doctrine"
    provenance_root = repo_root / ".kittify" / "charter" / "provenance"
    live_artifact_count = sum(
        len(list((doctrine_root / subdir).glob("*.yaml")))
        for subdir in ("directive", "tactic", "styleguide")
    )
    live_provenance_count = len(list(provenance_root.glob("*.yaml")))

    if not manifest_path.exists():
        state = "partial" if live_artifact_count or live_provenance_count else "missing"
        return (
            {
                "path": _display_path(manifest_path, repo_root),
                "exists": False,
                "state": state,
                "artifact_count": 0,
                "live_artifact_count": live_artifact_count,
                "live_provenance_count": live_provenance_count,
                "run_id": None,
                "created_at": None,
                "adapter_id": None,
                "adapter_version": None,
                "missing_provenance_paths": [],
                "error": None,
            },
            None,
        )

    try:
        manifest = load_yaml(manifest_path)
        try:
            verify(manifest, repo_root)
            state = "valid"
            error = None
        except Exception as exc:  # noqa: BLE001 — manifest verification errors are non-fatal; record as invalid state
            state = "invalid"
            error = str(exc)
    except Exception as exc:  # noqa: BLE001 — manifest YAML load failure is non-fatal; return invalid status dict
        return (
            {
                "path": _display_path(manifest_path, repo_root),
                "exists": True,
                "state": "invalid",
                "artifact_count": 0,
                "live_artifact_count": live_artifact_count,
                "live_provenance_count": live_provenance_count,
                "run_id": None,
                "created_at": None,
                "adapter_id": None,
                "adapter_version": None,
                "missing_provenance_paths": [],
                "error": f"manifest could not be parsed: {exc}",
            },
            None,
        )

    missing_provenance_paths = [
        entry.provenance_path
        for entry in manifest.artifacts
        if not (repo_root / entry.provenance_path).exists()
    ]

    return (
        {
            "path": _display_path(manifest_path, repo_root),
            "exists": True,
            "state": state,
            "artifact_count": len(manifest.artifacts),
            "live_artifact_count": live_artifact_count,
            "live_provenance_count": live_provenance_count,
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "adapter_id": manifest.adapter_id,
            "adapter_version": manifest.adapter_version,
            "missing_provenance_paths": missing_provenance_paths,
            "error": error,
        },
        manifest,
    )


def _collect_provenance_status(
    repo_root: Path,
    manifest: Any | None,
    *,
    include_entries: bool,
) -> dict[str, Any]:
    from charter.synthesizer.provenance import load_yaml as load_provenance

    provenance_root = repo_root / ".kittify" / "charter" / "provenance"
    paths = sorted(provenance_root.glob("*.yaml"))
    warnings: list[str] = []
    entries: list[dict[str, Any]] = []
    visible_paths = {_display_path(path, repo_root) for path in paths}
    manifest_paths = (
        {entry.provenance_path for entry in manifest.artifacts}
        if manifest is not None
        else set()
    )
    corpus_snapshot_ids: set[str] = set()
    adapters: set[str] = set()

    for path in paths:
        rel_path = _display_path(path, repo_root)
        try:
            entry = load_provenance(path)
        except Exception as exc:  # noqa: BLE001 — per-provenance-file failure must not abort the full provenance scan
            warnings.append(f"{rel_path}: {exc}")
            continue

        if entry.corpus_snapshot_id:
            corpus_snapshot_ids.add(entry.corpus_snapshot_id)
        adapters.add(f"{entry.adapter_id}@{entry.adapter_version}")

        if include_entries:
            entries.append(
                {
                    "path": rel_path,
                    "kind": entry.artifact_kind,
                    "slug": entry.artifact_slug,
                    "artifact_urn": entry.artifact_urn,
                    "adapter_id": entry.adapter_id,
                    "adapter_version": entry.adapter_version,
                    "synthesizer_version": getattr(entry, "synthesizer_version", None),  # v2
                    "produced_at": getattr(entry, "produced_at", None),  # v2
                    "corpus_snapshot_id": entry.corpus_snapshot_id,
                    "evidence_bundle_hash": entry.evidence_bundle_hash,
                    "generated_at": entry.generated_at,
                }
            )

    missing_for_manifest = sorted(manifest_paths - visible_paths)
    return {
        "path": _display_path(provenance_root, repo_root),
        "count": len(paths),
        "parsed_count": len(paths) - len(warnings),
        "manifest_artifact_count": len(manifest_paths),
        "missing_for_manifest_count": len(missing_for_manifest),
        "missing_for_manifest": missing_for_manifest,
        "corpus_snapshot_ids": sorted(corpus_snapshot_ids),
        "adapters": sorted(adapters),
        "warnings": warnings,
        "entries": entries,
    }


def _summarize_evidence(repo_root: Path) -> dict[str, Any]:
    evidence_result = _collect_evidence_result(
        repo_root,
        skip_code_evidence=False,
        skip_corpus=False,
    )
    bundle = evidence_result.bundle
    code_summary: dict[str, Any] | None = None
    if bundle.code_signals is not None:
        code_summary = {
            "stack_id": bundle.code_signals.stack_id,
            "primary_language": bundle.code_signals.primary_language,
            "frameworks": list(bundle.code_signals.frameworks),
            "test_frameworks": list(bundle.code_signals.test_frameworks),
            "representative_files_count": len(
                bundle.code_signals.representative_files
            ),
            "representative_files_preview": list(
                bundle.code_signals.representative_files[:5]
            ),
        }

    return {
        "warnings": evidence_result.warnings,
        "code": code_summary,
        "configured_urls": list(bundle.url_list),
        "configured_url_count": len(bundle.url_list),
        "corpus_snapshot_id": (
            bundle.corpus_snapshot.snapshot_id
            if bundle.corpus_snapshot is not None
            else None
        ),
        "corpus_entry_count": (
            len(bundle.corpus_snapshot.entries)
            if bundle.corpus_snapshot is not None
            else 0
        ),
    }


def _collect_synthesis_status(
    repo_root: Path,
    *,
    include_provenance: bool,
) -> dict[str, Any]:
    generated_inputs = _collect_generated_input_status(repo_root)
    manifest_status, manifest = _collect_manifest_status(repo_root)
    provenance_status = _collect_provenance_status(
        repo_root,
        manifest,
        include_entries=include_provenance,
    )
    evidence_summary = _summarize_evidence(repo_root)

    if (
        manifest_status["state"] == "valid"
        and provenance_status["missing_for_manifest_count"] == 0
        and not provenance_status["warnings"]
    ):
        generation_state = "promoted"
    elif (
        manifest_status["state"] in {"invalid", "partial"}
        or provenance_status["missing_for_manifest_count"] > 0
        or provenance_status["warnings"]
    ):
        generation_state = "needs_attention"
    elif generated_inputs["total"] > 0:
        generation_state = "ready_for_validation"
    else:
        generation_state = "not_started"

    return {
        "generation_state": generation_state,
        "generated_inputs": generated_inputs,
        "manifest": manifest_status,
        "provenance": provenance_status,
        "evidence": evidence_summary,
    }


def _collect_org_layer_status(repo_root: Path) -> dict[str, Any]:
    """Collect org-layer state for ``charter status`` (FR-002).

    Returns a structured dict describing the configured organisation-tier
    DRG packs, their fetched/missing state, node/edge counts, and any
    collision warnings surfaced by ``merge_three_layers``.

    When no packs are configured, returns ``{"packs": [], "has_built_in": True}``.
    The caller (``status``) always emits this key in JSON output so operators
    and ATDD assertions can rely on its presence.

    NFR-001: this function is always called but the packs list is empty
    for repos without org pack configuration — no spurious section added.

    Per the charter layer architectural boundary (kernel <- doctrine <-
    charter <- specify_cli), we use ``charter.drg.load_org_drg`` directly
    rather than the ``specify_cli`` config path.  The caller may also pass
    the repo root to ``specify_cli.doctrine.config`` for richer pack metadata;
    this implementation stays purely charter-layer.
    """
    from charter.drg import (  # noqa: PLC0415
        OrgDRGConflictError,
        OrgPackMissingError,
        load_org_drg,
        merge_three_layers,
    )
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415
    from doctrine.drg.loader import load_graph_or_dir  # noqa: PLC0415

    result: dict[str, Any] = {
        "has_built_in": True,  # built-in layer is always present
        "packs": [],
        "collision_warnings": [],
        "errors": [],
    }

    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as exc:
        result["errors"].append(str(exc))
        return result
    except Exception as exc:  # noqa: BLE001 — best-effort; status must not crash
        result["errors"].append(f"org-DRG load error: {exc}")
        return result

    for frag in fragments:
        pack_entry: dict[str, Any] = {
            "name": frag.pack_name,
            "source_kind": frag.source_kind,
            "source_ref": frag.source_ref,
            "layer_index": frag.layer_index,
            "fetched": True,
            "node_count": len(frag.nodes),
            "edge_count": len(frag.edges),
        }
        result["packs"].append(pack_entry)

    if not fragments:
        return result

    # Run merge to surface collision warnings (best-effort).
    try:
        built_in = load_graph_or_dir(resolve_doctrine_root())
        merge_three_layers(built_in=built_in, org_fragments=fragments, project=None)
    except OrgDRGConflictError as exc:
        for conflict in exc.conflicts:
            result["collision_warnings"].append(
                {
                    "kind": conflict.kind,
                    "target_id": conflict.target_id,
                    "conflicting_layers": conflict.conflicting_layers,
                    "resolution": conflict.resolution_applied,
                }
            )
    except Exception:  # noqa: BLE001 — collision check is advisory in doctor/status
        pass

    return result
