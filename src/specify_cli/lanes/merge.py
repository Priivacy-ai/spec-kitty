"""Lane-based merge operations.

Two-tier merge flow:
1. Lane → Mission: merge a lane branch into the mission integration branch.
2. Mission → Target: merge the mission branch into the target (e.g. main).

Both operations use temporary merge workspaces and the stale-lane
blocker to prevent overlapping file conflicts.

Strategy note (FR-006, FR-007):
- Lane→mission always uses merge commits (no-ff) regardless of strategy.
- Mission→target honors the ``strategy`` parameter (default: SQUASH).
"""

from __future__ import annotations

from mission_runtime import MissionArtifactKind
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.git.ref_advance import advance_branch_ref
from specify_cli.status import COORD_OWNED_STATUS_FILES
from specify_cli.lanes._git import branch_exists as _shared_branch_exists
from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path as _worktree_path
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.lanes.stale_check import StaleCheckResult, check_lane_staleness
from specify_cli.merge.config import MergeStrategy

_EVENT_LOG_DRIVER_NAME = "Spec Kitty event log union merge"
_EVENT_LOG_DRIVER_COMMAND = "spec-kitty merge-driver-event-log %O %A %B"


@dataclass
class LaneMergeResult:
    """Outcome of a lane merge operation."""

    success: bool
    lane_id: str
    merged_into: str
    errors: list[str] = field(default_factory=list)
    stale_check: StaleCheckResult | None = None


@dataclass
class MissionMergeResult:
    """Outcome of a mission-to-target merge."""

    success: bool
    mission_branch: str
    target_branch: str
    commit: str | None = None
    already_applied: bool = False
    errors: list[str] = field(default_factory=list)


def _resolve_lane_manifest(
    repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest | None,
) -> LanesManifest | None:
    """Return the provided manifest or load it from disk."""
    if lanes_manifest is not None:
        return lanes_manifest
    # FR-001 (#2185): ``lanes.json`` is LANE_STATE (PRIMARY-partition) — it lives
    # ONLY on the PRIMARY checkout post-#2106. The coord-aware resolver lands on
    # the STATUS-only ``-coord`` husk (no lanes.json), so route by kind.
    feature_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )
    return read_lanes_json(feature_dir)


def _try_auto_rebase_if_stale(
    stale: StaleCheckResult,
    lane: ExecutionLane,
    branch: str,
    mission_branch: str,
    mission_slug: str,
    repo_root: Path,
) -> StaleCheckResult:
    """If the lane is stale and a worktree exists, attempt auto-rebase and recheck."""
    if not stale.is_stale:
        return stale
    worktree_path = _worktree_path(
        repo_root, mission_slug, mission_id=None, lane_id=lane.lane_id
    )
    if not worktree_path.exists():
        return stale
    from specify_cli.lanes.auto_rebase import attempt_auto_rebase

    report = attempt_auto_rebase(
        lane, branch, mission_branch, repo_root, worktree_path
    )
    if report.succeeded:
        return check_lane_staleness(lane, branch, mission_branch, repo_root)
    return stale


def merge_lane_to_mission(
    repo_root: Path,
    mission_slug: str,
    lane_id: str,
    lanes_manifest: LanesManifest | None = None,
) -> LaneMergeResult:
    """Merge a lane branch into the mission integration branch.

    Performs stale-lane check before merging. If the lane is stale
    (overlapping files changed in mission), the merge is blocked.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lane_id: Lane to merge (e.g., "lane-a").
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).

    Returns:
        LaneMergeResult with success/error status.
    """
    lanes_manifest = _resolve_lane_manifest(repo_root, mission_slug, lanes_manifest)
    if lanes_manifest is None:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into="",
            errors=["No lanes.json found for this feature"],
        )

    lane = next(
        (c for c in lanes_manifest.lanes if c.lane_id == lane_id),
        None,
    )
    if lane is None:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into="",
            errors=[f"Lane {lane_id} not found in lanes.json"],
        )

    branch = lane_branch_name(
        mission_slug,
        lane_id,
        planning_base_branch=lanes_manifest.target_branch,
    )
    mission_branch = lanes_manifest.mission_branch

    if not _branch_exists(repo_root, branch):
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[f"Lane branch {branch} does not exist"],
        )

    stale = check_lane_staleness(lane, branch, mission_branch, repo_root)
    stale = _try_auto_rebase_if_stale(
        stale, lane, branch, mission_branch, mission_slug, repo_root,
    )
    if stale.is_stale:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[
                f"Lane {lane_id} is stale: overlapping files {stale.stale_files}. "
                f"{stale.remediation}"
            ],
            stale_check=stale,
        )

    try:
        _merge_branch_into(repo_root, branch, mission_branch)
    except RuntimeError as e:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[str(e)],
        )

    return LaneMergeResult(
        success=True, lane_id=lane_id, merged_into=mission_branch,
    )


