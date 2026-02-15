"""Lamport logical clock for event ordering."""

from pathlib import Path
import json
import os
import sys

# Cross-platform file locking
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def _lock_file(file_handle) -> None:
    """Acquire exclusive lock on file (cross-platform)."""
    if sys.platform == "win32":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(file_handle) -> None:
    """Release lock on file (cross-platform)."""
    if sys.platform == "win32":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


class LamportClock:
    """
    Lamport logical clock for event ordering.

    The clock value increments on every event emission, providing total order
    even across offline/online transitions.

    Clock state is persisted to ~/.spec-kitty/events/lamport_clock.json.
    """

    def __init__(self, node_id: str):
        """
        Initialize Lamport clock.

        Args:
            node_id: CLI node identifier (e.g., "cli-alice-macbook")
        """
        self.node_id = node_id
        self._clock_path = Path.home() / ".spec-kitty" / "events" / "lamport_clock.json"
        self._value = self._load()

    def _load(self) -> int:
        """Load clock value from disk (or 0 if file missing)."""
        if not self._clock_path.exists():
            return 0

        try:
            with open(self._clock_path, "r") as f:
                data = json.load(f)
                return data.get(self.node_id, 0)
        except (json.JSONDecodeError, IOError):
            return 0

    def _save(self) -> None:
        """Save clock value to disk (atomic write)."""
        self._clock_path.parent.mkdir(parents=True, exist_ok=True)

        # Load all node clocks (multi-node support)
        all_clocks = {}
        if self._clock_path.exists():
            try:
                with open(self._clock_path, "r") as f:
                    all_clocks = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Update this node's clock
        all_clocks[self.node_id] = self._value

        # Atomic write
        temp_path = self._clock_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            _lock_file(f)
            try:
                json.dump(all_clocks, f)
                f.flush()
                os.fsync(f.fileno())
            finally:
                _unlock_file(f)

        temp_path.replace(self._clock_path)

    def increment(self) -> int:
        """
        Increment clock and return new value.

        Returns:
            New clock value (monotonically increasing)
        """
        self._value += 1
        self._save()
        return self._value

    def update(self, received_clock: int) -> int:
        """
        Update clock with received value (Lamport algorithm).

        Args:
            received_clock: Clock value from received event

        Returns:
            New clock value (max(local, received) + 1)
        """
        self._value = max(self._value, received_clock) + 1
        self._save()
        return self._value

    def current(self) -> int:
        """
        Get current clock value without incrementing.

        Returns:
            Current clock value
        """
        return self._value
