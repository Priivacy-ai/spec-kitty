#!/usr/bin/env python3
"""Legacy format detection for Spec Kitty lane management.

This module provides utilities to detect whether a mission uses the old
directory-based lane structure (tasks/planned/, tasks/doing/, etc.) or
the new frontmatter-only lane system (flat tasks/ directory).
"""

from __future__ import annotations

from pathlib import Path

# Lane directories that indicate legacy format when they contain .md files
LEGACY_LANE_DIRS: list[str] = ["planned", "doing", "for_review", "done"]


def is_legacy_format(mission_path: Path) -> bool:
    """Check if mission uses legacy directory-based lanes.

    A mission is considered to use legacy format if:
    - It has a tasks/ subdirectory
    - Any of the lane subdirectories (planned/, doing/, for_review/, done/)
      exist AND contain at least one .md file

    Args:
        mission_path: Path to the mission directory (e.g., kitty-specs/007-mission/)

    Returns:
        True if legacy directory-based lanes detected, False otherwise.

    Note:
        Empty lane directories (containing only .gitkeep) are NOT considered
        legacy format - only directories with actual .md work package files.
    """
    tasks_dir = mission_path / "tasks"
    if not tasks_dir.exists():
        return False

    for lane in LEGACY_LANE_DIRS:
        lane_path = tasks_dir / lane
        if lane_path.is_dir():
            # Check if there are any .md files (not just .gitkeep)
            md_files = list(lane_path.glob("*.md"))
            if md_files:
                return True

    return False


def get_legacy_lane_counts(mission_path: Path) -> dict[str, int]:
    """Get count of work packages in each legacy lane directory.

    Useful for migration reporting and validation.

    Args:
        mission_path: Path to the mission directory

    Returns:
        Dictionary mapping lane names to count of .md files in each.
        Only includes lanes that have files.
    """
    tasks_dir = mission_path / "tasks"
    counts: dict[str, int] = {}

    if not tasks_dir.exists():
        return counts

    for lane in LEGACY_LANE_DIRS:
        lane_path = tasks_dir / lane
        if lane_path.is_dir():
            md_files = list(lane_path.glob("*.md"))
            if md_files:
                counts[lane] = len(md_files)

    return counts


__all__ = [
    "LEGACY_LANE_DIRS",
    "is_legacy_format",
    "get_legacy_lane_counts",
]
