"""Lane lifecycle sync points for coordination-branch missions."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from specify_cli.lanes.auto_rebase import AutoRebaseReport, attempt_auto_rebase
from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path as _worktree_path
from specify_cli.lanes.compute import is_planning_lane
from specify_cli.lanes.models import ExecutionLane
from specify_cli.lanes.persistence import CorruptLanesError, read_lanes_json
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
from mission_runtime import MissionArtifactKind

LANE_AUTO_REBASE_FAILED = "LANE_AUTO_REBASE_FAILED"
WORKTREES_DIRNAME = ".worktrees"


@dataclass
class LaneAutoRebaseSyncError(RuntimeError):
    """Structured failure for a lane sync-point auto-rebase refusal."""

    lane_id: str
    lane_branch: str
    lane_worktree_path: Path
    coordination_branch: str
    coordination_head: str | None
    halt_reason: str

    error_code: ClassVar[str] = LANE_AUTO_REBASE_FAILED

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)

    @property
    def message(self) -> str:
        return (
            f"{self.error_code}: auto-rebase refused for {self.lane_id}: "
            f"{self.halt_reason}"
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "error_code": self.error_code,
            "lane_id": self.lane_id,
            "lane_branch": self.lane_branch,
            "lane_worktree_path": str(self.lane_worktree_path),
            "coordination_branch": self.coordination_branch,
            "coordination_head": self.coordination_head,
            "halt_reason": self.halt_reason,
        }


def _git_stdout(repo_root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _resolve_lane_branch(
    repo_root: Path,
    worktree_path: Path,
    mission_slug: str,
    lane: ExecutionLane,
    *,
    planning_base_branch: str,
    mission_id: str | None,
) -> str:
    candidates: list[str] = []
    if mission_id and len(mission_id) >= 8:
        candidates.append(
            lane_branch_name(
                mission_slug,
                lane.lane_id,
                planning_base_branch=planning_base_branch,
                mission_id=mission_id,
            )
        )
    candidates.append(
        lane_branch_name(
            mission_slug,
            lane.lane_id,
            planning_base_branch=planning_base_branch,
        )
    )
    for candidate in candidates:
        if _git_ref_exists(repo_root, candidate):
            return candidate
    return (
        _git_stdout(worktree_path, "rev-parse", "--abbrev-ref", "HEAD")
        or candidates[0]
    )


def sync_lane_after_coordination_commit(
    *,
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    coordination_branch: str,
) -> AutoRebaseReport | None:
    """Merge the coordination branch into a WP lane at lifecycle sync points.

    Returns ``None`` when the WP is not lane-owned or no lane worktree exists.
    Raises :class:`LaneAutoRebaseSyncError` on a refused auto-rebase. The
    underlying auto-rebase path aborts failed git merges before this exception
    is raised, so lane worktree state remains at its pre-sync tip.
    """
    # FR-002 (#2185): ``lanes.json`` is a LANE_STATE (PRIMARY-partition) artifact
    # that lives ONLY on the PRIMARY checkout post-#2106. The auto-rebase callers
    # thread the coord-aware STATUS feature dir (the ``-coord`` husk for a
    # coord-topology mission), which lacks ``lanes.json`` — so trusting that dir
    # here makes ``read_lanes_json`` return ``None`` and SILENTLY skips the
    # post-coordination lane auto-rebase. Self-resolve the read by its real kind
    # so it lands on PRIMARY regardless of topology; the callers' STATUS legs (the
    # append-only event log) stay coord-aware untouched (C-001).
    lanes_read_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )
    try:
        lanes_manifest = read_lanes_json(lanes_read_dir)
    except CorruptLanesError as exc:
        raise LaneAutoRebaseSyncError(
            lane_id="unknown",
            lane_branch="unknown",
            lane_worktree_path=repo_root / WORKTREES_DIRNAME / f"{mission_slug}-unknown",
            coordination_branch=coordination_branch,
            coordination_head=_git_stdout(repo_root, "rev-parse", coordination_branch),
            halt_reason=str(exc),
        ) from exc

    if lanes_manifest is None:
        return None

    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None or is_planning_lane(lane):
        return None

    _lane_worktree = _worktree_path(
        repo_root, mission_slug, mission_id=None, lane_id=lane.lane_id
    )
    lane_branch = _resolve_lane_branch(
        repo_root,
        _lane_worktree,
        mission_slug,
        lane,
        planning_base_branch=lanes_manifest.target_branch,
        mission_id=lanes_manifest.mission_id,
    )
    coordination_head = _git_stdout(repo_root, "rev-parse", coordination_branch)
    worktree_path = _lane_worktree
    if not (worktree_path / ".git").exists():
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        add_result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), lane_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if add_result.returncode != 0:
            raise LaneAutoRebaseSyncError(
                lane_id=lane.lane_id,
                lane_branch=lane_branch,
                lane_worktree_path=worktree_path,
                coordination_branch=coordination_branch,
                coordination_head=coordination_head,
                halt_reason=(
                    "could not create lane worktree for auto-rebase: "
                    f"{(add_result.stderr or add_result.stdout).strip()}"
                ),
            )

    report = attempt_auto_rebase(
        lane=lane,
        branch=lane_branch,
        mission_branch=coordination_branch,
        repo_root=repo_root,
        worktree_path=worktree_path,
    )
    if report.succeeded:
        return report

    raise LaneAutoRebaseSyncError(
        lane_id=lane.lane_id,
        lane_branch=lane_branch,
        lane_worktree_path=worktree_path,
        coordination_branch=coordination_branch,
        coordination_head=coordination_head,
        halt_reason=report.halt_reason or "auto-rebase failed",
    )


__all__ = [
    "LANE_AUTO_REBASE_FAILED",
    "LaneAutoRebaseSyncError",
    "sync_lane_after_coordination_commit",
]
