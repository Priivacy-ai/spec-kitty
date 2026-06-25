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
    MissionArtifactKind,
    is_primary_artifact_kind,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.git import safe_commit


class PrimaryKindReachedCoordStagingError(RuntimeError):
    """A PRIMARY-partition kind reached the coordination staging path (DECISION 8).

    write-surface-coherence WP05 / FR-005 / C-004: once planning no longer transits
    the coordination worktree (WP02/WP03), the coord-staging helpers are reachable
    ONLY for coordination-partition writes. A ``_PRIMARY_ARTIFACT_KINDS`` member
    arriving at :func:`_materialise_coord_worktree` / the staging helper would mean
    a planning artifact is being staged onto the coordination branch — the exact
    mis-route the partition was built to forbid. This is raised (not asserted, so
    the invariant holds under ``python -O``) to keep "planning never reaches coord
    staging" an ENFORCED invariant rather than a comment.
    """


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
    kind: MissionArtifactKind,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
    target_branch: str | None = None,
) -> CommitRouterResult:
    """Commit a mission artifact to its kind-aware resolved placement.

    This is the single canonical commit entry point for all planning-phase
    artifacts (spec, plan, tasks, gap-analysis, generator-config) and the
    coordination-owned ones (analysis-report, acceptance meta). It replaces the
    formerly open-coded inline tails in ``agent/mission.py``.

    Args:
        repo_root:   Primary checkout root (where ``kitty-specs/`` lives).
        mission_slug: Mission handle (e.g. ``"001-my-mission"``).
        files:       Absolute paths of artifacts to commit.
        message:     Commit message.
        policy:      A :class:`~specify_cli.git.protection_policy.ProtectionPolicy`
                     instance (accepted via the structural
                     :class:`_ProtectionPolicyProtocol` to avoid a circular import;
                     duck-typed via ``is_protected``).
        kind:        The :class:`~mission_runtime.MissionArtifactKind` being
                     committed. REQUIRED keyword (DECISION 1 / write-surface-coherence
                     WP02): there is no default, mirroring the now-required
                     ``resolve_placement_only`` kind. A primary kind resolves to
                     the primary ``target_branch`` for every topology and NEVER
                     routes through coordination; a coordination kind keeps the
                     topology-routed placement. An un-threaded caller fails to
                     typecheck rather than silently mis-routing (FR-003 / C-005).
        primary_paths_created_this_invocation: Paths the caller materialised this
                     invocation (eligible for residue cleanup after staging, R6).
        target_branch: Short primary branch name for the post-commit ff-advance
                     (WP09 / FR-010 / #1878). Optional; advance is skipped when
                     ``None``.

    Returns:
        :class:`CommitRouterResult` with the typed outcome.
    """
    placement: CommitTarget = resolve_placement_only(repo_root, mission_slug, kind=kind)

    # FR-003 / C-005 / NFR-004: derive coord-vs-primary routing from the ONE
    # kind-aware ``placement`` (the single authority), not a second predicate.
    # The placement already encodes the partition: a ``_PRIMARY_ARTIFACT_KINDS``
    # member resolves to the primary ``target_branch`` for EVERY topology shape,
    # so it is a direct primary commit; every other kind keeps the topology-routed
    # destination ref. ``use_coord`` is True iff the mission routes through
    # coordination AND the kind-aware placement did NOT land on the primary target
    # branch — i.e. only coordination kinds materialise the coord worktree (C-001).
    # A primary kind therefore NEVER routes to coordination even under coord
    # topology — this removes the planning→coord arm (write-surface-coherence WP02).
    primary_target = _resolve_primary_target_branch(repo_root, mission_slug)
    use_coord = (
        routes_through_coordination(resolve_topology(repo_root, mission_slug))
        and placement.ref != primary_target
    )

    if not use_coord and policy.is_protected(placement.ref):
        # Primary placement on a protected ref — refused (FR-008 / G-4). A
        # planning artifact resolves to the primary ``target_branch``; when that
        # ref is protected the commit is refused with guidance to start a feature
        # branch. The planning→coord transit is GONE (FR-003 / C-005 /
        # write-surface-coherence WP03 T015), so the remedy is a feature branch,
        # NOT the coordination worktree: the deadlock is removed by the
        # feature-branch invariant (research D-3), not by transiting coord.
        return CommitRouterResult(
            status="no_op_wrong_surface",
            placement_ref=placement.ref,
            diagnostic=(
                f"Refusing to commit planning artifacts to the protected branch "
                f"'{placement.ref}'. Start a non-protected feature branch and "
                f"commit there: 'spec-kitty mission create --start-branch "
                f"<feature-branch>' (or check out an existing feature branch). "
                f"Planning artifacts must land on a feature branch."
            ),
        )

    if use_coord:
        worktree_root, commit_paths = _materialise_coord_worktree(
            repo_root,
            mission_slug,
            placement,
            files,
            kind=kind,
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

    # WP09 / FR-010 (#1878): best-effort ff-advance after a coord write. This
    # fires ONLY on the coord branch (``use_coord`` True ⇒ a coordination kind),
    # so it now advances ``target_branch`` to a STATUS/bookkeeping-only coord HEAD
    # (write-surface-coherence WP05 / FR-005): planning no longer transits coord,
    # so the coord HEAD never mixes planning+status. The
    # ``coord_owned_filenames=COORD_OWNED_STATUS_FILES`` exclusion in
    # ``_try_advance_ref`` still matches exactly what a status-only coord write
    # produces — no behaviour change for status writes; the planning case is gone.
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


def _resolve_primary_target_branch(repo_root: Path, mission_slug: str) -> str:
    """Resolve the mission's PRIMARY ``target_branch`` ref.

    This is the SAME ref ``resolve_placement_only`` returns for a primary kind
    (it reads ``get_feature_target_branch`` internally), so comparing the
    kind-aware ``placement.ref`` against it cleanly separates a primary commit
    (``placement.ref == primary_target``) from a coordination one. Resolving it
    here keeps ``use_coord`` derived from the ONE kind-aware placement authority
    (NFR-004) rather than re-deriving the partition.
    """
    from specify_cli.core.paths import get_feature_target_branch

    primary_target: str = get_feature_target_branch(repo_root, mission_slug)
    return primary_target


def _materialise_coord_worktree(
    repo_root: Path,
    mission_slug: str,
    _placement: object,
    files: tuple[Path, ...],
    *,
    kind: MissionArtifactKind,
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
        kind:         The artifact kind being staged. DECISION 8 runtime guard
                      (write-surface-coherence WP05): a PRIMARY-partition kind must
                      NEVER reach coord staging — only coordination kinds do after
                      WP02/WP03 removed the planning→coord route. Reaching here with
                      a primary kind raises :class:`PrimaryKindReachedCoordStagingError`.
        primary_paths_created_this_invocation: Eligible residue paths (R6).

    Returns:
        ``(coord_worktree, coord_paths)`` on success; ``(repo_root, files)`` on error.
    """
    # DECISION 8 / FR-005 / C-004: enforce the partition invariant at the coord
    # staging boundary. ``commit_for_mission`` only routes coordination kinds here
    # (``use_coord`` is False for primary kinds), so a primary kind arriving means a
    # caller mis-routed a planning artifact onto the coordination branch — fail loud.
    if is_primary_artifact_kind(kind):
        raise PrimaryKindReachedCoordStagingError(
            f"PRIMARY-partition kind {kind!r} reached coordination staging for "
            f"mission {mission_slug!r}; planning artifacts must commit directly to "
            f"the primary target branch and never transit the coordination worktree."
        )

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


# ---------------------------------------------------------------------------
# Planning-commit residue (relocated from mission.py — #2056 WP08 / T032).
#
# These were the last planning-commit primitives living in the ``mission`` god
# module. ``tasks.py``'s map-requirements + planning auto-commit paths consume
# them (LIVE on this base), so they are RELOCATED here — the canonical commit
# router — not deleted. ``mission.py`` re-exports them as deliberate shims so
# historical ``mission.<name>`` patch targets keep resolving (WP09 owns the
# final shim sweep). INV-8: one-way — commit_router never imports the mission
# seams; the ``CoordinationWorkspace`` / ``resolve_mid8`` reads use the same
# lower-layer authorities the existing router helpers already use.
# ---------------------------------------------------------------------------


def _resolve_planning_placement(
    repo_root: Path, mission_slug: str, *, kind: MissionArtifactKind
) -> CommitTarget:
    """Resolve the single planning-phase :class:`CommitTarget` for ``mission_slug``.

    WP05 / FR-003 / C-GUARD-3a (#1784): the ONE destination authority for every
    planning-phase commit (spec / plan / tasks / finalize-tasks / doc-mission
    bookkeeping). Routes through ``mission_runtime.resolve_placement_only`` — the
    WP-less projection over the SAME resolution authority the full resolver uses
    — so no planning commit path re-derives a destination from ``meta.json`` or
    the current git checkout (the catch-22 root). The placement is CWD-invariant
    and topology-correct (coordination / flattened / primary).

    ``kind`` is REQUIRED (write-surface-coherence WP02): the projection is now
    kind-aware, so the caller MUST name the artifact kind it is placing — a
    primary kind lands on the primary target branch for every topology.
    """
    return resolve_placement_only(repo_root, mission_slug, kind=kind)


def _planning_commit_worktree(
    repo_root: Path,
    mission_slug: str,
    paths: tuple[Path, ...],
    *,
    kind: MissionArtifactKind = MissionArtifactKind.TASKS_INDEX,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
) -> tuple[Path, tuple[Path, ...]]:
    """Resolve the worktree a planning commit lands in for ``mission_slug``.

    WP05: ``safe_commit`` requires ``worktree_root`` HEAD to equal the
    destination ref. When :func:`routes_through_coordination` holds for the
    STORED topology the destination is the coordination branch, which is checked
    out in the per-mission coordination worktree — so the commit must run there
    (and the artifacts, written to the main checkout, are copied across for
    staging, skipping coord-owned status files, #1589). For a coord-less topology
    the destination is already HEAD of the main checkout, so it is used directly.

    write-surface-coherence WP03 / T014: this helper is partition-aware. The
    coord-staging body runs ONLY for coordination-partition artifact kinds; a
    PRIMARY kind (the default — every caller here commits planning artifacts)
    resolves to the primary ``target_branch`` for every topology, so it commits
    directly from the primary checkout with NO coord transit (FR-003 / C-005).

    #2056 WP08 / T033: the coord-staging body reuses the router's existing
    ``_resolve_mid8`` + ``CoordinationWorkspace`` + ``_stage_artifacts_in_coord_
    worktree`` primitives — the reconciliation of the former mission.py
    ``_stage_finalize_artifacts_in_coord_worktree`` near-duplicate into the
    single canonical staging helper.

    Returns ``(worktree_root, paths_to_commit)``.
    """
    # PRIMARY kinds never transit coordination — commit directly from the primary
    # checkout (write-surface-coherence WP03 / T014). The coord-staging body below
    # is reached only by coordination-partition kinds.
    if is_primary_artifact_kind(kind):
        return repo_root, paths

    if not routes_through_coordination(resolve_topology(repo_root, mission_slug)):
        return repo_root, paths

    mid8 = _resolve_mid8(repo_root, mission_slug)
    if mid8 is None:
        return repo_root, paths

    from specify_cli.coordination.workspace import CoordinationWorkspace

    # Materialize the coordination worktree on demand (the coord branch already
    # exists from ``mission create``). This is the catch-22 killer: the planning
    # commit ALWAYS reaches its resolved coordination placement instead of
    # falling back to the protected main checkout and tripping the guard.
    try:
        coord_wt = CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)
    except Exception:
        # Resolution failed (e.g. branch mismatch under a divergent worktree);
        # fall back to the main checkout so the existing diagnostics surface
        # rather than crashing the lifecycle (C-004 strangler safety).
        return repo_root, paths

    coord_paths = _stage_artifacts_in_coord_worktree(
        list(paths),
        coord_wt,
        repo_root,
        primary_paths_created_this_invocation=primary_paths_created_this_invocation,
    )
    return coord_wt, tuple(coord_paths)


# Backwards-compatible alias: the former mission.py name for the staging helper.
# #2056 WP08 / T033 collapsed the near-duplicate into the canonical router
# helper; this alias preserves the historical
# ``_stage_finalize_artifacts_in_coord_worktree`` symbol for the existing
# coord-staging unit tests (and the ``mission`` re-export shim) without forking
# a second copy.
_stage_finalize_artifacts_in_coord_worktree = _stage_artifacts_in_coord_worktree


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


__all__ = [
    "CommitRouterResult",
    "commit_for_mission",
]
