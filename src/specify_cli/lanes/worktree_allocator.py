"""Lane worktree allocation.

Allocates or reuses worktrees for execution lanes. Each lane gets
exactly one worktree and one branch. Sequential WPs in the same
lane share the worktree — no recreation between WPs.

The mission integration branch is created (if absent) when the
first lane worktree is allocated.

#1348 (WP04): when the mission carries a ``coordination_branch`` field
in ``meta.json`` (new-topology missions, WP03+), the lane branch is
parented on the coordination branch rather than the legacy
``mission_branch`` field, and the lane worktree gets a sparse-checkout
policy registered so it cannot see ``status.events.jsonl`` or
``status.json`` (FR-024 / FR-025 / FR-029).
"""

from __future__ import annotations

from mission_runtime import MissionArtifactKind
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
import subprocess
from pathlib import Path

from specify_cli.coordination import register_lane_sparse_checkout
from specify_cli.core.errors import StructuredError
from specify_cli.lanes._git import branch_exists as _branch_exists
from specify_cli.lanes.branch_naming import lane_branch_name, resolve_mid8, worktree_path as _worktree_path
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.mission_metadata import load_meta


class DirtyWorktreeError(Exception):
    """Raised when a lane worktree has uncommitted changes during handoff."""


class LaneNotFoundError(Exception):
    """Raised when a WP is not assigned to any lane."""


class DependencyLaneMergeConflictError(StructuredError):
    """Raised when merging a dependency lane tip into a dependent lane conflicts.

    Issue #1684: a dependent lane's worktree base must contain the approved
    tips of every lane it ``depends_on_lanes``. When two dependency lanes (or a
    dependency lane and the lane base) touch overlapping content, the merge that
    propagates their code cannot auto-resolve. We fail CLOSED — the half-merged
    state is aborted before this is raised so the worktree is never left in a
    conflicted state — and hand the operator a structured ``next_step``.
    """

    error_code: str = "DEPENDENCY_LANE_MERGE_CONFLICT"

    def __init__(self, lane_id: str, dep_lane_id: str, dep_branch: str) -> None:
        self.lane_id = lane_id
        self.dep_lane_id = dep_lane_id
        self.dep_branch = dep_branch
        self.next_step = (
            f"merge {dep_branch!r} into lane {lane_id!r} manually, resolve the "
            f"conflicts, commit, then re-run the implement command for this WP."
        )
        super().__init__(
            f"cannot auto-merge dependency lane {dep_lane_id!r} ({dep_branch}) "
            f"into lane {lane_id!r}: the merge conflicts. {self.next_step}"
        )

    def to_dict(self) -> dict[str, object]:
        payload = super().to_dict()
        payload["lane_id"] = self.lane_id
        payload["dep_lane_id"] = self.dep_lane_id
        payload["dep_branch"] = self.dep_branch
        payload["next_step"] = self.next_step
        return payload


def predict_lane_worktree(
    repo_root: Path, mission_slug: str, lane_id: str
) -> tuple[Path, str]:
    """The ONE lane-worktree placement decision (path + branch), read-only.

    Both the write authority (:func:`allocate_lane_worktree`) and read-only
    mirrors (``orchestrator-api resolve-workspace``, its transition guard)
    consume this, so the compose grammar is single-sited and a future mid8
    cutover is one edit.

    Emit-don't-guess: routes the on-disk worktree name through the canonical
    WP01 seam instead of an ad-hoc f-string. Passes ``mission_id=None`` so the
    seam reproduces the legacy ``f"{slug}-{lane}"`` grammar byte-identically
    (the historical call sites carried no mid8); introducing a mission_id here
    would append ``-{mid8}`` and rename every existing lane worktree.
    """
    branch = lane_branch_name(mission_slug, lane_id)
    worktree_path = _worktree_path(
        repo_root, mission_slug, mission_id=None, lane_id=lane_id
    )
    return worktree_path, branch


