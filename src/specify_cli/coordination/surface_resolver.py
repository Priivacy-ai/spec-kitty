"""Canonical status-surface resolver for Spec Kitty missions.

This module is the sole canonical path through which callers should resolve
the ``status.events.jsonl`` path for a mission. No secondary fallback or
alternative resolution mechanism should exist — any contributor reaching
for a parallel resolution path should treat this constraint as load-bearing
(NFR-003 compliance boundary).

Coord-topology resolution happens **exactly once** (FR-036). The coord-aware
:func:`candidate_feature_dir_for_mission` resolver already returns the
coordination-worktree feature dir whenever that worktree is materialized on
disk; this module therefore never re-invokes that resolver on an
already-resolved root. The only remaining case it handles directly is the
transitional window where ``meta.json`` declares ``coordination_branch`` but
the coord worktree has not been materialized yet — there it composes the coord
path **once**, by hand, rather than resolving a second time. Re-running the
coord-aware resolver against a coord root nested
``.worktrees/<m>-coord/.worktrees/<m>-coord/…`` (the #1772 double-resolution
bug); building the path directly avoids that.
"""
from __future__ import annotations

from pathlib import Path

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.mission_metadata import load_meta
from specify_cli.missions._read_path_resolver import _compose_mission_dir
from specify_cli.missions.feature_dir_resolver import candidate_feature_dir_for_mission

_WORKTREES_SEGMENT = ".worktrees"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"


def _coord_mid8(meta: dict[str, object], mission_slug: str) -> str:
    """Derive the coord-worktree mid8 from meta, mirroring the read resolver."""
    raw_mid8 = meta.get("mid8")
    raw_mission_id = meta.get("mission_id")
    if raw_mid8:
        return str(raw_mid8)
    if raw_mission_id and len(str(raw_mission_id)) >= 8:
        return str(raw_mission_id)[:8]
    return (mission_slug.replace("-", "") + "00000000")[:8]


def resolve_status_surface(repo_root: Path, mission_slug: str) -> Path:
    """Return the canonical status.events.jsonl path for the given mission.

    Resolution is single-pass (FR-036):

    1. :func:`candidate_feature_dir_for_mission` is the coord-aware resolver and
       already returns the coordination-worktree feature dir when that worktree
       exists. If the resolved dir is already inside a ``.worktrees/<m>-coord``
       root, it is final — return it as-is.
    2. Otherwise the resolver landed in the primary checkout. When that mission
       declares ``coordination_branch`` but the coord worktree is not yet
       materialized, compose the coord path **directly** (one derivation), so we
       never re-resolve and nest ``.worktrees`` (#1772).

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    """
    feature_dir: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    meta = load_meta(feature_dir)
    if meta is None:
        if feature_dir.exists():
            return feature_dir / _STATUS_EVENTS_FILENAME
        raise FileNotFoundError(
            f"meta.json not found for mission {mission_slug!r} at {feature_dir}"
        )

    # If the single coord-aware resolution already landed inside a coord
    # worktree, it is final — never resolve again (the #1772 nesting bug).
    if any(part == _WORKTREES_SEGMENT for part in feature_dir.parts):
        return feature_dir / _STATUS_EVENTS_FILENAME

    raw_coord = meta.get("coordination_branch")
    coord_branch: str | None = str(raw_coord) if raw_coord else None
    if coord_branch is None:
        return feature_dir / _STATUS_EVENTS_FILENAME

    # Coord branch declared but the worktree is not materialized yet: compose
    # the coord feature dir once, by hand, from the primary-checkout meta.
    mid8: str = _coord_mid8(meta, mission_slug)
    dir_name: str = _compose_mission_dir(mission_slug, mid8)
    coord_root: Path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
    coord_feature_dir: Path = coord_root / KITTY_SPECS_DIR / dir_name
    return coord_feature_dir / _STATUS_EVENTS_FILENAME
