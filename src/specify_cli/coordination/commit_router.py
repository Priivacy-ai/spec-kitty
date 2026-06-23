"""Mission-aware planning-commit router (FR-001/002/005).

Extracted from ``cli/commands/agent/mission.py`` to provide a single canonical
``commit_for_mission`` entry point that:

1. Resolves the placement via ``mission_runtime.resolve_placement_only``.
2. If the resolved placement is COORDINATION and the policy marks the target ref
   as protected, materialises the coordination worktree on demand and stages the
   artifacts there before committing.
3. Otherwise commits directly to the primary checkout (flattened / unprotected).

This module owns the extraction described in WP02 / IC-02. The three formerly
open-coded inline commit tails in ``mission.py`` (gap-analysis, generator-config,
finalize-tasks) are folded into this entry point (T027 / #2056).

Design basis: ``plan.md`` (IC-02), ADR ``2026-06-21-1``.

C-001 (no parallel materialiser): every coordination worktree materialisation
goes through the single canonical ``CoordinationWorkspace.resolve()`` path.
NFR-001 (#1718 create-window): materialisation happens at the COMMIT boundary,
not at read time.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from mission_runtime import (
    CommitTarget,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.git import safe_commit


@runtime_checkable
class _ProtectionPolicyProtocol(Protocol):
    """Structural protocol for the ProtectionPolicy duck-type used by commit_for_mission.

    Avoids a hard circular import (commit_router → protection_policy → git →
    commit_helpers) by matching on structure rather than on the concrete class.
    """

    def is_protected(self, ref: str) -> bool: ...

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommitRouterResult:
    """Typed outcome of :func:`commit_for_mission`.

    status values:
    - ``"committed"``        — ``safe_commit`` landed a real commit.
    - ``"unchanged"``        — benign no-op: artifact present + already committed.
    - ``"no_op_wrong_surface"`` — artifact absent at resolved placement.
    - ``"error"``            — commit failed unexpectedly.
    """

    status: Literal["committed", "unchanged", "no_op_wrong_surface", "error"]
    placement_ref: str
    commit_hash: str | None = None
    diagnostic: str | None = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def commit_for_mission(
    repo_root: Path,
    mission_slug: str,
    files: tuple[Path, ...],
    message: str,
    policy: _ProtectionPolicyProtocol,
    *,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
    target_branch: str | None = None,
) -> CommitRouterResult:
    """Commit planning artifacts to the mission's resolved placement.

    This is the single canonical commit entry point for all planning-phase
    artifacts (spec, plan, tasks, gap-analysis, generator-config). It replaces
    the formerly open-coded inline tails in ``agent/mission.py``.

    Args:
        repo_root:   Primary checkout root (where ``kitty-specs/`` lives).
        mission_slug: Mission handle (e.g. ``"001-my-mission"``).
        files:       Absolute paths of artifacts to commit.
        message:     Commit message.
        policy:      A :class:`~specify_cli.git.protection_policy.ProtectionPolicy`
                     instance (accepted via the structural
                     :class:`_ProtectionPolicyProtocol` to avoid a circular import;
                     duck-typed via ``is_protected``).
        primary_paths_created_this_invocation: Paths the caller materialised this
                     invocation (eligible for residue cleanup after staging, R6).
        target_branch: Short primary branch name for the post-commit ff-advance
                     (WP09 / FR-010 / #1878). Optional; advance is skipped when
                     ``None``.

    Returns:
        :class:`CommitRouterResult` with the typed outcome.
    """
    placement: CommitTarget = resolve_placement_only(repo_root, mission_slug)

    # Determine whether the placement needs coordination routing. The decision
    # reads the WP02 STORED topology via the ONE canonical predicate (FR-005 /
    # FR-001b) — never a per-ref ``.kind`` (the retired transitional arm). A
    # coord-routing topology materialises the coord worktree (C-001); the policy
    # is still checked to guard against committing directly to a protected PRIMARY
    # ref on a flattened/primary placement (FR-005).
    use_coord = routes_through_coordination(resolve_topology(repo_root, mission_slug))

    if not use_coord and policy.is_protected(placement.ref):
        # Flattened or primary placement on a protected ref — surface a refusal
        # with the actionable recover command (T008) rather than an opaque error.
        return CommitRouterResult(
            status="no_op_wrong_surface",
            placement_ref=placement.ref,
            diagnostic=(
                f"Refusing direct commit to protected ref '{placement.ref}'. "
                f"Run 'spec-kitty spec-commit --mission {mission_slug} ...' to "
                f"route through the coordination worktree."
            ),
        )

    if use_coord:
        worktree_root, commit_paths = _materialise_coord_worktree(
            repo_root,
            mission_slug,
            placement,
            files,
            primary_paths_created_this_invocation=primary_paths_created_this_invocation,
        )
    else:
        # Flattened or unprotected primary: commit directly.
        worktree_root, commit_paths = repo_root, files

    if not commit_paths:
        # All artifacts already committed (or none present) — genuine no-op.
        return CommitRouterResult(status="unchanged", placement_ref=placement.ref)

    # FR-006 / D-5: detect no-op against the wrong surface.
    if _any_path_absent(commit_paths):
        diagnostic = (
            f"Artifact(s) not present at resolved placement "
            f"({placement.ref}, worktree={worktree_root}); commit would no-op "
            f"against the wrong surface and was not created."
        )
        return CommitRouterResult(
            status="no_op_wrong_surface",
            placement_ref=placement.ref,
            diagnostic=diagnostic,
        )

    try:
        commit_result = safe_commit(
            repo_root=repo_root,
            worktree_root=worktree_root,
            target=placement,
            message=message,
            paths=commit_paths,
        )
    except subprocess.CalledProcessError as exc:
        stderr = getattr(exc, "stderr", "") or ""
        if "nothing to commit" in stderr or "nothing added to commit" in stderr:
            return CommitRouterResult(status="unchanged", placement_ref=placement.ref)
        return CommitRouterResult(
            status="error",
            placement_ref=placement.ref,
            diagnostic=str(exc),
        )
    except RuntimeError as exc:
        if _is_empty_changeset_error(exc):
            return CommitRouterResult(status="unchanged", placement_ref=placement.ref)
        return CommitRouterResult(
            status="error",
            placement_ref=placement.ref,
            diagnostic=str(exc),
        )

    commit_hash: str | None = None
    if commit_result is not None and hasattr(commit_result, "sha"):
        commit_hash = commit_result.sha

    # WP09 / FR-010 (#1878): best-effort ff-advance after a coord write.
    if use_coord and target_branch:
        _try_advance_ref(repo_root, target_branch, worktree_root)

    return CommitRouterResult(
        status="committed",
        placement_ref=placement.ref,
        commit_hash=commit_hash,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _materialise_coord_worktree(
    repo_root: Path,
    mission_slug: str,
    _placement: object,
    files: tuple[Path, ...],
    *,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
) -> tuple[Path, tuple[Path, ...]]:
    """Resolve (materialise on demand) the coordination worktree and stage artifacts.

    Reuses the canonical ``CoordinationWorkspace.resolve()`` path (C-001).
    Falls back to the primary checkout on any resolution error so the lifecycle
    does not crash (C-004 strangler safety).

    Args:
        repo_root:    Primary checkout root.
        mission_slug: Mission slug for workspace resolution.
        _placement:   The resolved :class:`~mission_runtime.CommitTarget`; passed
                      for interface symmetry with ``commit_for_mission`` and
                      future callers. Resolution goes through
                      ``CoordinationWorkspace`` internally.
        files:        Artifacts to stage in the coord worktree.
        primary_paths_created_this_invocation: Eligible residue paths (R6).

    Returns:
        ``(coord_worktree, coord_paths)`` on success; ``(repo_root, files)`` on error.
    """
    from specify_cli.coordination.workspace import CoordinationWorkspace

    mid8 = _resolve_mid8(repo_root, mission_slug)
    if mid8 is None:
        return repo_root, files

    try:
        coord_wt = CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)
    except Exception:
        logger.debug(
            "commit_router: CoordinationWorkspace.resolve failed for %s; "
            "falling back to primary checkout",
            mission_slug,
        )
        return repo_root, files

    coord_paths = _stage_artifacts_in_coord_worktree(
        list(files),
        coord_wt,
        repo_root,
        primary_paths_created_this_invocation=primary_paths_created_this_invocation,
    )
    return coord_wt, tuple(coord_paths)


def _resolve_mid8(repo_root: Path, mission_slug: str) -> str | None:
    """Load meta.json and derive mid8 for worktree resolution."""
    try:
        from specify_cli.lanes.branch_naming import resolve_mid8
        from specify_cli.mission_metadata import load_meta
        from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission

        feature_dir = primary_feature_dir_for_mission(repo_root, mission_slug)
        meta = load_meta(feature_dir, allow_missing=True, on_malformed="none")
        raw_mid = meta.get("mission_id") if meta else None
        if not isinstance(raw_mid, str) or len(raw_mid) < 8:
            return None
        result: str | None = resolve_mid8(mission_slug, mission_id=raw_mid)
        return result
    except Exception:
        return None


def _stage_artifacts_in_coord_worktree(
    files: list[Path],
    coord_worktree: Path,
    repo_root: Path,
    *,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
) -> list[Path]:
    """Copy artifacts from the primary checkout to the coordination worktree.

    Mirrors ``_stage_finalize_artifacts_in_coord_worktree`` in ``mission.py``
    (the canonical source of this logic), including:
    - Skipping ``COORD_OWNED_STATUS_FILES`` (#1589).
    - Skipping worktrees-nested paths (#FR-035).
    - Residue cleanup for ``primary_paths_created_this_invocation`` (R6 / #1814).
    """
    from specify_cli.coordination.surface_resolver import is_under_worktrees_segment
    from specify_cli.status import COORD_OWNED_STATUS_FILES

    coord_files: list[Path] = []
    staged_sources: list[tuple[Path, Path]] = []

    for src in files:
        if src.name in COORD_OWNED_STATUS_FILES:
            continue
        rel = src.relative_to(repo_root)
        if is_under_worktrees_segment(rel):
            try:
                coord_rel = src.resolve().relative_to(coord_worktree.resolve())
            except ValueError:
                continue
            if is_under_worktrees_segment(coord_rel):
                continue
            coord_files.append(src)
            continue
        dst = coord_worktree / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            staged_sources.append((src, dst))
        coord_files.append(dst)

    if primary_paths_created_this_invocation:
        for src, dst in staged_sources:
            if src not in primary_paths_created_this_invocation:
                continue
            if not src.exists() or not dst.exists():
                continue
            try:
                if src.read_bytes() != dst.read_bytes():
                    logger.warning(
                        "commit_router: residue cleanup skipped %s: primary copy diverged",
                        src.relative_to(repo_root),
                    )
                    continue
                src.unlink()
            except OSError as exc:
                logger.warning(
                    "commit_router: residue cleanup failed for %s: %s",
                    src.relative_to(repo_root),
                    exc,
                )

    return coord_files


def _any_path_absent(paths: tuple[Path, ...]) -> bool:
    """Return True iff any path in *paths* does not exist on disk."""
    return any(not path.exists() for path in paths)


def _is_empty_changeset_error(exc: RuntimeError) -> bool:
    return str(exc).startswith("safe_commit: git commit failed")


def _try_advance_ref(
    repo_root: Path,
    primary_branch: str,
    coord_worktree: Path,
) -> None:
    """Best-effort fast-forward of *primary_branch* to the coord HEAD (#1878).

    ``advance_branch_ref`` advances the ref to a *SHA* (it does not accept a
    worktree path), so resolve the coordination worktree's HEAD here first.
    Coordination status residue on the primary checkout is legitimate after a
    coord-branch write, so exclude it from the dirty gate
    (#1878 / FR-012) — mirrors the merge-pipeline call sites.
    """
    try:
        from specify_cli.git.ref_advance import advance_branch_ref
        from specify_cli.status import COORD_OWNED_STATUS_FILES

        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(coord_worktree),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        advance_branch_ref(
            repo_root,
            primary_branch,
            head,
            coord_owned_filenames=COORD_OWNED_STATUS_FILES,
        )
    except Exception:  # noqa: BLE001  # best-effort only
        logger.debug(
            "commit_router: _try_advance_ref best-effort advance failed silently",
        )


__all__ = ["CommitRouterResult", "commit_for_mission"]