def allocate_lane_worktree(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    lanes_manifest: LanesManifest,
) -> tuple[Path, str]:
    """Allocate or reuse the worktree for the lane containing wp_id.

    Returns (worktree_path, branch_name).

    If the lane worktree already exists (from a prior WP in the same lane),
    validates it is clean and returns the existing path.

    If the lane worktree does not exist, creates the mission branch (if
    needed) and then creates the lane worktree branching from it.

    Issue #1684 — cross-lane dependency propagation: a lane may declare
    ``depends_on_lanes``. The dependent lane's worktree base must contain the
    approved tips of those dependency lanes so the dependent WP can see the
    sibling-lane code it builds on. Both the FRESH-creation path and the
    REUSE path merge in every resolvable dependency-lane tip (in
    ``parallel_group`` then ``lane_id`` order). The merge is idempotent —
    already-merged tips fast-forward to a no-op — so re-entering a lane after a
    dependency was approved late (the WP05/WP09 double-hit on 01KTYGTE) picks up
    the newly-approved tip. A dependency lane whose branch no longer resolves
    (merged-and-deleted post-mission) is skipped with a warning; a true merge
    conflict fails closed with :class:`DependencyLaneMergeConflictError` after
    aborting the merge (never a half-merged worktree).

    Args:
        repo_root: Absolute path to the main repository.
        mission_slug: Feature slug for branch naming.
        wp_id: Work package ID to allocate a worktree for.
        lanes_manifest: The computed lanes manifest.

    Returns:
        Tuple of (worktree_path, branch_name).

    Raises:
        LaneNotFoundError: If wp_id is not in any lane.
        DirtyWorktreeError: If reusing a worktree that has uncommitted changes.
        DependencyLaneMergeConflictError: If a dependency lane tip cannot be
            auto-merged into the lane (fail-closed, merge aborted first).
        RuntimeError: If git operations fail.
    """
    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None:
        raise LaneNotFoundError(
            f"{wp_id} is not assigned to any execution lane in lanes.json"
        )

    # Placement (path + branch) comes from the single predict seam — the write
    # authority and the read-only mirrors must never diverge on this decision.
    worktree_path, branch = predict_lane_worktree(repo_root, mission_slug, lane.lane_id)

    if worktree_path.exists():
        # Reuse existing lane worktree — validate it is clean first.
        _validate_worktree_clean(worktree_path, lane.lane_id)
        # #1684 reuse-path catch-up: a dependency lane may have been approved
        # *after* this worktree was created. Merge any newly-approved dep tips
        # so the dependent lane sees them. Idempotent: already-merged tips are
        # ancestors and skip.
        _merge_dependency_lane_tips(
            repo_root, worktree_path, mission_slug, lane, lanes_manifest
        )
        return worktree_path, branch

    # #1348 (WP04): pick the parent branch.
    #
    #   New-topology missions (meta.json has ``coordination_branch``):
    #     parent the lane on the coordination branch and register the
    #     status-files sparse-checkout exclusion.
    #
    #   Legacy missions (no ``coordination_branch``): fall back to the
    #     ``mission_branch`` field. No sparse-checkout. WP08 will harden
    #     the legacy path further; for now we preserve existing behaviour.
    coordination_branch = _read_coordination_branch(repo_root, mission_slug)

    if coordination_branch is not None:
        _ensure_branch_exists(
            repo_root, coordination_branch, lanes_manifest.target_branch,
        )
        _create_lane_worktree(repo_root, worktree_path, branch, coordination_branch)
        # Register the sparse-checkout policy so the lane filesystem does
        # NOT contain status.events.jsonl / status.json. Only meaningful
        # when we have a mid8; new-topology missions always do because
        # WP03 mints the coord branch only when mission_id is present.
        # Route through the authoritative resolver (WP03 / FR-009, F-1). The
        # former raising ``mid8`` + try/except is replaced by resolve_mid8's
        # decline-to-``""`` contract; ``or None`` preserves the prior ``None``
        # behaviour so the downstream registration guard is unchanged.
        short_id = resolve_mid8(mission_slug, mission_id=lanes_manifest.mission_id) or None
        if short_id is not None:
            register_lane_sparse_checkout(worktree_path, mission_slug, short_id)
    else:
        # Legacy path: parent on the mission_branch field.
        mission_branch = lanes_manifest.mission_branch
        _ensure_mission_branch(repo_root, mission_branch, lanes_manifest.target_branch)
        _create_lane_worktree(repo_root, worktree_path, branch, mission_branch)

    # #1684 fresh-path propagation: merge approved dependency-lane tips on top
    # of the chosen base (coordination or legacy mission branch) so the
    # dependent lane sees sibling code.
    _merge_dependency_lane_tips(
        repo_root, worktree_path, mission_slug, lane, lanes_manifest
    )

    return worktree_path, branch


