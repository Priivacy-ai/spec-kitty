"""Charter path resolution helpers for dashboard features/API."""

from __future__ import annotations

from pathlib import Path


def resolve_project_charter_path(project_dir: Path) -> Path | None:
    """Resolve the project-level charter file path.

    Resolution order:
    1. .kittify/charter/charter.md (canonical)
    2. .kittify/memory/charter.md (legacy)
    """
    project_root = Path(project_dir)
    candidate_paths = (
        project_root / ".kittify" / "charter" / "charter.md",
        project_root / ".kittify" / "memory" / "charter.md",
    )

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    return None
