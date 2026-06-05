"""Publish-layer push-safety preflight for merge operations.

This module owns all remote-state inspection that is only relevant when
``--push`` is requested.  The domain merge layer (``preflight.py``) must
remain network-free; callers that perform a local-only merge must never
import from this module.

See architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md
Issue: https://github.com/Priivacy-ai/spec-kitty/issues/1706
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = [
    "TargetBranchSyncStatus",
    "check_push_safety",
]

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

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
    """Local target branch state relative to its tracking branch.

    This dataclass lives in the *publish layer* and is used only when a push
    is being evaluated.  Use ``is_safe_to_push`` for push-safety decisions.
    ``is_safe`` is a deprecated alias kept for transition compatibility; it
    always returns ``True`` because local-merge operations do not require
    remote sync.
    """

    target_branch: str
    tracking_branch: str | None
    ahead_count: int
    behind_count: int
    state: TargetBranchSyncState

    @property
    def is_safe_to_push(self) -> bool:
        """Return True only when merge --push can publish without remote catch-up.

        The following states are safe to push:
        - ``"ahead"``: local has new commits; push advances the remote normally.
        - ``"in_sync"``: identical tip; a no-op push.
        - ``"no_tracking_branch"``: no remote ref configured; push creates it.
        - ``"missing_local_branch"``: local branch does not exist; nothing to push.

        ``"behind"`` is not safe for Spec Kitty's merge --push flow: after the
        local merge creates new target commits from a stale base, git will reject
        the push as non-fast-forward, leaving local merge/bookkeeping mutations.
        It must be blocked before mutation, like ``"diverged"``.
        """
        return self.state not in {"behind", "diverged"}

    @property
    def is_safe(self) -> bool:
        """Deprecated.  Always returns True.

        This predicate was previously used to gate *local* merge operations on
        remote sync state, which was incorrect (see ADR 2026-06-05-1 and issue
        #1706).  Local merges do not require remote sync; only push operations
        do.

        Callers making push decisions must migrate to ``is_safe_to_push``.
        """
        return True


@dataclass(frozen=True)
class TargetBranchRefreshStatus:
    """Result of refreshing a target branch tracking ref before push-safety check."""

    target_branch: str
    remote_name: str
    attempted: bool
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class TargetBranchPushSafetyResult:
    """Composite result of a push-safety check including fetch and sync status."""

    refresh_status: TargetBranchRefreshStatus
    sync_status: TargetBranchSyncStatus | None
    is_safe_to_push: bool
    fetch_failed: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Internal git helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def refresh_target_branch_tracking_ref(
    repo_root: Path,
    target_branch: str,
    *,
    remote_name: str = "origin",
) -> TargetBranchRefreshStatus:
    """Refresh ``origin/<target_branch>`` before enforcing push-safety.

    This is a network operation and must only be called from publish-layer
    code (i.e., inside ``if push:`` branches in ``merge.py``).  Never call
    this from the domain merge layer.

    If the checkout has no ``origin`` remote, the function returns a
    successful status with ``attempted=False``.
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

    Read-only: compares against the locally-known tracking ref.  Callers
    performing push-safety enforcement should call
    :func:`refresh_target_branch_tracking_ref` first so the tracking ref is
    current.
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


def check_push_safety(
    repo_root: Path,
    target_branch: str,
    remote_name: str = "origin",
) -> TargetBranchPushSafetyResult:
    """Check whether pushing target_branch to remote_name is safe.

    Performs a ``git fetch`` to refresh the tracking ref, then compares the
    local and remote commit graphs.  Returns a result whose ``is_safe_to_push``
    field is ``False`` when the local target cannot be pushed without first
    integrating remote commits.

    This function must only be called when ``--push`` is requested.  Never call
    it from the domain merge layer.
    """
    refresh = refresh_target_branch_tracking_ref(
        repo_root, target_branch, remote_name=remote_name
    )
    if not refresh.success:
        return TargetBranchPushSafetyResult(
            refresh_status=refresh,
            sync_status=None,
            is_safe_to_push=False,
            fetch_failed=True,
            error=refresh.error,
        )
    sync = inspect_target_branch_sync(repo_root, target_branch)
    return TargetBranchPushSafetyResult(
        refresh_status=refresh,
        sync_status=sync,
        is_safe_to_push=sync.is_safe_to_push,
        fetch_failed=False,
    )
