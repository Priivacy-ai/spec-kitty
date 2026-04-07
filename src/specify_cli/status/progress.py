"""Lane-weighted progress computation for spec-kitty work packages.

This module provides a pure-function implementation of weighted progress
that reflects true pipeline advancement. A WP in ``in_progress`` contributes
more than one in ``planned`` but less than one that is ``done``.

The computation is intentionally side-effect-free. No file I/O occurs
inside ``compute_weighted_progress``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases

from .models import StatusSnapshot
from .reducer import materialize

# Default lane weights for the 9-lane state machine.
# blocked and canceled contribute 0 — they don't represent forward progress.
# in_review sits between for_review and approved in the review pipeline.
DEFAULT_LANE_WEIGHTS: dict[str, float] = {
    "planned": 0.0,
    "claimed": 0.05,
    "in_progress": 0.3,
    "for_review": 0.6,
    "in_review": 0.7,
    "approved": 0.8,
    "done": 1.0,
    "blocked": 0.0,
    "canceled": 0.0,
}


@dataclass
class WPProgress:
    """Per-WP progress breakdown."""

    wp_id: str
    lane: str
    lane_weight: float
    wp_weight: float
    fractional_progress: float  # lane_weight * wp_weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "wp_id": self.wp_id,
            "lane": self.lane,
            "lane_weight": self.lane_weight,
            "wp_weight": self.wp_weight,
            "fractional_progress": self.fractional_progress,
        }


@dataclass
class ProgressResult:
    """Weighted progress result for a feature.

    JSON-serialisable for machine consumption.
    """

    mission_slug: str
    percentage: float
    done_count: int
    total_count: int
    per_lane_counts: dict[str, int] = field(default_factory=dict)
    per_wp: list[WPProgress] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return with_tracked_mission_slug_aliases(
            {
                "mission_slug": self.mission_slug,
                "percentage": round(self.percentage, 4),
                "done_count": self.done_count,
                "total_count": self.total_count,
                "per_lane_counts": self.per_lane_counts,
                "per_wp": [wp.to_dict() for wp in self.per_wp],
            }
        )


def compute_weighted_progress(
    snapshot: StatusSnapshot,
    wp_weights: dict[str, float] | None = None,
    lane_weights: dict[str, float] | None = None,
) -> ProgressResult:
    """Compute lane-weighted progress from a status snapshot.

    This is a pure function — it does not read or write files.

    The formula is::

        percentage = sum(wp_weight[wp] * lane_weight[wp.lane])
                     / sum(wp_weight[wp])
                     * 100

    A feature where all WPs are in ``in_progress`` (weight 0.3) returns
    approximately 30%, not 0%. ``done`` (weight 1.0) returns 100%.

    Args:
        snapshot: Materialised snapshot of the feature state.
        wp_weights: Optional per-WP weight overrides (default: 1.0 each).
        lane_weights: Optional lane weight overrides (default:
            ``DEFAULT_LANE_WEIGHTS``).

    Returns:
        A :class:`ProgressResult` with percentage, per-lane counts,
        and per-WP breakdown.
    """
    resolved_lane_weights = dict(DEFAULT_LANE_WEIGHTS)
    if lane_weights:
        resolved_lane_weights.update(lane_weights)

    work_packages = snapshot.work_packages
    if not work_packages:
        return ProgressResult(
            mission_slug=snapshot.mission_slug,
            percentage=0.0,
            done_count=0,
            total_count=0,
            per_lane_counts={},
            per_wp=[],
        )

    per_lane_counts: dict[str, int] = {}
    per_wp: list[WPProgress] = []
    weighted_sum = 0.0
    weight_total = 0.0
    done_count = 0

    for wp_id, wp_state in sorted(work_packages.items()):
        lane = wp_state.get("lane", "planned")
        wp_weight = (wp_weights or {}).get(wp_id, 1.0)
        lw = resolved_lane_weights.get(lane, 0.0)
        fractional = wp_weight * lw

        weighted_sum += fractional
        weight_total += wp_weight
        per_lane_counts[lane] = per_lane_counts.get(lane, 0) + 1

        if lane == "done":
            done_count += 1

        per_wp.append(
            WPProgress(
                wp_id=wp_id,
                lane=lane,
                lane_weight=lw,
                wp_weight=wp_weight,
                fractional_progress=fractional,
            )
        )

    percentage = (weighted_sum / weight_total * 100.0) if weight_total > 0 else 0.0

    return ProgressResult(
        mission_slug=snapshot.mission_slug,
        percentage=percentage,
        done_count=done_count,
        total_count=len(work_packages),
        per_lane_counts=per_lane_counts,
        per_wp=per_wp,
    )


def generate_progress_json(feature_dir: Path, derived_dir: Path) -> None:
    """Materialise snapshot, compute progress, and write ``progress.json``.

    Writes to ``derived_dir / <mission_slug> / progress.json`` atomically
    (write-to-temp then ``os.replace``). The output directory is created
    if it does not exist.

    Args:
        feature_dir: Path to the feature directory
            (e.g. ``kitty-specs/034-feature/``).
        derived_dir: Root directory for derived artefacts.
    """
    snapshot = materialize(feature_dir)
    mission_slug = snapshot.mission_slug or feature_dir.name
    result = compute_weighted_progress(snapshot)

    output_dir = derived_dir / mission_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    json_str = json.dumps(result.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    out_path = output_dir / "progress.json"
    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))
