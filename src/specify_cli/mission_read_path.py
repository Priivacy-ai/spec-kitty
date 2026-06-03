"""Lightweight mission read-path resolution.

This module intentionally lives outside ``specify_cli.missions``. Importing
that package executes its compatibility facade and loads the charter stack,
which is too expensive for ``spec-kitty next`` startup.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.coordination.workspace import CoordinationWorkspace


STATUS_READ_PATH_NOT_FOUND_CODE = "STATUS_READ_PATH_NOT_FOUND"


class StatusReadPathNotFound(Exception):
    """Neither coord worktree nor primary checkout carries the mission dir."""

    error_code: str = STATUS_READ_PATH_NOT_FOUND_CODE

    def __init__(
        self,
        *,
        repo_root: Path,
        mission_slug: str,
        mid8: str,
        coord_candidate: Path,
        primary_candidate: Path,
    ) -> None:
        self.repo_root = repo_root
        self.mission_slug = mission_slug
        self.mid8 = mid8
        self.coord_candidate = coord_candidate
        self.primary_candidate = primary_candidate
        super().__init__(
            f"Status read path not found for {mission_slug!r} "
            f"(mid8={mid8!r}): checked {coord_candidate} and "
            f"{primary_candidate}"
        )


def _declares_coordination_branch(path: Path) -> bool:
    meta_path = path / "meta.json"
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    branch = meta.get("coordination_branch") if isinstance(meta, dict) else None
    return isinstance(branch, str) and bool(branch.strip())


def _compose_mission_dir(mission_slug: str, mid8: str) -> str:
    if mid8 and mission_slug.endswith(f"-{mid8}"):
        return mission_slug
    if mid8:
        return f"{mission_slug}-{mid8}"
    return mission_slug


def resolve_mission_read_path(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    require_exists: bool = False,
) -> Path:
    """Return dir containing this mission's status read surface."""
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)

    coord_candidate: Path | None = None
    if mid8:
        coord_root = CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, mid8,
        )
        coord_candidate = coord_root / "kitty-specs" / mission_dir_name
        if coord_candidate.exists():
            return coord_candidate

    primary_candidate = repo_root / "kitty-specs" / mission_dir_name
    if primary_candidate.exists():
        if coord_candidate is not None and _declares_coordination_branch(primary_candidate):
            raise StatusReadPathNotFound(
                repo_root=repo_root,
                mission_slug=mission_slug,
                mid8=mid8 or "",
                coord_candidate=coord_candidate,
                primary_candidate=primary_candidate,
            )
        return primary_candidate

    if require_exists:
        raise StatusReadPathNotFound(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8 or "",
            coord_candidate=coord_candidate
            if coord_candidate is not None
            else primary_candidate,
            primary_candidate=primary_candidate,
        )

    return primary_candidate


__all__ = [
    "resolve_mission_read_path",
]