def _ordered_dependency_lanes(
    lane: ExecutionLane, lanes_manifest: LanesManifest,
) -> list[ExecutionLane]:
    """Resolve a lane's ``depends_on_lanes`` ids to lane objects, in merge order.

    Ordered by ``(parallel_group, lane_id)`` — the same topological order
    ``compute_lanes`` sorts lanes into and that ``merge`` consumes — so multiple
    dependency tips are merged deterministically from the earliest group up.

    Dependency lane ids that do not resolve to a lane in the manifest are
    skipped (defensive — ``compute_lanes`` only emits real lane ids).
    """
    by_id = {dep_lane.lane_id: dep_lane for dep_lane in lanes_manifest.lanes}
    resolved = [
        by_id[dep_id] for dep_id in lane.depends_on_lanes if dep_id in by_id
    ]
    return sorted(resolved, key=lambda dep: (dep.parallel_group, dep.lane_id))


def _create_branch_from(
    repo_root: Path, branch: str, parent: str, *, label: str = "branch",
) -> None:
    """Create ``branch`` pointing at ``parent`` (no worktree), or raise.

    ``label`` only tunes the error wording (``"branch"`` vs ``"mission
    branch"``) so callers keep their historical messages.
    """
    result = subprocess.run(
        ["git", "branch", branch, parent],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create {label} {branch} from {parent}: "
            f"{result.stderr.strip()}"
        )


