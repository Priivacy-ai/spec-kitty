"""Branch/preflight fixture shapes for release workflow tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchDivergenceState:
    """A deterministic local-vs-remote branch divergence scenario."""

    local_target_branch: str
    remote_tracking_branch: str
    merge_target_branch: str
    local_ahead: int
    remote_ahead: int
    mission_owned_files: tuple[str, ...]
    remediation_branch: str

    @property
    def has_diverged(self) -> bool:
        return self.local_ahead > 0 and self.remote_ahead > 0


def branch_divergence_state(
    *,
    local_target_branch: str = "main",
    remote_tracking_branch: str = "origin/main",
    merge_target_branch: str = "main",
    local_ahead: int = 1,
    remote_ahead: int = 1,
    mission_owned_files: tuple[str, ...] = ("src/specify_cli/status/emit.py",),
    remediation_branch: str = "release-320-workflow-reliability-focused-pr",
) -> BranchDivergenceState:
    """Return a focused PR branch preflight scenario without invoking Git."""

    return BranchDivergenceState(
        local_target_branch=local_target_branch,
        remote_tracking_branch=remote_tracking_branch,
        merge_target_branch=merge_target_branch,
        local_ahead=local_ahead,
        remote_ahead=remote_ahead,
        mission_owned_files=mission_owned_files,
        remediation_branch=remediation_branch,
    )
