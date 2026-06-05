"""Merge preflight checks for target branch safety."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus

_PUSH_PREFLIGHT_EXPORTS = {
    "TargetBranchRefreshStatus",
    "TargetBranchSyncState",
    "TargetBranchSyncStatus",
    "inspect_target_branch_sync",
    "refresh_target_branch_tracking_ref",
}


def __getattr__(name: str) -> Any:
    """Lazily expose moved publish-layer symbols for transition compatibility."""
    if name in _PUSH_PREFLIGHT_EXPORTS:
        from specify_cli.merge import push_preflight

        return getattr(push_preflight, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
        (
            "Inspect changed paths: "
            f"git diff --name-only {tracking_branch}...{status.target_branch}"
        ),
    ]

    if status.state in {"ahead", "diverged"}:
        lines.extend(
            [
                (
                    "Recommended: use the focused PR path unless you verified every ahead "
                    f"commit belongs on '{status.target_branch}' now."
                ),
                (
                    f"Do not run 'git push origin {status.target_branch}' just to satisfy "
                    "this preflight; local target commits may include orchestration history "
                    "or unrelated missions."
                ),
                (
                    f"Only direct-push '{status.target_branch}' after reviewing the ahead "
                    "commits and changed paths."
                ),
            ]
        )
    elif status.state == "behind":
        lines.append(
            f"Recommended: update local '{status.target_branch}' from '{tracking_branch}' "
            "after reviewing remote-only commits; do not push the local target branch."
        )

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
