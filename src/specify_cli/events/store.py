"""
Event storage interface (stub for WP01).

This module will be fully implemented in WP02. For now, it provides
error handling for missing library dependencies.
"""

from pathlib import Path

from specify_cli.events import EventAdapter


class EventStore:
    """
    Event storage interface (stub for WP01).

    This class will be implemented in WP02 (Event Storage Foundation).
    For now, it validates that the spec-kitty-events library is available.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize EventStore.

        Args:
            repo_root: Root directory of the repository

        Raises:
            RuntimeError: If spec-kitty-events library is not installed
        """
        if not EventAdapter.check_library_available():
            raise RuntimeError(EventAdapter.get_missing_library_error())

        self.repo_root = repo_root
        # Actual implementation will be added in WP02
