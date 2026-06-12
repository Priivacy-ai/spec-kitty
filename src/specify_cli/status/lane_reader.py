"""Canonical lane reader from event log.

All runtime lane reads MUST go through this module. Frontmatter is no longer
consulted for lane values. When the event log file is absent the feature has
not been finalized and callers must surface a hard-fail with actionable
guidance.
"""
from __future__ import annotations
from pathlib import Path

from .models import Lane
from .store import EVENTS_FILENAME

# Sentinel returned by lane-reader functions when an event log exists but
# contains no events for the requested WP.  Kept here (the canonical
# lane-read surface) so every reader site can import a single shared
# definition rather than inlining the raw ``"uninitialized"`` string.
# ``status/aggregate.py`` imports this constant rather than redeclaring it.
LEGACY_UNINITIALIZED_SENTINEL: str = "uninitialized"


class CanonicalStatusNotFoundError(RuntimeError):
    """Raised when the event log file does not exist for a feature.

    This indicates that ``spec-kitty agent mission finalize-tasks`` has not
    been run yet, so canonical status events have not been bootstrapped.
    """


def has_event_log(feature_dir: Path) -> bool:
    """Return True when the canonical event log file exists on disk."""
    return bool((feature_dir / EVENTS_FILENAME).exists())


def _require_event_log(feature_dir: Path) -> None:
    """Raise ``CanonicalStatusNotFoundError`` when no event log exists.

    When the reason finalize-tasks never created the event log is an unresolved
    WP dependency cycle, surface that as the root cause (#1589) instead of a
    bare "run finalize-tasks" hint that loops forever on the same cycle.
    """
    if not has_event_log(feature_dir):
        from .uninitialized_hint import feature_event_log_missing_error

        raise CanonicalStatusNotFoundError(
            feature_event_log_missing_error(feature_dir)
        )


def get_wp_lane(feature_dir: Path, wp_id: str) -> Lane | str:
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
        return LEGACY_UNINITIALIZED_SENTINEL
    snapshot = reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return LEGACY_UNINITIALIZED_SENTINEL
    # Defensive default matches the write side (#1775 review M4 / I3 parity):
    # an entry that somehow lacks a lane is genesis (unseeded), not planned.
    return Lane(wp_state.get("lane", Lane.GENESIS))


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
        # Defensive default matches the write side (#1775 review M4 / I3 parity).
        wp_id: Lane(state.get("lane", Lane.GENESIS))
        for wp_id, state in snapshot.work_packages.items()
    }
