"""Constitution path resolution helpers for dashboard features/API."""

from __future__ import annotations

from pathlib import Path


def resolve_project_constitution_path(project_dir: Path) -> Path | None:
    """Resolve the project-level constitution file path.

    Resolution order:
    1. .kittify/constitution/constitution.md (canonical)
    2. .kittify/memory/constitution.md (legacy)
    """
    project_root = Path(project_dir)
    candidate_paths = (
        project_root / ".kittify" / "constitution" / "constitution.md",
        project_root / ".kittify" / "memory" / "constitution.md",
    )

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    return None
