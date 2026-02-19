"""Internal runtime engine helpers used by tests."""

from __future__ import annotations

from pathlib import Path

from ._state import read_snapshot
from .models import Snapshot



def _read_snapshot(run_dir: Path) -> Snapshot:
    """Read current run snapshot from ``state.json``."""
    return read_snapshot(run_dir)
