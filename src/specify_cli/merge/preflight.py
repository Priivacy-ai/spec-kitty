"""Merge preflight checks for target branch safety."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

TargetBranchSyncState = Literal[
    "in_sync",
    "ahead",
    "behind",
    "diverged",
    "no_tracking_branch",
    "missing_local_branch",
]


@dataclass(frozen=True)
class TargetBranchSyncStatus:
    """Local target branch state relative to its tracking branch."""

    target_branch: str
    tracking_branch: str | None
    ahead_count: int
    behind_count: int
    state: TargetBranchSyncState

    @property
    def is_safe(self) -> bool:
        return self.state in {"in_sync", "no_tracking_branch"}


@dataclass(frozen=True)
class TargetBranchRefreshStatus:
    """Result of refreshing a target branch tracking ref before preflight."""

    target_branch: str
    remote_name: str
    attempted: bool
    success: bool
    error: str | None = None


def _git(
    repo_root: Path,
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )


def _branch_commit_exists(repo_root: Path, ref: str) -> bool:
    result = _git(repo_root, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
    return result.returncode == 0


def _resolve_tracking_branch(repo_root: Path, target_branch: str) -> str | None:
    upstream = _git(
        repo_root,
        [
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            f"{target_branch}@{{upstream}}",
        ],
    )
    if upstream.returncode == 0 and upstream.stdout.strip():
        return upstream.stdout.strip()

    origin_branch = f"origin/{target_branch}"
    if _branch_commit_exists(repo_root, f"refs/remotes/{origin_branch}"):
        return origin_branch
    return None


def refresh_target_branch_tracking_ref(
    repo_root: Path,
    target_branch: str,
    *,
    remote_name: str = "origin",
) -> TargetBranchRefreshStatus:
    """Refresh ``origin/<target_branch>`` before enforcing sync safety.

    The sync inspector remains read-only so callers can use it for diagnostics,
    but merge enforcement must compare against current remote state. If the
    checkout has no ``origin`` remote, there is nothing to refresh and the
    local-only preflight can continue.
    """
    remote = _git(repo_root, ["remote", "get-url", remote_name])
    if remote.returncode != 0:
        return TargetBranchRefreshStatus(
            target_branch=target_branch,
            remote_name=remote_name,
            attempted=False,
            success=True,
        )

    fetch = _git(
        repo_root,
        [
            "fetch",
            "--quiet",
            remote_name,
            f"+refs/heads/{target_branch}:refs/remotes/{remote_name}/{target_branch}",
        ],
    )
    if fetch.returncode != 0:
        detail = (fetch.stderr or fetch.stdout or "").strip()
        return TargetBranchRefreshStatus(
            target_branch=target_branch,
            remote_name=remote_name,
            attempted=True,
            success=False,
            error=detail or f"git fetch {remote_name} {target_branch} failed",
        )

    return TargetBranchRefreshStatus(
        target_branch=target_branch,
        remote_name=remote_name,
        attempted=True,
        success=True,
    )


def inspect_target_branch_sync(
    repo_root: Path,
    target_branch: str,
) -> TargetBranchSyncStatus:
    """Compare a local target branch with its tracking branch.

    The check is read-only and compares against the locally-known tracking ref.
    Merge enforcement should call :func:`refresh_target_branch_tracking_ref`
    first so it cannot miss a recently advanced remote target.
    """
    if not _branch_commit_exists(repo_root, f"refs/heads/{target_branch}"):
        return TargetBranchSyncStatus(
            target_branch=target_branch,
            tracking_branch=None,
            ahead_count=0,
            behind_count=0,
            state="missing_local_branch",
        )

    tracking_branch = _resolve_tracking_branch(repo_root, target_branch)
    if tracking_branch is None:
        return TargetBranchSyncStatus(
            target_branch=target_branch,
            tracking_branch=None,
            ahead_count=0,
            behind_count=0,
            state="no_tracking_branch",
        )

    counts = _git(
        repo_root,
        ["rev-list", "--left-right", "--count", f"{target_branch}...{tracking_branch}"],
    )
    if counts.returncode != 0:
        return TargetBranchSyncStatus(
            target_branch=target_branch,
            tracking_branch=tracking_branch,
            ahead_count=0,
            behind_count=0,
            state="no_tracking_branch",
        )

    left, right = (int(part) for part in counts.stdout.strip().split())
    if left > 0 and right > 0:
        state: TargetBranchSyncState = "diverged"
    elif left > 0:
        state = "ahead"
    elif right > 0:
        state = "behind"
    else:
        state = "in_sync"

    return TargetBranchSyncStatus(
        target_branch=target_branch,
        tracking_branch=tracking_branch,
        ahead_count=left,
        behind_count=right,
        state=state,
    )


def focused_pr_branch_name(mission_slug: str, target_branch: str) -> str:
    """Return a deterministic branch name for non-destructive recovery."""
    safe_target = target_branch.replace("/", "-")
    return f"kitty/pr/{mission_slug}-to-{safe_target}"


def target_branch_sync_remediation(
    status: TargetBranchSyncStatus,
    *,
    mission_slug: str | None,
    mission_branch: str | None = None,
) -> list[str]:
    """Build actionable, non-destructive remediation diagnostics."""
    tracking_branch = status.tracking_branch or f"origin/{status.target_branch}"
    lines = [
        (
            f"Local target branch '{status.target_branch}' is {status.state} "
            f"relative to '{tracking_branch}' "
            f"({status.ahead_count} ahead, {status.behind_count} behind)."
        ),
        "Spec Kitty stopped before mutating merge state or reconstructing branches.",
        f"Refresh remote refs: git fetch origin {status.target_branch}",
        (
            "Inspect differences: "
            f"git log --oneline --left-right --cherry-pick {status.target_branch}...{tracking_branch}"
        ),
    ]

    if mission_slug:
        focused_branch = focused_pr_branch_name(mission_slug, status.target_branch)
        source_branch = mission_branch or f"kitty/mission-{mission_slug}"
        lines.extend(
            [
                (
                    "Focused PR path: "
                    f"git switch -c {focused_branch} {source_branch}"
                ),
                f"Then push it: git push -u origin {focused_branch}",
                f"Open a PR from {focused_branch} into {status.target_branch}.",
            ]
        )
    else:
        lines.append(
            "If local-only commits are intentional, preserve them on a new PR branch before retrying."
        )

    lines.append("Do not use reset, rebase, or force-push as part of this preflight remediation.")
    return lines
