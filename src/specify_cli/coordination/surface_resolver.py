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
from specify_cli.lanes.branch_naming import mid8_from_slug
from specify_cli.mission_metadata import load_meta
from specify_cli.missions._read_path_resolver import (
    StatusReadPathNotFound,
    _compose_mission_dir,
    primary_feature_dir_for_mission,
)
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


def _coord_mid8(meta: dict[str, object], mission_slug: str, repo_root: Path) -> str:
    """Derive the coord-worktree mid8 from declared authority, or fail closed.

    Cascade of declared sources (post-083 ``meta.json`` is authoritative):
    ``meta.mid8`` → ``meta.mission_id[:8]`` → the mid8 embedded in the canonical
    ``<slug>-<mid8>`` directory name. When every declared source is exhausted the
    disambiguator is genuinely lost, and composing a coord path would mis-route
    to a wrong-but-plausible surface. Per the 3.x execution invariant ("raises
    rather than silently falling back on unresolvable context"; F-001: never
    compose a wrong-but-plausible coord path), this raises a structured
    :class:`StatusReadPathNotFound` instead of fabricating a mid8.
    """
    raw_mid8 = meta.get("mid8")
    raw_mission_id = meta.get("mission_id")
    if raw_mid8:
        return str(raw_mid8)
    if raw_mission_id and len(str(raw_mission_id)) >= 8:
        return str(raw_mission_id)[:8]
    # The canonical ``<slug>-<mid8>`` directory name carries the real mid8.
    slug_mid8: str = mid8_from_slug(mission_slug)
    if slug_mid8:
        return slug_mid8
    # Cascade exhausted: no declared source carries the disambiguator. Fail
    # closed rather than fabricate a wrong-but-plausible mid8 (FR-005 / F-001).
    raise StatusReadPathNotFound(
        repo_root=repo_root,
        mission_slug=mission_slug,
        mid8="",
        coord_candidate=CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, ""
        )
        / KITTY_SPECS_DIR
        / mission_slug,
        primary_candidate=repo_root / KITTY_SPECS_DIR / mission_slug,
    )


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
       materialized, compose the coord path **directly** (one derivation). If the
       coord worktree root *is* materialized but lacks the mission dir, fail
       closed with :class:`StatusReadPathNotFound` rather than handing back a
       primary surface — the silent fallback is the #1589/#1821 split-brain
       class this resolver exists to kill (FR-005). The bare-slug path used to
       lose this signal because :func:`candidate_feature_dir_for_mission`
       derives mid8 from the *slug* (empty for a bare slug), so the
       materialization check never fired; here mid8 comes from ``meta`` so the
       check holds for both bare and ``<slug>-<mid8>`` handles.

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    Raises StatusReadPathNotFound when the coord worktree is materialized but
        its mission dir is absent, or when the coord-worktree mid8 cannot be
        derived from any declared source (fail closed — never fabricate a mid8).
    """
    feature_dir: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    # F-001: the candidate resolution above is the single canonicalization
    # point — a mid8 / ULID / numeric-prefix handle lands on the real mission
    # directory, whose NAME is the canonical mission-dir name. Every downstream
    # composition (the primary re-anchor, the coord-path assembly) consumes
    # that canonical name; re-anchoring on the raw operator handle is exactly
    # the wrong-but-plausible ``kitty-specs/<mid8>/`` surface this resolver
    # must never hand back. (For unresolvable handles the candidate's name
    # equals the raw handle, so the not-found behaviour is unchanged.)
    mission_slug = feature_dir.name
    meta = load_meta(feature_dir)

    # If the single coord-aware resolution already landed inside a coord
    # worktree that carries its own meta, it is final — never resolve again (the
    # #1772 nesting bug).
    if meta is not None and any(
        part == _WORKTREES_SEGMENT for part in feature_dir.parts
    ):
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )

    # FR-003 cascade layer 1: config must be readable BEFORE topology can be
    # resolved. ``coordination_branch`` lives in the PRIMARY-checkout meta.json;
    # the coord worktree's mission dir has none. When ``candidate_feature_dir``
    # prefers a materialized coord worktree, ``load_meta`` above silently
    # returns None and the resolver historically handed back the coord path as
    # ``primary_anchor`` with no coord/primary distinction — losing the config
    # signal and flipping topology classification (the #1589/#1821 split-brain
    # the write path then inherits via ``_identity_for_request``). Re-anchor the
    # config read on the canonical primary dir so the surface authority is
    # config-determined, never topology-determined-then-config-lost.
    primary_dir: Path = primary_feature_dir_for_mission(repo_root, mission_slug)
    if meta is None:
        meta = load_meta(primary_dir)
    if meta is None:
        if primary_dir.exists():
            return ResolvedStatusSurface(
                surface_path=primary_dir / _STATUS_EVENTS_FILENAME,
                primary_anchor=primary_dir,
            )
        if feature_dir.exists():
            return ResolvedStatusSurface(
                surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
                primary_anchor=feature_dir,
            )
        raise FileNotFoundError(
            f"meta.json not found for mission {mission_slug!r} at {feature_dir}"
        )

    # Config is now in hand. The canonical primary anchor is the topology-blind
    # primary dir (the create→first-write window authority the transaction
    # identity logic expects), not the coord-preferring candidate.
    feature_dir = primary_dir

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
    mid8: str = _coord_mid8(meta, mission_slug, repo_root)
    dir_name: str = _compose_mission_dir(mission_slug, mid8)
    coord_root: Path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
    coord_feature_dir: Path = coord_root / KITTY_SPECS_DIR / dir_name
    # Fail closed: the coord worktree root is materialized but its mission dir is
    # absent → reading the primary checkout would expose a stale, split-brain
    # status surface (#1589/#1821). Before materialization the composed coord
    # path is returned as-is; the create→first-write window keeps the primary
    # checkout authoritative one level up (the aggregate's not-yet-materialized
    # gate). FR-005.
    if coord_root.exists() and not coord_feature_dir.exists():
        raise StatusReadPathNotFound(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8,
            coord_candidate=coord_feature_dir,
            primary_candidate=feature_dir,
        )
    return ResolvedStatusSurface(
        surface_path=coord_feature_dir / _STATUS_EVENTS_FILENAME,
        primary_anchor=feature_dir,
    )
