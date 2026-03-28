"""Merge Engine v2 — Orchestration.

Implements T039: the main merge orchestrator for workspace-per-WP features.

The engine operates entirely inside a dedicated git worktree
(``.kittify/runtime/merge/<mission_id>/workspace/``) so the main
repository's checked-out branch is never changed.

Public API:
    ``execute_merge(...)``   – Start a fresh merge or resume from state.
    ``resume_merge(...)``    – Load existing state and continue.
    ``abort_merge(...)``     – Cleanup workspace and clear state.

Merge is deterministic: same inputs → same result regardless of main repo state.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.merge.conflict_resolver import ResolutionResult, resolve_owned_conflicts
from specify_cli.merge.ordering import MergeOrderError, get_merge_order
from specify_cli.merge.preflight import run_preflight, run_preflight_from_context
from specify_cli.merge.reconciliation import reconcile_done_state
from specify_cli.merge.state import (
    MergeState,
    abort_git_merge,
    acquire_merge_lock,
    clear_state,
    detect_git_merge_state,
    load_state,
    release_merge_lock,
    save_state,
)
from specify_cli.merge.workspace import (
    cleanup_merge_workspace,
    create_merge_workspace,
    get_merge_workspace,
)

if TYPE_CHECKING:
    from specify_cli.context.models import MissionContext

__all__ = [
    "MergeResult",
    "execute_merge",
    "resume_merge",
    "abort_merge",
]

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Outcome of a merge engine run."""

    success: bool
    merged_wps: list[str] = field(default_factory=list)
    """WPs that were successfully merged during this run."""

    skipped_wps: list[str] = field(default_factory=list)
    """WPs that were skipped (e.g. already completed from a prior run)."""

    conflicts: list[str] = field(default_factory=list)
    """Files that had unresolvable merge conflicts (merge paused)."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered (preflight failures, git errors, etc.)."""

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_git(
    args: list[str],
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command; raise RuntimeError with stderr on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def _get_conflicted_files(workspace_path: Path) -> list[str]:
    """Return list of paths with unmerged conflicts in the worktree."""
    result = _run_git(["diff", "--name-only", "--diff-filter=U"], workspace_path, check=False)
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def _branch_tip(branch: str, workspace_path: Path) -> str | None:
    """Return the full SHA of a branch tip, or None if not found."""
    result = _run_git(["rev-parse", "--verify", branch], workspace_path, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _merge_branch(
    branch: str,
    wp_id: str,
    feature_slug: str,
    strategy: str,
    workspace_path: Path,
) -> None:
    """Execute a single branch merge in the workspace.

    Raises RuntimeError on failure (caller handles conflicts).
    """
    if strategy == "squash":
        _run_git(["merge", "--squash", branch], workspace_path)
        _run_git(
            ["commit", "-m", f"Merge {wp_id} from {feature_slug}"],
            workspace_path,
        )
    elif strategy == "rebase":
        raise RuntimeError(
            "Rebase strategy is not supported for workspace-per-WP merge. "
            "Use 'merge' or 'squash'."
        )
    else:
        # Default: merge
        _run_git(
            [
                "merge", "--no-ff", branch,
                "-m", f"Merge {wp_id} from {feature_slug}",
            ],
            workspace_path,
        )


def _checkout_target(target_branch: str, workspace_path: Path) -> None:
    """Position the workspace at the target branch tip without binding it.

    The workspace was created via ``git worktree add --detach``, so we
    cannot ``git checkout <branch>`` — that would fail with
    "fatal: '<branch>' is already used by worktree ..." when the main
    repo has the same branch checked out.

    Instead we reset the detached HEAD to the branch tip.
    """
    # Resolve the target branch tip
    tip_result = _run_git(
        ["rev-parse", f"refs/heads/{target_branch}"],
        workspace_path,
    )
    target_tip = tip_result.stdout.strip()
    # Reset detached HEAD to that tip
    _run_git(["reset", "--hard", target_tip], workspace_path)
    # Try fast-forward fetch; skip gracefully if no remote
    ff_result = _run_git(
        ["fetch", "origin", target_branch],
        workspace_path,
        check=False,
    )
    if ff_result.returncode == 0:
        # Update to remote tip if available
        remote_tip = _run_git(
            ["rev-parse", f"origin/{target_branch}"],
            workspace_path,
            check=False,
        )
        if remote_tip.returncode == 0:
            _run_git(["reset", "--hard", remote_tip.stdout.strip()], workspace_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_merge(
    feature_slug: str,
    repo_root: Path,
    context: MissionContext | None = None,
    strategy: str = "merge",
    push: bool = False,
    dry_run: bool = False,
    keep_workspace: bool = False,
) -> MergeResult:
    """Orchestrate merging all WPs for *feature_slug* into the target branch.

    Workflow:
    1. Acquire merge lock.
    2. Run preflight validation.
    3. Create / reuse dedicated merge workspace.
    4. Checkout target branch in workspace; pull --ff-only.
    5. Compute merge order (dependency-based topological sort).
    6. For each WP in order:
       a. Skip if already completed (resume support).
       b. Set state.current_wp, persist state.
       c. Merge branch into workspace.
       d. On conflict: attempt auto-resolution; if unresolved, pause and persist.
       e. Mark WP complete, persist state.
    7. If push: push merged target branch.
    8. Run post-merge reconciliation (emit done events from git ancestry).
    9. Cleanup workspace (unless keep_workspace).
    10. Release lock.

    Args:
        feature_slug: Feature identifier (e.g. "057-canonical-context-...").
        repo_root: Absolute path to the main repository root.
        context: Optional MissionContext for richer preflight validation.
        strategy: "merge" (default) or "squash". "rebase" raises immediately.
        push: If True, push the merged target branch to origin after merge.
        dry_run: If True, run preflight + compute order but do not actually merge.
        keep_workspace: If True, do not remove the workspace after merge.

    Returns:
        MergeResult with success status, merged/skipped WPs, conflicts, errors.
    """
    from specify_cli.cli.commands.merge import find_wp_worktrees

    result = MergeResult(success=False)

    # Derive target branch
    target_branch = _resolve_target_branch(feature_slug, repo_root, context)
    mission_id = feature_slug  # canonical mission ID == feature slug

    # 1. Acquire lock
    if not acquire_merge_lock(mission_id, repo_root):
        result.errors.append(
            f"Merge lock already held for {mission_id}. "
            "Another merge may be running. Use --abort to clear."
        )
        return result

    try:
        # 2. Discover WP workspaces
        wp_workspaces = find_wp_worktrees(repo_root, feature_slug)
        if not wp_workspaces:
            result.errors.append(
                f"No WP worktrees found for feature {feature_slug!r}."
            )
            return result

        # 3. Preflight
        if context is not None:
            preflight = run_preflight_from_context(context, wp_workspaces)
        else:
            preflight = run_preflight(
                feature_slug=feature_slug,
                target_branch=target_branch,
                repo_root=repo_root,
                wp_workspaces=wp_workspaces,
            )

        if not preflight.passed:
            result.errors.extend(preflight.errors)
            return result

        # 4. Compute merge order
        feature_dir = repo_root / "kitty-specs" / feature_slug
        try:
            ordered_workspaces = get_merge_order(wp_workspaces, feature_dir)
        except MergeOrderError as exc:
            result.errors.append(str(exc))
            return result

        wp_order = [wp_id for _, wp_id, _ in ordered_workspaces]

        # 5. Dry run: return plan without executing
        if dry_run:
            logger.info(
                "[dry-run] Merge order for %s: %s",
                feature_slug,
                ", ".join(wp_order),
            )
            result.success = True
            result.merged_wps = []
            result.skipped_wps = []
            return result

        # 6. Create merge workspace
        workspace_path = create_merge_workspace(mission_id, target_branch, repo_root)

        # 7. Initialize / reuse state
        existing_state = load_state(repo_root, mission_id)
        if existing_state is not None:
            state = existing_state
            # Update order in case WPs changed
            state.wp_order = wp_order
        else:
            state = MergeState(
                mission_id=mission_id,
                feature_slug=feature_slug,
                target_branch=target_branch,
                wp_order=wp_order,
                strategy=strategy,
                workspace_path=str(workspace_path),
            )

        save_state(state, repo_root)

        # 8. Checkout target branch in workspace
        try:
            _checkout_target(target_branch, workspace_path)
        except RuntimeError as exc:
            result.errors.append(f"Failed to checkout {target_branch}: {exc}")
            return result

        # Build lookup: wp_id → (path, wp_id, branch)
        wp_map = {wp_id: (path, wp_id, branch) for path, wp_id, branch in ordered_workspaces}

        merged_branches: list[str] = []

        # 9. Merge each WP in order
        for wp_id in wp_order:
            if wp_id in state.completed_wps:
                result.skipped_wps.append(wp_id)
                logger.debug("Skipping %s (already completed from prior run)", wp_id)
                continue

            wp_entry = wp_map.get(wp_id)
            if wp_entry is None:
                result.errors.append(f"No workspace found for {wp_id}")
                continue

            _, _, branch = wp_entry

            # Update state: mark current WP
            state.set_current_wp(wp_id)
            save_state(state, repo_root)

            logger.info("Merging %s (%s)...", wp_id, branch)

            try:
                _merge_branch(branch, wp_id, feature_slug, strategy, workspace_path)
                # Success
                state.mark_wp_complete(wp_id)
                save_state(state, repo_root)
                result.merged_wps.append(wp_id)
                merged_branches.append(branch)
                logger.info("Merged %s successfully.", wp_id)

            except RuntimeError as exc:
                # Check for merge conflict
                conflicted = _get_conflicted_files(workspace_path)
                if conflicted:
                    # Attempt auto-resolution
                    resolution = resolve_owned_conflicts(workspace_path, conflicted)
                    if resolution.errors:
                        for err in resolution.errors:
                            result.errors.append(err)

                    if resolution.has_unresolved:
                        # Human-authored conflict: pause merge
                        result.conflicts.extend(resolution.unresolved)
                        state.set_pending_conflicts(True)
                        save_state(state, repo_root)
                        logger.warning(
                            "Merge paused: unresolved conflicts in %s for %s",
                            resolution.unresolved,
                            wp_id,
                        )
                        return result
                    elif resolution.resolved:
                        # All owned conflicts resolved — complete the merge commit
                        try:
                            _run_git(
                                ["commit", "-m", f"Merge {wp_id} from {feature_slug} (auto-resolved)"],
                                workspace_path,
                            )
                            state.mark_wp_complete(wp_id)
                            save_state(state, repo_root)
                            result.merged_wps.append(wp_id)
                            merged_branches.append(branch)
                            logger.info("Merged %s with auto-resolved conflicts.", wp_id)
                        except RuntimeError as commit_exc:
                            result.errors.append(
                                f"Failed to commit auto-resolved merge for {wp_id}: {commit_exc}"
                            )
                            return result
                    else:
                        # No conflicts detected but merge failed
                        result.errors.append(
                            f"Merge failed for {wp_id}: {exc}"
                        )
                        return result
                else:
                    result.errors.append(f"Merge failed for {wp_id}: {exc}")
                    return result

        # 10. Push if requested
        if push:
            try:
                _run_git(["push", "origin", target_branch], workspace_path)
                logger.info("Pushed %s to origin.", target_branch)
            except RuntimeError as exc:
                result.errors.append(f"Push failed: {exc}")
                # Non-fatal: merge succeeded, push failed

        # 11. Post-merge reconciliation
        if merged_branches and feature_dir.exists():
            try:
                reconcile_done_state(
                    feature_dir=feature_dir,
                    merged_branches=merged_branches,
                    target_branch=target_branch,
                    workspace_path=workspace_path,
                )
            except Exception as exc:
                logger.warning("Reconciliation failed (non-fatal): %s", exc)

        # 12. Cleanup state
        clear_state(repo_root, mission_id)
        result.success = True

    finally:
        # 13. Cleanup workspace (unless keep_workspace or still have conflicts)
        if not keep_workspace and not result.has_conflicts:
            try:
                cleanup_merge_workspace(mission_id, repo_root)
            except Exception as exc:
                logger.warning("Failed to cleanup merge workspace: %s", exc)

        # 14. Release lock
        release_merge_lock(mission_id, repo_root)

    return result


def resume_merge(
    repo_root: Path,
    keep_workspace: bool = False,
) -> MergeResult:
    """Resume an interrupted merge from persisted state.

    Loads the state from ``.kittify/runtime/merge/<mission_id>/state.json``,
    then calls ``execute_merge`` with the same parameters.

    Args:
        repo_root: Absolute path to the main repository root.
        keep_workspace: If True, do not remove the workspace after merge.

    Returns:
        MergeResult. If no state exists, returns failure with an error message.
    """
    state = load_state(repo_root)
    if state is None:
        result = MergeResult(success=False)
        result.errors.append(
            "No merge state to resume. "
            "Run 'spec-kitty merge --feature <slug>' to start a new merge."
        )
        return result

    # Check for pending git conflicts that must be resolved first
    workspace_path = Path(state.workspace_path) if state.workspace_path else None
    if workspace_path and workspace_path.exists():
        if detect_git_merge_state(workspace_path):
            result = MergeResult(success=False)
            result.errors.append(
                "Git merge in progress in workspace. Resolve conflicts and "
                "run 'spec-kitty merge --resume' again."
            )
            return result

    logger.info(
        "Resuming merge of %s: %d/%d WPs complete",
        state.feature_slug,
        len(state.completed_wps),
        len(state.wp_order),
    )

    return execute_merge(
        feature_slug=state.feature_slug,
        repo_root=repo_root,
        strategy=state.strategy,
        keep_workspace=keep_workspace,
    )


def abort_merge(repo_root: Path) -> None:
    """Abort an in-progress merge: abort any git merge, cleanup workspace, clear state.

    Args:
        repo_root: Absolute path to the main repository root.
    """
    state = load_state(repo_root)
    mission_id: str | None = state.mission_id if state else None

    # Abort git merge in workspace if one is in progress
    if state and state.workspace_path:
        workspace_path = Path(state.workspace_path)
        if workspace_path.exists() and detect_git_merge_state(workspace_path):
            abort_git_merge(workspace_path)
            logger.info("Aborted git merge in workspace %s", workspace_path)

    # Also check main repo
    if detect_git_merge_state(repo_root):
        abort_git_merge(repo_root)

    # Cleanup workspace
    if mission_id:
        try:
            cleanup_merge_workspace(mission_id, repo_root)
        except Exception as exc:
            logger.warning("Could not fully cleanup workspace: %s", exc)

        clear_state(repo_root, mission_id)
        release_merge_lock(mission_id, repo_root)
        logger.info("Merge aborted for %s", mission_id)
    else:
        # No known mission_id — try scanning runtime dir
        clear_state(repo_root)
        logger.info("Merge state cleared (no active mission found)")


def _resolve_target_branch(
    feature_slug: str,
    repo_root: Path,
    context: MissionContext | None,
) -> str:
    """Resolve the target branch for a feature.

    Priority:
    1. context.target_branch (if context is provided)
    2. meta.json ``target_branch``
    3. "main" as fallback
    """
    if context is not None:
        return context.target_branch

    meta_path = repo_root / "kitty-specs" / feature_slug / "meta.json"
    if meta_path.exists():
        import json
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            tb = data.get("target_branch") or data.get("merge_target_branch")
            if tb and isinstance(tb, str):
                return tb.strip()
        except (json.JSONDecodeError, OSError):
            pass

    return "main"
