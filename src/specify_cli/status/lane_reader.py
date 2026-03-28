"""Canonical lane reader from event log."""
from __future__ import annotations
from pathlib import Path


def get_wp_lane(feature_dir: Path, wp_id: str) -> str:
    """Get canonical lane for a WP from the event log.
    Returns 'planned' if no events exist for this WP.
    """
    from .store import read_events
    from .reducer import reduce
    events = read_events(feature_dir)
    if not events:
        return "planned"
    snapshot = reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return "planned"
    return str(wp_state.get("lane", "planned"))


def get_all_wp_lanes(feature_dir: Path) -> dict[str, str]:
    """Get canonical lanes for all WPs from the event log.
    Returns dict mapping wp_id -> lane string.
    """
    from .store import read_events
    from .reducer import reduce
    events = read_events(feature_dir)
    if not events:
        return {}
    snapshot = reduce(events)
    return {
        wp_id: str(state.get("lane", "planned"))
        for wp_id, state in snapshot.work_packages.items()
    }
