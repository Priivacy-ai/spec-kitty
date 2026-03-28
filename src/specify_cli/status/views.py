"""Derived view generation from the canonical status event log.

Generates output-only views (status.json, board-summary.json) from the
event log snapshot. These views are never authoritative — the event log
is the sole source of truth.

Use these functions after emitting events or materializing a snapshot
when human-readable or machine-readable output is needed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import StatusSnapshot
from .reducer import materialize, reduce
from .store import EVENTS_FILENAME, read_events

BOARD_SUMMARY_FILENAME = "board-summary.json"
DERIVED_STATUS_FILENAME = "status.json"
DERIVED_PROGRESS_FILENAME = "progress.json"


def generate_status_view(feature_dir: Path) -> dict[str, Any]:
    """Read the event log and return the current snapshot as a dict.

    Reads events via ``read_events(feature_dir)``, reduces to a
    ``StatusSnapshot``, and returns its dict representation.

    Returns:
        Snapshot dict suitable for JSON serialisation.
        Returns an empty snapshot dict if the event log is missing
        or contains no events.
    """
    events = read_events(feature_dir)
    snapshot = reduce(events)
    return snapshot.to_dict()


def write_derived_views(
    feature_dir: Path,
    derived_dir: Path,
) -> None:
    """Generate and write derived views from the event log.

    Produces two files under ``derived_dir / <feature_slug>/``:

    - ``status.json`` — full StatusSnapshot serialised as JSON.
    - ``board-summary.json`` — lane counts and WP lists per lane.

    Both files are written atomically (write-to-temp then os.replace).
    The output directory is created if it does not exist.

    These views are output-only and must never be consulted as
    authoritative state.

    Args:
        feature_dir: Path to the feature directory
            (e.g. ``kitty-specs/034-feature/``).
        derived_dir: Root directory for derived artefacts.
    """
    snapshot = materialize(feature_dir)
    feature_slug = snapshot.feature_slug or feature_dir.name

    output_dir = derived_dir / feature_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write status.json
    _atomic_write_json(
        output_dir / "status.json",
        snapshot.to_dict(),
    )

    # Write board-summary.json
    board_summary = _build_board_summary(snapshot)
    _atomic_write_json(
        output_dir / BOARD_SUMMARY_FILENAME,
        board_summary,
    )


def _build_board_summary(snapshot: Any) -> dict[str, Any]:
    """Build a compact board summary from a StatusSnapshot.

    Returns a dict with:
    - ``feature_slug``: feature identifier
    - ``total_wps``: total number of work packages
    - ``summary``: lane -> count mapping (all 7 lanes)
    - ``lanes``: lane -> list of wp_ids mapping
    - ``materialized_at``: ISO timestamp of snapshot

    Only lanes with at least one WP are included in ``lanes``.
    """
    lanes: dict[str, list[str]] = {}
    for wp_id, wp_state in sorted(snapshot.work_packages.items()):
        lane = wp_state.get("lane", "planned")
        if lane not in lanes:
            lanes[lane] = []
        lanes[lane].append(wp_id)

    return {
        "feature_slug": snapshot.feature_slug,
        "total_wps": len(snapshot.work_packages),
        "summary": snapshot.summary,
        "lanes": lanes,
        "materialized_at": snapshot.materialized_at,
    }


def materialize_if_stale(feature_dir: Path, repo_root: Path) -> StatusSnapshot:
    """Regenerate derived views when the event log is newer than the derived files.

    Checks whether ``status.json`` and ``progress.json`` exist in
    ``.kittify/derived/<feature_slug>/`` and whether the event log
    (``status.events.jsonl``) has a newer mtime than either derived file.
    If stale (or derived files are missing), regenerates all derived views.

    Returns the current snapshot (whether freshly generated or previously
    materialised on disk via the event log).

    Args:
        feature_dir: Path to the feature directory
            (e.g. ``kitty-specs/034-feature/``).
        repo_root: Root of the main repository (contains ``.kittify/``).
    """
    from .progress import generate_progress_json  # local import to avoid circular

    feature_slug = feature_dir.name
    derived_dir = repo_root / ".kittify" / "derived"
    feature_derived = derived_dir / feature_slug

    events_path = feature_dir / EVENTS_FILENAME
    status_path = feature_derived / DERIVED_STATUS_FILENAME
    progress_path = feature_derived / DERIVED_PROGRESS_FILENAME

    def _is_stale() -> bool:
        if not status_path.exists() or not progress_path.exists():
            return True
        if not events_path.exists():
            return False
        events_mtime = events_path.stat().st_mtime
        status_mtime = status_path.stat().st_mtime
        progress_mtime = progress_path.stat().st_mtime
        return events_mtime > status_mtime or events_mtime > progress_mtime

    if _is_stale():
        write_derived_views(feature_dir, derived_dir)
        generate_progress_json(feature_dir, derived_dir)

    # Always return a fresh snapshot from the event log
    return materialize(feature_dir)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file atomically using a temp-file + os.replace."""
    json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(path))
