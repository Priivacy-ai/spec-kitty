"""Legacy layout detector — migration/upgrade namespace. Canonical import: specify_cli.upgrade.legacy_detector."""

from __future__ import annotations

from pathlib import Path

# Lane directories that indicate legacy format when they contain .md files
LEGACY_LANE_DIRS: list[str] = ["planned", "doing", "for_review", "done"]


def is_legacy_format(feature_path: Path) -> bool:
    """Check if feature uses legacy directory-based lanes.

    A feature is considered to use legacy format if:
    - It has a tasks/ subdirectory
    - Any of the lane subdirectories (planned/, doing/, for_review/, done/)
      exist AND contain at least one .md file

    Args:
        feature_path: Path to the feature directory (e.g., kitty-specs/007-feature/)

    Returns:
        True if legacy directory-based lanes detected, False otherwise.

    Note:
        Empty lane directories (containing only .gitkeep) are NOT considered
        legacy format - only directories with actual .md work package files.
    """
    tasks_dir = feature_path / "tasks"
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


__all__ = [
    # LEGACY_LANE_DIRS: demoted — no cross-module src/ callers (WP01).
    # get_legacy_lane_counts: demoted — no cross-module src/ from-import
    # callers (WP01 harden-dead-symbol-gate-01KW0RJR).
    "is_legacy_format",
]