def merge_mission_to_target(
    repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest | None = None,
    *,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
    allow_already_applied: bool = False,
) -> MissionMergeResult:
    """Merge the mission integration branch into the target branch (e.g., main).

    This is the final step: only the mission branch may merge to main.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).
        strategy: Merge strategy for the mission→target step (FR-006/T010).
            Defaults to SQUASH. Lane→mission is NOT affected by this parameter.

    Returns:
        MissionMergeResult with success/error status.
    """
    if lanes_manifest is None:
        # FR-001 (#2185): LANE_STATE read — PRIMARY-partition (see above).
        feature_dir = resolve_planning_read_dir(
            repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
        )
        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is None:
            return MissionMergeResult(
                success=False, mission_branch="", target_branch="",
                errors=["No lanes.json found for this feature"],
            )

    mission_branch = lanes_manifest.mission_branch
    target_branch = lanes_manifest.target_branch

    if not _branch_exists(repo_root, mission_branch):
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch,
            errors=[f"Mission branch {mission_branch} does not exist"],
        )

    try:
        # T010: honor strategy for mission→target only; lane→mission is not touched
        changed = _merge_branch_into(
            repo_root,
            mission_branch,
            target_branch,
            strategy=strategy,
            allow_noop_squash=allow_already_applied,
        )
    except RuntimeError as e:
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch, errors=[str(e)],
        )

    # Get the merge commit.
    commit = _rev_parse(repo_root, target_branch) if changed else None

    return MissionMergeResult(
        success=True,
        mission_branch=mission_branch,
        target_branch=target_branch,
        commit=commit,
        already_applied=not changed,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _branch_exists(repo_root: Path, branch: str) -> bool:
    # Routes the existence check through the shared lanes/_git helper while
    # preserving the merge pipeline's single env authority (_make_merge_env);
    # the env composes through rather than forking the helper (#1904).
    return bool(_shared_branch_exists(repo_root, branch, env=_make_merge_env()))


def _git_config_get(repo_root: Path, key: str) -> str | None:
    """Return a local git config value or ``None`` when unset/unreadable."""
    result = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=_make_merge_env(),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _ensure_event_log_merge_driver_config(repo_root: Path) -> None:
    """Ensure the local semantic merge driver is configured before git merges.

    ``spec-kitty init`` may run before the project becomes a git repository, so
    the upgrade migration cannot always install the local merge-driver config at
    init time. The merge path self-heals that gap here so status.events.jsonl
    merges stay semantic for freshly initialized repos too.
    """
    if not (repo_root / ".git").exists():
        return

    if _git_config_get(repo_root, "merge.spec-kitty-event-log.name") != _EVENT_LOG_DRIVER_NAME:
        subprocess.run(
            ["git", "config", "--local", "merge.spec-kitty-event-log.name", _EVENT_LOG_DRIVER_NAME],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            env=_make_merge_env(),
        )
    if _git_config_get(repo_root, "merge.spec-kitty-event-log.driver") != _EVENT_LOG_DRIVER_COMMAND:
        subprocess.run(
            ["git", "config", "--local", "merge.spec-kitty-event-log.driver", _EVENT_LOG_DRIVER_COMMAND],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            env=_make_merge_env(),
        )


def _make_merge_env() -> dict[str, str]:
    """Single environment authority for the lane-merge pipeline (AC-F1).

    Prepends the current venv's bin directory to PATH so that git's merge
    driver invocation of ``spec-kitty merge-driver-event-log`` resolves to the
    same spec-kitty binary that is currently running, not a stale global one.

    Every subprocess invocation in this module routes its ``env`` through
    this helper — no inline ``os.environ`` copies with ad-hoc PATH/GIT_*
    mutations (FR-008b; ratchet in
    ``tests/architectural/test_merge_pipeline_ratchets.py``).
    """
    venv_bin = str(Path(sys.executable).parent)
    env = os.environ.copy()
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    return env


def _rev_parse(repo_root: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(repo_root), capture_output=True, text=True, env=_make_merge_env(),
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _merge_branch_into(
    repo_root: Path,
    source_branch: str,
    target_branch: str,
    *,
    strategy: MergeStrategy = MergeStrategy.MERGE,
    allow_noop_squash: bool = False,
) -> bool:
    """Merge source_branch into target_branch using a temporary worktree.

    Creates a detached worktree at the target branch tip, merges source
    into it using the specified strategy, then fast-forwards the target branch
    ref to the result. The main repo's checkout is never changed.

    Uses --detach to avoid "branch already checked out" errors when
    target_branch is the currently checked-out branch.

    Strategy behavior:
    - MERGE (default for lane→mission): ``git merge --no-ff``  — preserves structure
    - SQUASH: ``git merge --squash`` + explicit commit
    - REBASE: ``git rebase`` then fast-forward

    Raises RuntimeError on merge failure (including conflicts).
    """
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="kitty-merge-")
    tmp_path = Path(tmp_dir)

    # Single environment authority for the lane-merge pipeline (AC-F1).
    _env = _make_merge_env()

    try:
        _ensure_event_log_merge_driver_config(repo_root)

        # Create detached worktree at target branch tip.
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_path), target_branch],
            cwd=str(repo_root), capture_output=True, text=True, env=_env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create merge worktree: {result.stderr.strip()}"
            )

        if strategy == MergeStrategy.SQUASH:
            # Squash all commits from source into a single new commit.
            # -X theirs: when the mission branch (source) conflicts with the
            # target on kitty-specs/ planning artifacts, the mission branch
            # version is authoritative (it carries the reviewed, finalized state).
            result = subprocess.run(
                ["git", "merge", "--squash", "-X", "theirs", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Squash merge of {source_branch} into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Squash merges do not record ancestry. On retry after a previous
            # successful squash, Git reports a clean index and a plain commit
            # would fail in this detached worktree with "Not currently on any
            # branch." Only explicit resume callers may treat that as
            # idempotent success; ordinary callers need a real merge result.
            staged = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if staged.returncode == 0:
                if allow_noop_squash:
                    return False
                raise RuntimeError(
                    f"Squash merge of {source_branch} into {target_branch} "
                    "produced no changes; target may already contain this tree. "
                    "Retry with merge resume if recovering an interrupted merge."
                )
            if staged.returncode not in (0, 1):
                raise RuntimeError(
                    f"Could not inspect squash merge result for {source_branch} "
                    f"into {target_branch}: {staged.stderr.strip()}"
                )
            # Commit the squashed result.
            result = subprocess.run(
                [
                    "git", "-c", "commit.gpgsign=false",
                    "commit", "-m",
                    f"feat({source_branch}): squash merge of mission",
                ],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Squash commit into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
        elif strategy == MergeStrategy.REBASE:
            # Rebase source onto target in the isolated worktree, then
            # fast-forward target to the rebased detached HEAD. Do not check
            # out or rewrite source_branch in the user's main checkout.
            result = subprocess.run(
                ["git", "checkout", "--detach", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to check out {source_branch} in merge worktree: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Rebase source on top of target.
            result = subprocess.run(
                ["git", "rebase", target_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Rebase of {source_branch} onto {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Get the rebased HEAD SHA.
            rebased_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(tmp_path), capture_output=True, text=True, check=True, env=_env,
            ).stdout.strip()
            # Fast-forward the target branch to the rebased tip, resyncing any
            # worktree that has target_branch checked out (#1826 / AC-B2).
            # Coordination status residue is excluded from the dirty gate via
            # the single residue authority (FR-012 / #1878).
            advance_branch_ref(
                repo_root,
                target_branch,
                rebased_sha,
                env=_env,
                coord_owned_filenames=COORD_OWNED_STATUS_FILES,
            )
            return True  # early return — ref already updated
        else:
            # MERGE strategy (default for lane→mission): no-ff merge commit.
            result = subprocess.run(
                ["git", "merge", source_branch, "--no-edit",
                 "-m", f"Merge {source_branch} into {target_branch}"],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Merge of {source_branch} into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )

        # Get the resulting commit SHA.
        merge_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True, env=_env,
        ).stdout.strip()

        # Update the target branch ref to point to the merge commit, resyncing
        # any worktree that has target_branch checked out (#1826 / AC-B2).
        # Coordination status residue is excluded from the dirty gate via the
        # single residue authority (FR-012 / #1878).
        advance_branch_ref(
            repo_root,
            target_branch,
            merge_commit,
            env=_env,
            coord_owned_filenames=COORD_OWNED_STATUS_FILES,
        )
        return True
    finally:
        subprocess.run(
            ["git", "worktree", "remove", str(tmp_path), "--force"],
            cwd=str(repo_root), capture_output=True, env=_env,
        )
