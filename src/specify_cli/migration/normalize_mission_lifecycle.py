"""Normalize legacy ``kitty-specs`` missions for the MVP lifecycle model.

The goal is not to rewrite historical repositories into a perfect new layout.
It is to make old missions coherent enough that lifecycle derivation and
Teamspace-facing projections can reason about them consistently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.mission_metadata import load_meta
from specify_cli.migration.backfill_identity import (
    backfill_mission,
    backfill_wp_ids,
    trigger_feature_dossier_sync_if_enabled,
)
from specify_cli.migration.rebuild_state import rebuild_event_log
from specify_cli.status.lifecycle import derive_mission_lifecycle, generate_lifecycle_json
from specify_cli.status.progress import generate_progress_json
from specify_cli.status.views import write_derived_views


@dataclass
class NormalizeMissionLifecycleResult:
    slug: str
    status: str
    lifecycle_state: str | None = None
    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def _discover_candidates(repo_root: Path, mission_slug: str | None = None) -> list[Path]:
    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.is_dir():
        return []
    candidates = [entry for entry in sorted(kitty_specs.iterdir()) if entry.is_dir()]
    if mission_slug is not None:
        candidates = [entry for entry in candidates if entry.name == mission_slug]
    return candidates


def _needs_event_log(feature_dir: Path) -> bool:
    events_path = feature_dir / "status.events.jsonl"
    if events_path.exists():
        return False
    return (feature_dir / "status.json").exists() or (feature_dir / "tasks").is_dir()


def _needs_derived_refresh(feature_dir: Path, derived_dir: Path) -> bool:
    feature_derived = derived_dir / feature_dir.name
    status_path = feature_derived / "status.json"
    progress_path = feature_derived / "progress.json"
    lifecycle_path = feature_derived / "lifecycle.json"
    if not status_path.exists() or not progress_path.exists() or not lifecycle_path.exists():
        return True

    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return False

    events_mtime = events_path.stat().st_mtime
    return any(events_mtime > path.stat().st_mtime for path in (status_path, progress_path, lifecycle_path))


def _load_meta_for_normalization(
    feature_dir: Path,
    result: NormalizeMissionLifecycleResult,
) -> dict | None:
    try:
        meta = load_meta(feature_dir)
    except Exception as exc:  # noqa: BLE001 - keep one broken mission from aborting the run
        result.status = "error"
        result.error = f"Could not read meta.json: {exc}"
        return None
    if meta is None:
        result.warnings.append("meta.json missing; mission skipped")
        return None
    return meta


def _apply_identity_normalization(
    feature_dir: Path,
    repo_root: Path,
    meta: dict,
    result: NormalizeMissionLifecycleResult,
    *,
    dry_run: bool,
) -> tuple[dict, bool] | None:
    refresh_derived = False
    try:
        backfill = backfill_mission(feature_dir, dry_run=dry_run)
    except Exception as exc:  # noqa: BLE001 - mission_number sentinel and similar legacy breakage
        result.status = "error"
        result.error = f"Identity backfill failed: {exc}"
        return None

    if backfill.action == "wrote":
        result.actions.append("Backfilled mission identity metadata")
        refresh_derived = True
    if backfill.number_coerced:
        result.actions.append("Normalized legacy mission_number type")
        refresh_derived = True
    if not dry_run and (backfill.action == "wrote" or backfill.number_coerced):
        try:
            trigger_feature_dossier_sync_if_enabled(
                feature_dir=feature_dir,
                mission_slug=result.slug,
                repo_root=repo_root,
            )
        except Exception as exc:  # noqa: BLE001 - keep normalization best-effort
            result.warnings.append(f"dossier rehash failed: {exc}")
        meta = load_meta(feature_dir) or meta

    return meta, refresh_derived


def _normalize_event_log(
    feature_dir: Path,
    meta: dict,
    result: NormalizeMissionLifecycleResult,
    *,
    dry_run: bool,
) -> bool | None:
    if not _needs_event_log(feature_dir):
        return False

    mission_id = meta.get("mission_id")
    if mission_id and (feature_dir / "tasks").is_dir():
        if dry_run:
            result.actions.append("Would backfill missing WP identity fields before rebuilding the event log")
        else:
            backfill_wp_ids(feature_dir, str(mission_id))
            result.actions.append("Backfilled missing WP identity fields")

    if dry_run:
        result.actions.append("Would rebuild status.events.jsonl from legacy mission state")
        return True

    rebuild = rebuild_event_log(feature_dir, result.slug, wp_id_map={})
    if rebuild.errors:
        result.status = "error"
        result.error = "; ".join(rebuild.errors)
        result.warnings.extend(rebuild.warnings)
        return None

    result.actions.append(f"Rebuilt status.events.jsonl ({rebuild.events_generated} synthetic events, {rebuild.events_corrected} corrected)")
    result.warnings.extend(rebuild.warnings)
    return True


def _finalize_lifecycle_projection(
    feature_dir: Path,
    derived_dir: Path,
    result: NormalizeMissionLifecycleResult,
    *,
    dry_run: bool,
    refresh_derived: bool,
) -> None:
    if dry_run and refresh_derived:
        result.actions.append("Would regenerate canonical status/progress/lifecycle views")
        try:
            result.lifecycle_state = derive_mission_lifecycle(feature_dir).state
        except Exception as exc:  # noqa: BLE001 - preview should stay resilient
            result.warnings.append(f"Lifecycle preview unavailable: {exc}")
    elif not dry_run and refresh_derived:
        try:
            write_derived_views(feature_dir, derived_dir)
            generate_progress_json(feature_dir, derived_dir)
            generate_lifecycle_json(feature_dir, derived_dir)
            result.lifecycle_state = derive_mission_lifecycle(feature_dir).state
        except Exception as exc:  # noqa: BLE001 - collect per-mission failure
            result.status = "error"
            result.error = f"Lifecycle materialization failed: {exc}"
            return
        result.actions.append("Regenerated canonical status/progress/lifecycle views")
    else:
        try:
            result.lifecycle_state = derive_mission_lifecycle(feature_dir).state
        except Exception as exc:  # noqa: BLE001 - report but do not fail a read-only no-op
            result.warnings.append(f"Lifecycle preview unavailable: {exc}")


def normalize_repo(
    repo_root: Path,
    *,
    dry_run: bool = False,
    mission_slug: str | None = None,
) -> list[NormalizeMissionLifecycleResult]:
    """Normalize lifecycle-relevant mission state for one repo."""
    results: list[NormalizeMissionLifecycleResult] = []
    candidates = _discover_candidates(repo_root, mission_slug=mission_slug)
    if not candidates:
        return results

    derived_dir = repo_root / ".kittify" / "derived"

    for feature_dir in candidates:
        slug = feature_dir.name
        result = NormalizeMissionLifecycleResult(slug=slug, status="skipped")
        meta = _load_meta_for_normalization(feature_dir, result)
        if meta is None:
            results.append(result)
            continue

        identity_result = _apply_identity_normalization(
            feature_dir,
            repo_root,
            meta,
            result,
            dry_run=dry_run,
        )
        if identity_result is None:
            results.append(result)
            continue
        meta, refresh_derived = identity_result

        event_refresh = _normalize_event_log(
            feature_dir,
            meta,
            result,
            dry_run=dry_run,
        )
        if event_refresh is None:
            results.append(result)
            continue

        refresh_derived = refresh_derived or event_refresh or _needs_derived_refresh(feature_dir, derived_dir)
        _finalize_lifecycle_projection(
            feature_dir,
            derived_dir,
            result,
            dry_run=dry_run,
            refresh_derived=refresh_derived,
        )
        if result.status == "error":
            results.append(result)
            continue

        if result.actions:
            result.status = "normalized"
        results.append(result)

    return results
