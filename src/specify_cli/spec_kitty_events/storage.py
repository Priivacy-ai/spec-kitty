"""Storage adapters for events and errors."""
from abc import ABC, abstractmethod
from typing import List, Dict
from spec_kitty_events.models import Event, ErrorEntry


class EventStore(ABC):
    """Abstract base class for event persistence.

    Implementations must provide idempotent save semantics:
    - Saving the same event twice (by event_id) should not duplicate it
    - load_events() returns events in temporal order (sorted by lamport_clock, then node_id)

    Note: Thread-safety is the responsibility of the concrete implementation.
    """

    @abstractmethod
    def save_event(self, event: Event) -> None:
        """Save event (idempotent - duplicate event_id overwrites).

        Args:
            event: Event to persist

        Raises:
            StorageError: If save fails
        """
        pass  # pragma: no cover

    @abstractmethod
    def load_events(self, aggregate_id: str) -> List[Event]:
        """Load all events for a specific aggregate.

        Args:
            aggregate_id: Aggregate identifier to filter by

        Returns:
            List of events sorted by (lamport_clock, node_id)

        Raises:
            StorageError: If load fails
        """
        pass  # pragma: no cover

    @abstractmethod
    def load_all_events(self) -> List[Event]:
        """Load all events across all aggregates.

        Returns:
            List of all events sorted by (lamport_clock, node_id)

        Raises:
            StorageError: If load fails
        """
        pass  # pragma: no cover


class ClockStorage(ABC):
    """Abstract base class for Lamport clock persistence.

    Implementations must:
    - Return 0 if clock has never been saved (initial state)
    - Overwrite previous value on each save (no history)

    Note: Thread-safety is the responsibility of the concrete implementation.
    """

    @abstractmethod
    def load(self, node_id: str) -> int:
        """Load current clock value for a node.

        Args:
            node_id: Node identifier

        Returns:
            Current clock value (0 if never saved)

        Raises:
            StorageError: If load fails
        """
        pass  # pragma: no cover

    @abstractmethod
    def save(self, node_id: str, clock_value: int) -> None:
        """Save clock value for a node (overwrites previous value).

        Args:
            node_id: Node identifier
            clock_value: New clock value (must be ≥ 0)

        Raises:
            StorageError: If save fails
            ValueError: If clock_value < 0
        """
        pass  # pragma: no cover


class ErrorStorage(ABC):
    """Abstract base class for error log persistence.

    Implementations must:
    - Support append-only semantics (no updates/deletes)
    - Return errors in reverse chronological order (newest first)
    - Enforce retention policy (evict oldest when limit exceeded)

    Note: Thread-safety is the responsibility of the concrete implementation.
    """

    @abstractmethod
    def append(self, entry: ErrorEntry) -> None:
        """Append error entry to log.

        Args:
            entry: Error entry to persist

        Raises:
            StorageError: If append fails
        """
        pass  # pragma: no cover

    @abstractmethod
    def load_recent(self, limit: int = 10) -> List[ErrorEntry]:
        """Load most recent error entries.

        Args:
            limit: Maximum number of entries to return (default 10)

        Returns:
            List of error entries in reverse chronological order (newest first)

        Raises:
            StorageError: If load fails
            ValueError: If limit < 1
        """
        pass  # pragma: no cover


class InMemoryEventStore(EventStore):
    """In-memory event storage for testing (not thread-safe, not durable).

    WARNING: All data is lost when the object is garbage collected.
    For production use, implement a persistent adapter (e.g., SQLite, PostgreSQL).
    """

    def __init__(self) -> None:
        """Initialize empty event store."""
        self._events: Dict[str, Event] = {}  # event_id -> Event

    def save_event(self, event: Event) -> None:
        """Save event (overwrites if event_id already exists)."""
        self._events[event.event_id] = event

    def load_events(self, aggregate_id: str) -> List[Event]:
        """Load events for aggregate, sorted by (lamport_clock, node_id)."""
        events = [e for e in self._events.values() if e.aggregate_id == aggregate_id]
        return sorted(events, key=lambda e: (e.lamport_clock, e.node_id))

    def load_all_events(self) -> List[Event]:
        """Load all events, sorted by (lamport_clock, node_id)."""
        return sorted(self._events.values(), key=lambda e: (e.lamport_clock, e.node_id))


class InMemoryClockStorage(ClockStorage):
    """In-memory clock storage for testing (not thread-safe, not durable).

    WARNING: All data is lost when the object is garbage collected.
    For production use, implement a persistent adapter (e.g., file, database).
    """

    def __init__(self) -> None:
        """Initialize empty clock storage."""
        self._clocks: Dict[str, int] = {}  # node_id -> clock_value

    def load(self, node_id: str) -> int:
        """Load clock value (returns 0 if never saved)."""
        return self._clocks.get(node_id, 0)

    def save(self, node_id: str, clock_value: int) -> None:
        """Save clock value (validates ≥ 0)."""
        if clock_value < 0:
            raise ValueError(f"Clock value must be ≥ 0, got {clock_value}")
        self._clocks[node_id] = clock_value


class InMemoryErrorStorage(ErrorStorage):
    """In-memory error storage for testing (not thread-safe, not durable).

    WARNING: All data is lost when the object is garbage collected.
    Retention policy: Keeps only the 100 most recent errors (configurable).
    """

    def __init__(self, max_entries: int = 100) -> None:
        """Initialize empty error storage.

        Args:
            max_entries: Maximum number of errors to retain (default 100)
        """
        self._entries: List[ErrorEntry] = []
        self._max_entries = max_entries

    def append(self, entry: ErrorEntry) -> None:
        """Append error entry, evict oldest if limit exceeded."""
        self._entries.append(entry)
        # Enforce retention policy
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)  # Remove oldest (FIFO)

    def load_recent(self, limit: int = 10) -> List[ErrorEntry]:
        """Load most recent errors (reverse chronological order)."""
        if limit < 1:
            raise ValueError(f"Limit must be ≥ 1, got {limit}")
        # Return newest first (reverse order)
        return list(reversed(self._entries[-limit:]))
