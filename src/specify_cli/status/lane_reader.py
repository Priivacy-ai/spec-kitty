"""Canonical lane reader from event log.

All runtime lane reads MUST go through this module. Frontmatter is no longer
consulted for lane values. When the event log file is absent the feature has
not been finalized and callers must surface a hard-fail with actionable
guidance.
"""
from __future__ import annotations
from pathlib import Path

from .store import EVENTS_FILENAME


class CanonicalStatusNotFoundError(RuntimeError):
    """Raised when the event log file does not exist for a feature.

    This indicates that ``spec-kitty agent mission finalize-tasks`` has not
    been run yet, so canonical status events have not been bootstrapped.
    """


def has_event_log(feature_dir: Path) -> bool:
    """Return True when the canonical event log file exists on disk."""
    return (feature_dir / EVENTS_FILENAME).exists()


def _require_event_log(feature_dir: Path) -> None:
    """Raise ``CanonicalStatusNotFoundError`` when no event log exists."""
    if not has_event_log(feature_dir):
        slug = feature_dir.name
        raise CanonicalStatusNotFoundError(
            f"Canonical status not found for feature '{slug}'. "
            f"Run 'spec-kitty agent mission finalize-tasks --feature {slug}' "
            f"to bootstrap the event log."
        )


def get_wp_lane(feature_dir: Path, wp_id: str) -> str:
    """Get canonical lane for a WP from the event log.

    Raises ``CanonicalStatusNotFoundError`` when the event log file is
    absent (feature not finalized).

    Returns ``"uninitialized"`` when the event log exists but contains
    no events for *wp_id*.
    """
    _require_event_log(feature_dir)
    from .store import read_events
    from .reducer import reduce
    events = read_events(feature_dir)
    if not events:
        # File exists but is empty — treat WP as uninitialized.
        return "uninitialized"
    snapshot = reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return "uninitialized"
    return str(wp_state.get("lane", "planned"))


def get_all_wp_lanes(feature_dir: Path) -> dict[str, str]:
    """Get canonical lanes for all WPs from the event log.

    Raises ``CanonicalStatusNotFoundError`` when the event log file is
    absent (feature not finalized).

    Returns dict mapping wp_id -> lane string. WPs with no events are
    *not* included (caller should treat missing keys as ``"uninitialized"``).
    """
    _require_event_log(feature_dir)
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
