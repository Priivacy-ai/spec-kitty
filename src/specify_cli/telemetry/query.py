"""Query layer for execution event filtering and retrieval.

Provides EventFilter dataclass for flexible event filtering,
and query functions for both feature-level and project-level
event retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.spec_kitty_events.models import Event
from specify_cli.telemetry.store import SimpleJsonStore

EXECUTION_EVENTS_FILE = "execution.events.jsonl"


def _ensure_aware(dt: datetime) -> datetime:
    """Convert naive datetimes to UTC; return aware datetimes unchanged."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass(frozen=True)
class EventFilter:
    """Filter criteria for execution events.

    All fields are optional. When provided, they act as AND conditions.
    Each field must match for an event to pass the filter.

    Attributes:
        event_type: Filter by event type (e.g., 'WPStarted', 'WPCompleted').
        wp_id: Filter by work package ID (checks event.payload['wp_id']).
        agent: Filter by agent name (checks event.payload['agent']).
        model: Filter by model name (checks event.payload['model']).
        since: Only include events at or after this timestamp.
        until: Only include events at or before this timestamp.
        success: Filter by success status (checks event.payload['success']).
    """

    event_type: str | None = None
    wp_id: str | None = None
    agent: str | None = None
    model: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    success: bool | None = None

    def matches(self, event: Event) -> bool:
        """Check if event matches all non-None filter criteria.

        Args:
            event: Event to check against filter.

        Returns:
            True if event passes all active filters, False otherwise.
        """
        if self.event_type is not None and event.event_type != self.event_type:
            return False

        if self.wp_id is not None and event.payload.get("wp_id") != self.wp_id:
            return False

        if self.agent is not None and event.payload.get("agent") != self.agent:
            return False

        if self.model is not None and event.payload.get("model") != self.model:
            return False

        if self.since is not None:
            ts = _ensure_aware(event.timestamp)
            since = _ensure_aware(self.since)
            if ts < since:
                return False

        if self.until is not None:
            ts = _ensure_aware(event.timestamp)
            until = _ensure_aware(self.until)
            if ts > until:
                return False

        if self.success is not None and event.payload.get("success") != self.success:
            return False

        return True


def query_execution_events(feature_dir: Path, filters: EventFilter | None = None) -> list[Event]:
    """Query execution events for a single feature.

    Loads events from the feature's execution.events.jsonl file,
    applies optional filters, and returns sorted results.

    Args:
        feature_dir: Path to feature directory (e.g., kitty-specs/043-feature/).
        filters: Optional filter criteria. If None, returns all events.

    Returns:
        Filtered and sorted list of events (sorted by lamport_clock, node_id).
    """
    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    events = store.load_all_events()

    if filters is None:
        return events

    return [e for e in events if filters.matches(e)]


def query_project_events(repo_root: Path, filters: EventFilter | None = None) -> list[Event]:
    """Query execution events across all features in a project.

    Globs all execution.events.jsonl files in kitty-specs/*/,
    merges events, applies filters, and re-sorts by causal order.

    Args:
        repo_root: Root directory of the spec-kitty project.
        filters: Optional filter criteria. If None, returns all events.

    Returns:
        Filtered and sorted list of events from all features
        (sorted by lamport_clock, node_id).
    """
    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.exists():
        return []

    all_events: list[Event] = []

    for event_file in kitty_specs.glob(f"*/{EXECUTION_EVENTS_FILE}"):
        store = SimpleJsonStore(event_file)
        events = store.load_all_events()
        all_events.extend(events)

    if filters is not None:
        all_events = [e for e in all_events if filters.matches(e)]

    return sorted(all_events, key=lambda e: (e.lamport_clock, e.node_id))
