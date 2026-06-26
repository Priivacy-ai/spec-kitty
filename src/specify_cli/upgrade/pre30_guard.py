"""Command-boundary guard for pre-3.0 project layout detection.

Raises Pre30LayoutError when a mission directory still uses lane-directory
layout (tasks/planned/, tasks/doing/, etc.). Called after feature_path is
resolved, before any WP mutation.
"""
from __future__ import annotations

from pathlib import Path

from specify_cli.upgrade.legacy_detector import is_legacy_format

__all__ = ["Pre30LayoutError", "check_pre30_layout"]


class Pre30LayoutError(Exception):
    """Raised when a pre-3.0 lane-directory layout is detected."""

    def __init__(self, feature_path: Path, detected_dirs: list[str]) -> None:
        self.feature_path = feature_path
        self.detected_dirs = detected_dirs
        lane_hint = detected_dirs[0] if detected_dirs else "tasks/{lane}/"
        super().__init__(
            f"Pre-3.0 layout detected (tasks/{lane_hint}/ directories or "
            f"frontmatter lane state).\n"
            f"Run `spec-kitty upgrade` to migrate before continuing."
        )


def check_pre30_layout(feature_path: Path) -> None:
    """Raise Pre30LayoutError if feature_path has a pre-3.0 lane-directory layout.

    Call this after feature_path is resolved but before any WP mutation.
    Returns None if the layout is post-3.0 (no exception raised).
    """
    if not is_legacy_format(feature_path):
        return
    tasks_dir = feature_path / "tasks"
    detected = [
        d.name
        for d in tasks_dir.iterdir()
        if d.is_dir() and list(d.glob("*.md"))
    ]
    raise Pre30LayoutError(feature_path=feature_path, detected_dirs=detected)
