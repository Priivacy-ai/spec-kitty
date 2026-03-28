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

from .reducer import materialize, reduce
from .store import read_events

BOARD_SUMMARY_FILENAME = "board-summary.json"


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


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file atomically using a temp-file + os.replace."""
    json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(path))
