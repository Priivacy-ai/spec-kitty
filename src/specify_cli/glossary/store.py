"""In-memory glossary store backed by event log."""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from .models import TermSense


class GlossaryStore:
    """In-memory glossary store backed by event log."""

    def __init__(self, event_log_path: Path):
        self.event_log_path = event_log_path
        self._cache: Dict[str, Dict[str, List[TermSense]]] = {}
        # Format: {scope: {surface: [senses]}}

    def load_from_events(self) -> None:
        """Rebuild glossary from event log."""
        # Read GlossarySenseUpdated events from log
        # Populate self._cache
        pass  # WP08 will implement event reading

    def add_sense(self, sense: TermSense) -> None:
        """
        Add a sense to the store.

        Args:
            sense: TermSense to add
        """
        scope = sense.scope
        surface = sense.surface.surface_text

        if scope not in self._cache:
            self._cache[scope] = {}
        if surface not in self._cache[scope]:
            self._cache[scope][surface] = []

        self._cache[scope][surface].append(sense)

    def lookup(self, surface: str, scopes: tuple) -> List[TermSense]:
        """
        Look up term in scope hierarchy.

        Args:
            surface: Term surface text (normalized)
            scopes: Tuple of scope names in precedence order

        Returns:
            List of matching TermSense objects in scope order
        """
        # Clear cache for this method (new implementation uses dict directly)
        results = []
        for scope in scopes:
            if scope in self._cache and surface in self._cache[scope]:
                results.extend(self._cache[scope][surface])
        return results
