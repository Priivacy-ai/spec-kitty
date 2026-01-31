"""Error logging system for tracking failed actions (Manus pattern)."""
from typing import List
from spec_kitty_events.storage import ErrorStorage
from spec_kitty_events.models import ErrorEntry


class ErrorLog:
    """Error log for systematic tracking of failed actions.

    This class provides a simple interface for logging errors and retrieving
    recent errors. All persistence is delegated to an ErrorStorage adapter.

    The Manus pattern encourages agents to learn from failed actions by
    maintaining a searchable log of errors and their resolutions.

    Attributes:
        storage: ErrorStorage adapter for persistence

    Example:
        >>> storage = InMemoryErrorStorage()
        >>> error_log = ErrorLog(storage)
        >>> error_log.log_error(ErrorEntry(
        ...     timestamp=datetime.now(),
        ...     action_attempted="Run pytest",
        ...     error_message="AssertionError: test failed"
        ... ))
        >>> errors = error_log.get_recent_errors(limit=10)
        >>> len(errors)
        1

    Note:
        Thread-safety is the responsibility of the ErrorStorage adapter.
    """

    def __init__(self, storage: ErrorStorage) -> None:
        """Initialize error log with storage adapter.

        Args:
            storage: ErrorStorage adapter for persistence
        """
        self._storage = storage

    def log_error(self, entry: ErrorEntry) -> None:
        """Log an error entry.

        Args:
            entry: ErrorEntry to persist

        Example:
            >>> error_log.log_error(ErrorEntry(
            ...     timestamp=datetime.now(),
            ...     action_attempted="Save file",
            ...     error_message="PermissionError: access denied"
            ... ))
        """
        self._storage.append(entry)

    def get_recent_errors(self, limit: int = 10) -> List[ErrorEntry]:
        """Retrieve most recent error entries.

        Args:
            limit: Maximum number of entries to retrieve (default 10)

        Returns:
            List of ErrorEntry objects in reverse chronological order (newest first)

        Raises:
            ValueError: If limit < 1

        Example:
            >>> errors = error_log.get_recent_errors(limit=5)
            >>> # Returns up to 5 most recent errors, newest first
        """
        return self._storage.load_recent(limit)