def _current_head(worktree_path: Path) -> str | None:
    """Return the commit SHA at ``worktree_path``'s HEAD, or ``None``.

    Used to snapshot a lane worktree's ref before the dependency-merge loop so
    a later-dependency conflict can roll the lane back atomically (#1915). On an
    unborn HEAD or any git failure we return ``None`` and the caller skips the
    reset — there is no committed state to preserve.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    head = result.stdout.strip()
    return head or None


def _merge_dependency_lane_tips(
    repo_root: Path,
    worktree_path: Path,
    mission_slug: str,
    lane: ExecutionLane,
    lanes_manifest: LanesManifest,
) -> None:
    """Merge each dependency lane's tip into ``worktree_path`` (issue #1684).

    For every lane in ``lane.depends_on_lanes`` (resolved in ``parallel_group``
    then ``lane_id`` order), resolve its branch through the canonical
    :func:`lane_branch_name` grammar — never a name-guessing f-string — and
    ``git merge`` its tip into the dependent lane's worktree. This is what
    propagates an approved sibling lane's committed code into the lane that
    depends on it.

    Semantics:

    * **Idempotent.** A dep tip already contained in HEAD is an ancestor and is
      skipped (no empty merge commit, no-op on the reuse path).
    * **Missing branch → warn + skip.** A dependency lane that was
      merged-and-deleted post-mission no longer resolves; we emit a warning and
      fall back to the existing base rather than crashing (mirrors the
      ``--base main`` recovery surface).
    * **Conflict → fail closed AND atomic (#1915).** A merge that cannot
      auto-resolve is aborted (``git merge --abort``) and the lane is then reset
      hard to the ref recorded BEFORE the loop, so no *earlier* clean dep merge
      survives a *later* dep conflict. Without this, ``git merge --abort`` only
      undoes the conflicting merge, orphaning a partially-propagated state the
      operator never asked for. The whole multi-dep loop is all-or-nothing.

    The merge composes with an explicit ``--base`` override: ``--base`` selects
    the *root* the lane branches from (handled by the caller via the patched
    ``mission_branch``); dependency tips are then merged on top so cross-lane
    code still propagates regardless of the chosen root.
    """
    ordered = _ordered_dependency_lanes(lane, lanes_manifest)
    if not ordered:
        return
    # Snapshot the lane ref before the loop so a later-dep conflict can roll
    # the worktree back to its exact pre-merge HEAD (#1915 atomicity).
    pre_loop_ref = _current_head(worktree_path)
    for dep_lane in ordered:
        dep_branch = lane_branch_name(mission_slug, dep_lane.lane_id)
        if not _branch_exists(repo_root, dep_branch):
            # Merged-and-deleted (or never-started) dependency lane: fall back
            # to the existing base. Do not crash, do not silently swallow —
            # surface a warning so the operator can use --base if needed.
            print(
                f"WARNING: dependency lane {dep_lane.lane_id!r} branch "
                f"{dep_branch!r} does not resolve; lane {lane.lane_id!r} will "
                f"not contain its tip (it may have been merged-and-deleted). "
                f"If you need its code, re-run with an explicit --base."
            )
            continue
        # Already an ancestor of HEAD? Then it is already merged — skip so we
        # do not create a redundant merge commit (idempotent reuse-path).
        is_ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", dep_branch, "HEAD"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        if is_ancestor.returncode == 0:
            continue
        merge = subprocess.run(
            [
                "git", "merge", "--no-edit",
                "-m", f"Merge dependency lane {dep_lane.lane_id} into {lane.lane_id}",
                dep_branch,
            ],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        if merge.returncode != 0:
            # Fail closed AND atomic (#1915): abort the half-merge, then reset
            # hard to the pre-loop ref so no EARLIER clean dep merge survives
            # this LATER conflict. The worktree is left exactly as it was before
            # the loop began — clean, for the operator's manual merge.
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
            )
            if pre_loop_ref is not None:
                subprocess.run(
                    ["git", "reset", "--hard", pre_loop_ref],
                    cwd=str(worktree_path),
                    capture_output=True,
                    text=True,
                )
            raise DependencyLaneMergeConflictError(
                lane.lane_id, dep_lane.lane_id, dep_branch
            )


def _read_coordination_branch(
    repo_root: Path, mission_slug: str,
) -> str | None:
    """Return the ``coordination_branch`` field from ``meta.json``.

    Returns ``None`` for legacy missions (no field, or no meta.json).

    The meta.json is in the main checkout under
    ``kitty-specs/<mission_slug>/meta.json`` — the same place WP03's
    mission_create writes it.
    """
    # FR-001 (#2185): this is the chicken-and-egg coord discovery — it reads
    # ``meta.json`` (PRIMARY_METADATA, PRIMARY-partition) to *discover* whether the
    # mission routes through a coordination branch. The kind-aware seam is
    # topology-blind for PRIMARY kinds, so it correctly anchors on the PRIMARY
    # checkout where ``meta.json`` lives post-#2106 (the coord husk has none / a
    # STATUS-only one) — never the coord-aware resolver (which would need the very
    # answer this read produces).
    meta_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.PRIMARY_METADATA
    )
    data = load_meta(meta_dir, on_malformed="none")
    if data is None:
        return None
    value = data.get("coordination_branch")
    if isinstance(value, str) and value:
        return value
    return None


def _ensure_branch_exists(
    repo_root: Path, branch: str, fallback_parent: str,
) -> None:
    """Create ``branch`` from ``fallback_parent`` if it does not exist.

    Used for the coordination-branch path: WP03 normally creates the
    coordination branch at ``mission create`` time, but legacy
    upgrade-in-place projects may still hit this code path with the
    branch missing. We defensively recreate from the target branch
    rather than crashing.
    """
    if _branch_exists(repo_root, branch):
        return
    _create_branch_from(repo_root, branch, fallback_parent)


def _validate_worktree_clean(worktree_path: Path, lane_id: str) -> None:
    """Fail if the worktree has uncommitted changes.

    This prevents a WP from inheriting dirty state from a prior WP
    in the same lane.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git status failed in {worktree_path}: {result.stderr.strip()}"
        )
    if result.stdout.strip():
        raise DirtyWorktreeError(
            f"Lane {lane_id} worktree at {worktree_path} has uncommitted changes. "
            f"Commit or stash before starting the next WP."
        )


def _ensure_mission_branch(
    repo_root: Path, mission_branch: str, target_branch: str,
) -> None:
    """Create the mission integration branch if it doesn't exist.

    The mission branch is created from the target branch (e.g., main).
    It is a regular branch, not backed by a worktree.
    """
    if _branch_exists(repo_root, mission_branch):
        return
    _create_branch_from(
        repo_root, mission_branch, target_branch, label="mission branch",
    )


def _create_lane_worktree(
    repo_root: Path, worktree_path: Path, branch: str, base_branch: str,
) -> None:
    """Create a git worktree for a lane branch."""
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create lane worktree at {worktree_path}: "
            f"{result.stderr.strip()}"
        )


def _recover_lane_worktree(
    repo_root: Path, worktree_path: Path, existing_branch: str,
) -> None:
    """Recreate worktree from existing branch (recovery mode).

    Uses ``git worktree add <path> <branch>`` WITHOUT ``-b`` to attach
    to an already-existing branch. This is the recovery path for when
    the agent process crashed and the branch survived but the worktree
    was lost.

    Raises:
        RuntimeError: If the git worktree add command fails.
    """
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), existing_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to recover worktree at {worktree_path}: "
            f"{result.stderr.strip()}"
        )
