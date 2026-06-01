"""Lane lifecycle sync points for coordination-branch missions."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from specify_cli.lanes.auto_rebase import AutoRebaseReport, attempt_auto_rebase
from specify_cli.lanes.branch_naming import lane_branch_name
from specify_cli.lanes.models import ExecutionLane
from specify_cli.lanes.persistence import CorruptLanesError, read_lanes_json

LANE_AUTO_REBASE_FAILED = "LANE_AUTO_REBASE_FAILED"


@dataclass(frozen=True)
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
    candidates = []
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
    feature_dir: Path,
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
    try:
        lanes_manifest = read_lanes_json(feature_dir)
    except CorruptLanesError as exc:
        raise LaneAutoRebaseSyncError(
            lane_id="unknown",
            lane_branch="unknown",
            lane_worktree_path=repo_root / ".worktrees" / f"{mission_slug}-unknown",
            coordination_branch=coordination_branch,
            coordination_head=_git_stdout(repo_root, "rev-parse", coordination_branch),
            halt_reason=str(exc),
        ) from exc

    if lanes_manifest is None:
        return None

    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None or lane.lane_id == "lane-planning":
        return None

    lane_branch = _resolve_lane_branch(
        repo_root,
        repo_root / ".worktrees" / f"{mission_slug}-{lane.lane_id}",
        mission_slug,
        lane,
        planning_base_branch=lanes_manifest.target_branch,
        mission_id=lanes_manifest.mission_id,
    )
    coordination_head = _git_stdout(repo_root, "rev-parse", coordination_branch)
    worktree_path = repo_root / ".worktrees" / f"{mission_slug}-{lane.lane_id}"
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
