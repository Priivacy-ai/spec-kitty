"""Canonical status-surface resolver for Spec Kitty missions.

This module is the sole canonical path through which callers should resolve
the ``status.events.jsonl`` path for a mission. No secondary fallback or
alternative resolution mechanism should exist — any contributor reaching
for a parallel resolution path should treat this constraint as load-bearing
(NFR-003 compliance boundary).
"""
from __future__ import annotations

from pathlib import Path

from specify_cli.mission_metadata import load_meta

_KITTY_SPECS_DIR = "kitty-specs"
_WORKTREES_DIR = ".worktrees"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"


def _mission_dir_name(mission_slug: str, mid8: str) -> str:
    """Return the kitty-specs subdirectory name, deduplicating the mid8 suffix."""
    if mission_slug.endswith(f"-{mid8}"):
        return mission_slug
    return f"{mission_slug}-{mid8}"


def resolve_status_surface(repo_root: Path, mission_slug: str) -> Path:
    """Return the canonical status.events.jsonl path for the given mission.

    Routes to the coordination worktree when ``coordination_branch`` is set
    in the mission's ``meta.json``; otherwise returns the primary-checkout path.
    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    """
    feature_dir = repo_root / _KITTY_SPECS_DIR / mission_slug
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(
            f"meta.json not found for mission {mission_slug!r} at {feature_dir}"
        )
    raw_coord = meta.get("coordination_branch")
    coord_branch: str | None = str(raw_coord) if raw_coord else None
    if coord_branch is None:
        return repo_root / _KITTY_SPECS_DIR / mission_slug / _STATUS_EVENTS_FILENAME
    raw_mid8 = meta.get("mid8")
    raw_mission_id = meta.get("mission_id")
    mid8: str
    if raw_mid8:
        mid8 = str(raw_mid8)
    elif raw_mission_id and len(str(raw_mission_id)) >= 8:
        mid8 = str(raw_mission_id)[:8]
    else:
        mid8 = (mission_slug.replace("-", "") + "00000000")[:8]
    dir_name = _mission_dir_name(mission_slug, mid8)
    worktree_root = repo_root / _WORKTREES_DIR / f"{dir_name}-coord"
    return worktree_root / _KITTY_SPECS_DIR / dir_name / _STATUS_EVENTS_FILENAME
