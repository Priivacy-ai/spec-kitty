"""SimpleJsonStore — JSONL-backed EventStore implementation.

Provides file-backed persistence for spec_kitty_events.Event objects
using append-only JSONL (one JSON object per line). Supports:

- Stream-parsed reads (line-by-line iteration)
- Idempotent writes (duplicate event_id silently skipped)
- Malformed line tolerance (corrupt lines skipped with warning)
- Automatic parent directory creation
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from specify_cli.spec_kitty_events.models import Event
from specify_cli.spec_kitty_events.storage import EventStore

logger = logging.getLogger(__name__)


class SimpleJsonStore(EventStore):
    """JSONL-backed EventStore for telemetry events.

    Each event is persisted as a single JSON line in append-only mode.
    Events are sorted by (lamport_clock, node_id) on read, matching
    the InMemoryEventStore contract.

    Args:
        file_path: Path to the JSONL file. Parent directories are
            created automatically on first write.
    """

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._known_ids: set[str] | None = None

    def save_event(self, event: Event) -> None:
        """Save event to JSONL file (idempotent by event_id).

        If the event_id already exists in the file, the write is
        silently skipped. Parent directories are created if needed.

        Args:
            event: Event to persist.
        """
        known = self._ensure_known_ids()
        if event.event_id in known:
            return

        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        data = event.to_dict()
        line = json.dumps(
            data,
            default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o),
            sort_keys=True,
        )

        with open(self._file_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        known.add(event.event_id)

    def load_events(self, aggregate_id: str) -> list[Event]:
        """Load events for a specific aggregate, sorted by (lamport_clock, node_id).

        Args:
            aggregate_id: Aggregate identifier to filter by.

        Returns:
            Filtered, sorted list of events.
        """
        all_events = self._read_all_raw()
        filtered = [e for e in all_events if e.aggregate_id == aggregate_id]
        return sorted(filtered, key=lambda e: (e.lamport_clock, e.node_id))

    def load_all_events(self) -> list[Event]:
        """Load all events, sorted by (lamport_clock, node_id).

        Returns:
            All events sorted by causal order.
        """
        events = self._read_all_raw()
        return sorted(events, key=lambda e: (e.lamport_clock, e.node_id))

    def _read_all_raw(self) -> list[Event]:
        """Stream-parse JSONL file into Event objects.

        Reads line-by-line (Python's file iterator is lazy).
        Malformed lines are skipped with a warning log.

        Returns:
            List of successfully parsed events (unsorted).
        """
        if not self._file_path.exists():
            return []

        events: list[Event] = []
        skipped = 0

        with open(self._file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(Event.from_dict(data))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                    skipped += 1
                    logger.warning("Skipping malformed event line: %s", str(e)[:100])
                except Exception as e:
                    skipped += 1
                    logger.warning(
                        "Skipping malformed event line (unexpected): %s",
                        str(e)[:100],
                    )

        if skipped:
            logger.warning("Skipped %d malformed line(s) in %s", skipped, self._file_path)

        return events

    def _ensure_known_ids(self) -> set[str]:
        """Lazy-load the set of known event_ids from the JSONL file.

        On first call, scans the entire file to build the dedup set.
        Subsequent calls return the cached set.

        Returns:
            Set of event_id strings already persisted.
        """
        if self._known_ids is not None:
            return self._known_ids

        self._known_ids = set()
        if not self._file_path.exists():
            return self._known_ids

        with open(self._file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event_id = data.get("event_id")
                    if event_id:
                        self._known_ids.add(event_id)
                except (json.JSONDecodeError, KeyError):
                    pass  # Skip corrupt lines during ID scan

        return self._known_ids
