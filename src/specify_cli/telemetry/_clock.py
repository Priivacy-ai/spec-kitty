"""File-backed Lamport clock storage for telemetry."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from specify_cli.spec_kitty_events.storage import ClockStorage

logger = logging.getLogger(__name__)


class FileClockStorage(ClockStorage):
    """Persist Lamport clock values in a JSON file.

    File format: ``{"node_id": clock_value, ...}``
    Returns 0 for unknown or corrupt entries.
    """

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def load(self, node_id: str) -> int:
        """Load clock value for *node_id*, returning 0 if missing or corrupt."""
        if not self._file_path.exists():
            return 0
        try:
            data = json.loads(self._file_path.read_text(encoding="utf-8"))
            value = data.get(node_id, 0)
            return int(value) if isinstance(value, (int, float)) else 0
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            logger.warning("Corrupt clock file %s – returning 0", self._file_path)
            return 0

    def save(self, node_id: str, clock_value: int) -> None:
        """Persist *clock_value* for *node_id*."""
        if clock_value < 0:
            raise ValueError(f"Clock value must be ≥ 0, got {clock_value}")

        data: dict[str, int] = {}
        if self._file_path.exists():
            try:
                data = json.loads(self._file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, TypeError, ValueError, OSError):
                data = {}

        data[node_id] = clock_value
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(data, sort_keys=True), encoding="utf-8"
        )
