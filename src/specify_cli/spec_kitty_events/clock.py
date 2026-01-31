"""Lamport logical clock implementation for causal ordering."""
from spec_kitty_events.storage import ClockStorage


class LamportClock:
    """Lamport logical clock for establishing causal ordering in distributed systems.

    Each node maintains its own clock. The clock increments on local events (tick)
    and synchronizes with remote clocks (update) using the max(local, remote) + 1 rule.

    Attributes:
        node_id: Unique identifier for this node
        storage: ClockStorage adapter for persistence

    Example:
        >>> storage = InMemoryClockStorage()
        >>> clock = LamportClock(node_id="alice", storage=storage)
        >>> clock.tick()  # Returns 1
        1
        >>> clock.tick()  # Returns 2
        2
        >>> clock.update(remote_clock=5)  # Sets to max(2, 5) + 1 = 6
        >>> clock.current()  # Returns 6 (no increment)
        6

    Note:
        Thread-safety is the responsibility of the ClockStorage adapter.
        This class does NOT provide thread-safe operations on its own.
        Clock values are expected to fit in a signed 64-bit range for
        interoperability. Python ints are unbounded, so overflow is
        practically impossible; exceeding 2^63 events is unrealistic.
    """

    def __init__(self, node_id: str, storage: ClockStorage) -> None:
        """Initialize clock (loads existing value from storage if present).

        Args:
            node_id: Unique identifier for this node
            storage: ClockStorage adapter for persistence
        """
        self.node_id = node_id
        self._storage = storage
        # Load existing clock value (returns 0 if never saved)
        self._counter = self._storage.load(node_id)

    def tick(self) -> int:
        """Increment clock by 1 for a local event.

        Returns:
            New clock value after increment

        Example:
            >>> clock.tick()
            1
            >>> clock.tick()
            2
        """
        self._counter += 1
        self._storage.save(self.node_id, self._counter)
        return self._counter

    def update(self, remote_clock: int) -> None:
        """Update clock based on received remote clock value.

        Sets local clock to max(local, remote) + 1 (per Lamport's algorithm).

        Args:
            remote_clock: Clock value from remote event

        Example:
            >>> clock = LamportClock("alice", storage)
            >>> clock.tick()  # local = 1
            1
            >>> clock.update(remote_clock=5)  # Sets to max(1, 5) + 1 = 6
            >>> clock.current()
            6
        """
        self._counter = max(self._counter, remote_clock) + 1
        self._storage.save(self.node_id, self._counter)

    def current(self) -> int:
        """Get current clock value without incrementing.

        Returns:
            Current clock value

        Example:
            >>> clock.current()
            5
            >>> clock.current()  # No increment
            5
        """
        return self._counter
