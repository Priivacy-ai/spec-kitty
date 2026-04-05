"""Charter path resolution helpers for dashboard features/API."""

from __future__ import annotations

from pathlib import Path


def resolve_project_charter_path(project_dir: Path) -> Path | None:
    """Resolve the project-level charter file path.

    Returns the canonical charter path only. Does not fall back to legacy
    locations — those must be migrated via 'spec-kitty upgrade'.
    """
    charter_path = Path(project_dir) / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return charter_path
    return None
