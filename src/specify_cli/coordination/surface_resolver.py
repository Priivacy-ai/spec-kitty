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

from dataclasses import dataclass
from pathlib import Path

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.mission_metadata import load_meta
from specify_cli.missions._read_path_resolver import _compose_mission_dir
from specify_cli.missions.feature_dir_resolver import candidate_feature_dir_for_mission

_WORKTREES_SEGMENT = ".worktrees"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"


@dataclass(frozen=True)
class ResolvedStatusSurface:
    """Single-pass product of the canonical status-surface resolution.

    Carries both halves consumers need so neither re-derives the path (FR-005 /
    #1821):

    * ``surface_path`` — the canonical ``status.events.jsonl`` path (identical
      to :func:`resolve_status_surface`).
    * ``primary_anchor`` — the canonical primary feature-dir anchor
      (``candidate_feature_dir_for_mission``), the CWD-invariant authority the
      transaction-identity logic anchors on (#1737). Resolved exactly once and
      shared, so the historical validate-then-re-derive double resolution is
      gone.
    """

    surface_path: Path
    primary_anchor: Path

    @property
    def read_dir(self) -> Path:
        """Directory containing the resolved ``status.events.jsonl``."""
        return self.surface_path.parent


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

    Thin wrapper over :func:`resolve_status_surface_with_anchor` that discards
    the carried primary anchor. Retained as the canonical surface-path accessor;
    consumers that also need the CWD-invariant primary anchor (transaction
    identity, #1737) should call :func:`resolve_status_surface_with_anchor`
    instead of re-deriving it.

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    """
    return resolve_status_surface_with_anchor(repo_root, mission_slug).surface_path


def resolve_status_surface_with_anchor(
    repo_root: Path, mission_slug: str
) -> ResolvedStatusSurface:
    """Resolve the canonical status surface and primary anchor in one pass.

    Resolution is single-pass (FR-036): :func:`candidate_feature_dir_for_mission`
    — the coord-aware primitive that ``MissionStatus`` is also built on — is
    invoked **exactly once** and its result is carried as ``primary_anchor``.
    The surface path is derived from that same resolution:

    1. If the resolved dir is already inside a ``.worktrees/<m>-coord`` root, it
       is final — the surface lives there (never re-resolve; the #1772 nesting
       bug).
    2. Otherwise the resolver landed in the primary checkout. When that mission
       declares ``coordination_branch`` but the coord worktree is not yet
       materialized, compose the coord path **directly** (one derivation).

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    """
    feature_dir: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    meta = load_meta(feature_dir)
    if meta is None:
        if feature_dir.exists():
            return ResolvedStatusSurface(
                surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
                primary_anchor=feature_dir,
            )
        raise FileNotFoundError(
            f"meta.json not found for mission {mission_slug!r} at {feature_dir}"
        )

    # If the single coord-aware resolution already landed inside a coord
    # worktree, it is final — never resolve again (the #1772 nesting bug).
    if any(part == _WORKTREES_SEGMENT for part in feature_dir.parts):
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )

    raw_coord = meta.get("coordination_branch")
    coord_branch: str | None = str(raw_coord) if raw_coord else None
    if coord_branch is None:
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )

    # Coord branch declared but the worktree is not materialized yet: compose
    # the coord feature dir once, by hand, from the primary-checkout meta. The
    # primary anchor stays the canonical primary candidate (the create→first-
    # write window authority the transaction-identity logic expects).
    mid8: str = _coord_mid8(meta, mission_slug)
    dir_name: str = _compose_mission_dir(mission_slug, mid8)
    coord_root: Path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
    coord_feature_dir: Path = coord_root / KITTY_SPECS_DIR / dir_name
    return ResolvedStatusSurface(
        surface_path=coord_feature_dir / _STATUS_EVENTS_FILENAME,
        primary_anchor=feature_dir,
    )
