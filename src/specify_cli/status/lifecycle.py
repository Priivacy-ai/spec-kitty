"""Canonical mission lifecycle derivation for local and Teamspace-facing surfaces.

This module intentionally sits above the WP lane model.  It translates
authoritative mission status snapshots into a small set of product-facing
states that can be shared by CLI UX, migrations, and downstream consumers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import load_meta, resolve_mission_identity
from specify_cli.status.models import Lane, StatusSnapshot
from specify_cli.status.progress import compute_weighted_progress
from specify_cli.status.store import EVENTS_FILENAME, read_events
from specify_cli.status.wp_state import wp_state_for

DERIVED_LIFECYCLE_FILENAME = "lifecycle.json"

MISSION_RECENT_COMPLETION_WINDOW_DAYS = 3
MISSION_STALE_THRESHOLD_DAYS = 14
MISSION_ABANDONED_THRESHOLD_DAYS = 30

_ACTIVE_LANES = frozenset(
    {
        Lane.CLAIMED,
        Lane.IN_PROGRESS,
        Lane.FOR_REVIEW,
        Lane.IN_REVIEW,
        Lane.APPROVED,
        Lane.BLOCKED,
    }
)
_TERMINAL_LANES = frozenset({Lane.DONE, Lane.CANCELED})


@dataclass(frozen=True)
class MissionLifecycleResult:
    """Derived mission lifecycle state for machine-facing surfaces."""

    mission_slug: str
    mission_number: int | None
    mission_type: str | None
    state: str
    surface_state: str | None
    reason: str
    last_activity_at: datetime | None
    last_transition_at: datetime | None
    age_days: int | None
    completion_pct: float
    event_count: int
    total_wps: int
    active_wp_count: int
    blocked_wp_count: int
    review_wp_count: int
    terminal_wp_count: int
    has_event_log: bool
    stale_after_days: int = MISSION_STALE_THRESHOLD_DAYS
    abandoned_after_days: int = MISSION_ABANDONED_THRESHOLD_DAYS

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_slug": self.mission_slug,
            "mission_number": self.mission_number,
            "mission_type": self.mission_type,
            "state": self.state,
            "surface_state": self.surface_state,
            "reason": self.reason,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "last_transition_at": self.last_transition_at.isoformat() if self.last_transition_at else None,
            "age_days": self.age_days,
            "completion_pct": round(self.completion_pct, 1),
            "event_count": self.event_count,
            "total_wps": self.total_wps,
            "active_wp_count": self.active_wp_count,
            "blocked_wp_count": self.blocked_wp_count,
            "review_wp_count": self.review_wp_count,
            "terminal_wp_count": self.terminal_wp_count,
            "has_event_log": self.has_event_log,
            "stale_after_days": self.stale_after_days,
            "abandoned_after_days": self.abandoned_after_days,
        }


def _empty_snapshot(mission_slug: str, mission_number: int | None, mission_type: str | None) -> StatusSnapshot:
    return StatusSnapshot(
        mission_slug=mission_slug,
        materialized_at="",
        event_count=0,
        last_event_id=None,
        work_packages={},
        summary={lane.value: 0 for lane in Lane},
        mission_number=str(mission_number) if mission_number is not None else None,
        mission_type=mission_type,
    )


def _parse_dt(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _fallback_created_at(feature_dir: Path) -> datetime | None:
    meta = load_meta(feature_dir) or {}
    created_at = _parse_dt(meta.get("created_at"))
    if created_at is not None:
        return created_at

    try:
        return datetime.fromtimestamp(feature_dir.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _derive_last_transition_at(snapshot: StatusSnapshot) -> datetime | None:
    candidates = [
        _parse_dt(wp_state.get("last_transition_at"))
        for wp_state in snapshot.work_packages.values()
        if isinstance(wp_state, dict)
    ]
    filtered = [candidate for candidate in candidates if candidate is not None]
    if filtered:
        return max(filtered)
    return _parse_dt(snapshot.materialized_at)


def _classify_state(
    *,
    total_wps: int,
    active_wp_count: int,
    terminal_wp_count: int,
    age_days: int | None,
) -> tuple[str, str | None, str]:
    if active_wp_count > 0:
        if age_days is not None and age_days >= MISSION_ABANDONED_THRESHOLD_DAYS:
            return ("abandoned", None, "Active work appears abandoned and should stay off primary surfaces.")
        if age_days is not None and age_days >= MISSION_STALE_THRESHOLD_DAYS:
            return ("stale", None, "Active work has gone stale and should be recovered before it resurfaces.")
        return ("active", "active", "Mission has live work in progress or review.")

    if total_wps > 0 and terminal_wp_count == total_wps:
        if age_days is not None and age_days <= MISSION_RECENT_COMPLETION_WINDOW_DAYS:
            return ("recently_completed", "recently_completed", "Mission completed recently and still deserves short-lived visibility.")
        return ("archived", None, "Mission is completed and now belongs in history rather than the default surface.")

    if age_days is not None and age_days >= MISSION_ABANDONED_THRESHOLD_DAYS:
        return ("abandoned", None, "Mission never reached an active terminal state and now looks abandoned.")
    if age_days is not None and age_days >= MISSION_STALE_THRESHOLD_DAYS:
        return ("stale", None, "Mission is recoverable but stale and should not pollute primary surfaces.")
    return ("recoverable", None, "Mission is recoverable history and not active enough for the default surface.")


def derive_mission_lifecycle(
    feature_dir: Path,
    *,
    now: datetime | None = None,
) -> MissionLifecycleResult:
    """Return canonical lifecycle state for one mission directory."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    identity = resolve_mission_identity(feature_dir)
    has_event_log = (feature_dir / EVENTS_FILENAME).exists()

    if has_event_log:
        from specify_cli.status.reducer import reduce

        snapshot = reduce(read_events(feature_dir))
        snapshot.mission_number = (
            str(identity.mission_number)
            if identity.mission_number is not None
            else None
        )
        snapshot.mission_type = identity.mission_type
        if not snapshot.mission_slug:
            snapshot.mission_slug = identity.mission_slug or feature_dir.name
    else:
        snapshot = _empty_snapshot(identity.mission_slug or feature_dir.name, identity.mission_number, identity.mission_type)

    progress = compute_weighted_progress(snapshot)
    total_wps = len(snapshot.work_packages)
    active_wp_count = 0
    blocked_wp_count = 0
    review_wp_count = 0
    terminal_wp_count = 0

    for wp_state in snapshot.work_packages.values():
        lane_value = wp_state.get("lane", Lane.PLANNED)
        try:
            lane = Lane(str(lane_value))
        except ValueError:
            lane = Lane.PLANNED
        wp_lifecycle_state = wp_state_for(lane)
        if lane in _ACTIVE_LANES:
            active_wp_count += 1
        if wp_lifecycle_state.is_blocked:
            blocked_wp_count += 1
        if wp_lifecycle_state.progress_bucket() == "review":
            review_wp_count += 1
        if wp_lifecycle_state.is_terminal:
            terminal_wp_count += 1

    last_transition_at = _derive_last_transition_at(snapshot)
    last_activity_at = last_transition_at or _fallback_created_at(feature_dir)
    age_days = None
    if last_activity_at is not None:
        age_delta = now - last_activity_at
        age_days = max(0, int(age_delta / timedelta(days=1)))

    mission_state, surface_state, reason = _classify_state(
        total_wps=total_wps,
        active_wp_count=active_wp_count,
        terminal_wp_count=terminal_wp_count,
        age_days=age_days,
    )

    return MissionLifecycleResult(
        mission_slug=snapshot.mission_slug or identity.mission_slug or feature_dir.name,
        mission_number=identity.mission_number,
        mission_type=identity.mission_type,
        state=mission_state,
        surface_state=surface_state,
        reason=reason,
        last_activity_at=last_activity_at,
        last_transition_at=last_transition_at,
        age_days=age_days,
        completion_pct=progress.percentage,
        event_count=snapshot.event_count,
        total_wps=total_wps,
        active_wp_count=active_wp_count,
        blocked_wp_count=blocked_wp_count,
        review_wp_count=review_wp_count,
        terminal_wp_count=terminal_wp_count,
        has_event_log=has_event_log,
    )


def generate_lifecycle_json(feature_dir: Path, derived_dir: Path) -> None:
    """Write ``lifecycle.json`` for one mission under ``.kittify/derived``."""
    lifecycle = derive_mission_lifecycle(feature_dir)
    mission_slug = lifecycle.mission_slug or feature_dir.name
    output_dir = derived_dir / mission_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / DERIVED_LIFECYCLE_FILENAME
    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(lifecycle.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(str(tmp_path), str(out_path))
