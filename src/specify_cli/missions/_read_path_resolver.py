"""Mission read-path resolution (WP08 T037, FR-030).

Read-side CLI commands — ``spec-kitty agent tasks status``,
``agent context resolve``, ``agent decision verify`` — must locate
``status.events.jsonl`` / ``status.json`` / ``decisions/index.json``
regardless of the operator's current working directory.  The truth lives
in one of two places depending on mission topology:

* **New topology** (post-WP03): the coordination worktree at
  ``<repo_root>/.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/``.
  All lane processes write through ``BookkeepingTransaction``, which
  commits to that worktree; lanes themselves do not carry the status
  files (sparse-checkout policy excludes them).
* **Legacy mission** (pre-WP03): no coord worktree exists.  The status
  files live in the primary checkout at
  ``<repo_root>/kitty-specs/<slug>[-<mid8>]/``.

The resolver returns the directory containing those files.  It does
**not** assert their presence — the caller decides whether absence is
an error (and surfaces ``STATUS_READ_PATH_NOT_FOUND`` accordingly).

Spec source: FR-030, SC-02.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import json
from pathlib import Path


STATUS_READ_PATH_NOT_FOUND_CODE = "STATUS_READ_PATH_NOT_FOUND"


class StatusReadPathNotFound(Exception):
    """Neither the coordination worktree nor the primary checkout carries
    the requested mission directory.

    Carries a stable ``error_code`` (``STATUS_READ_PATH_NOT_FOUND``) so
    callers can route on it without string parsing.
    """

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
    """Return ``<slug>-<mid8>`` but avoid double-suffixing.

    Mirrors :func:`specify_cli.coordination.workspace._compose_mission_dir`
    so the two paths stay in lock-step.  ``mission_slug`` may be either
    the bare human slug (legacy) or the post-WP03 ``<human>-<mid8>``
    slug.
    """
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
    """Return the directory containing this mission's status read surface.

    Priority:

    1. Coordination worktree (new topology) — chosen when its directory
       exists on disk.  This is the canonical reader path for any
       mission whose ``meta.json`` carries ``coordination_branch``.
    2. Primary checkout view — chosen when no coord worktree exists.
       This serves legacy missions and the transitional window between
       ``mission create`` and the first coord-worktree materialisation.

    The function is **pure-path on the happy path**: it does not touch
    git, does not spawn subprocesses, and does not invoke any heavy
    lookup that would meaningfully extend the cost of a status read.
    It performs at most one filesystem stat per candidate.

    Args:
        repo_root: Absolute repository root (primary checkout).
        mission_slug: Mission slug, either bare human form or
            ``<human>-<mid8>`` (post-WP03).  The resolver normalises.
        mid8: 8-character mission disambiguator; may be empty for
            legacy missions that never minted a ``mission_id``.
        require_exists: When ``True``, raise
            :class:`StatusReadPathNotFound` if neither candidate exists
            on disk.  Defaults to ``False`` so the caller can decide
            how to render the diagnostic.

    Returns:
        Absolute path to the mission directory containing
        ``status.events.jsonl`` / ``status.json``.

    Raises:
        StatusReadPathNotFound: When ``require_exists`` is ``True`` and
            neither the coord worktree nor the primary checkout carries
            the mission directory.
    """
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)

    # Candidate 1: coordination worktree (new topology).  We only build
    # the path when mid8 is present — coord worktree naming requires it.
    coord_candidate: Path | None = None
    coord_worktree_materialized = False
    if mid8:
        # Lazy import breaks the import cycle: ``coordination.__init__`` eagerly
        # imports ``surface_resolver``, which imports ``_compose_mission_dir``
        # from this module. A module-level import here would deadlock whenever
        # this resolver is the first entry point into the coordination package.
        from specify_cli.coordination.workspace import CoordinationWorkspace

        coord_root = CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, mid8,
        )
        # #1718 Fix C: distinguish "coord worktree materialized" from "coord
        # branch merely declared". The scaffold writes coordination_branch into
        # meta.json at mission-create time but defers worktree materialization
        # to the first coord write, so there is a legitimate window where the
        # worktree does not exist yet.
        coord_worktree_materialized = coord_root.exists()
        coord_candidate = coord_root / KITTY_SPECS_DIR / mission_dir_name
        if coord_candidate.exists():
            return coord_candidate

    # Candidate 2: primary checkout (legacy + early lifecycle).  Fail closed
    # only when the coord worktree is *materialized* (so falling back to the
    # primary would expose stale/empty status files). When the coord branch is
    # declared but the worktree has not been created yet, the primary checkout
    # is the only place the bootstrap status events live — read it (#1718).
    primary_candidate = repo_root / KITTY_SPECS_DIR / mission_dir_name
    if primary_candidate.exists():
        if (
            coord_candidate is not None
            and coord_worktree_materialized
            and _declares_coordination_branch(primary_candidate)
        ):
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

    # Default: return the primary candidate so the caller can render its
    # own diagnostic (e.g. "Mission directory not found: <path>").
    return primary_candidate


__all__ = [
    "STATUS_READ_PATH_NOT_FOUND_CODE",
    "StatusReadPathNotFound",
    "resolve_mission_read_path",
]
