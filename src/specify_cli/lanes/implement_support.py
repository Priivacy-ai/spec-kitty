"""Workspace creation support for the implement command.

Extracted from implement.py to keep the command clean.
This module handles both supported execution paths:
- code_change WPs allocate or reuse a lane worktree and write context
- planning_artifact WPs execute directly in the repository root
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.ownership.models import ExecutionMode
from specify_cli.lanes.models import LanesManifest
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree
from specify_cli.workspace_context import ResolvedWorkspace
from specify_cli.workspace_context import WorkspaceContext, save_context


@dataclass
class LaneWorkspaceResult:
    """Result of implement workspace creation."""

    workspace_path: Path
    branch_name: str | None
    workspace_name: str
    lane_id: str | None
    mission_branch: str | None
    is_reuse: bool
    vcs_backend_value: str
    execution_mode: str
    resolution_kind: str


def create_lane_workspace(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_file: Path,
    resolved_workspace: ResolvedWorkspace,
    lanes_manifest: LanesManifest | None,
    declared_deps: list[str],
    vcs_backend_value: str,
) -> LaneWorkspaceResult:
    """Create or reuse the execution workspace for the given WP.

    Planning-artifact WPs reuse the repository root directly and do not write a
    lane workspace context file.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        wp_id: Work package ID.
        wp_file: Path to the WP markdown file (for frontmatter updates).
        resolved_workspace: Canonical workspace contract for the WP.
        lanes_manifest: The computed lanes manifest for code_change WPs.
        declared_deps: Declared dependencies for this WP.
        vcs_backend_value: VCS backend value string (e.g., "git").

    Returns:
        LaneWorkspaceResult with workspace info.
    """
    if resolved_workspace.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
        return LaneWorkspaceResult(
            workspace_path=resolved_workspace.worktree_path,
            branch_name=resolved_workspace.branch_name,
            workspace_name=resolved_workspace.workspace_name,
            lane_id=resolved_workspace.lane_id,
            mission_branch=None,
            is_reuse=False,
            vcs_backend_value=vcs_backend_value,
            execution_mode=resolved_workspace.execution_mode,
            resolution_kind=resolved_workspace.resolution_kind,
        )

    if lanes_manifest is None:
        raise ValueError(f"{wp_id} requires lanes.json workspace allocation metadata")

    workspace_path, branch_name = allocate_lane_worktree(
        repo_root=repo_root,
        mission_slug=mission_slug,
        wp_id=wp_id,
        lanes_manifest=lanes_manifest,
    )

    # Install pre-commit ownership guard.
    from specify_cli.policy.hook_installer import install_commit_guard

    install_commit_guard(workspace_path, repo_root)

    lane = lanes_manifest.lane_for_wp(wp_id)
    lane_id = lane.lane_id if lane else "unknown"

    # Detect reuse: if the worktree has a .git file it was pre-existing
    # and allocate_lane_worktree just validated it was clean.
    git_marker = workspace_path / ".git"
    is_reuse = git_marker.exists() and _has_commits_beyond_base(
        workspace_path,
        lanes_manifest.mission_branch,
    )

    from specify_cli.workspace_context import load_context

    base_branch = lanes_manifest.mission_branch

    if is_reuse:
        # Reuse — refresh context to reflect the new active WP.
        context_name = f"{mission_slug}-{lane_id}"
        existing_ctx = load_context(repo_root, context_name)
        if existing_ctx is not None:
            existing_ctx.wp_id = wp_id
            existing_ctx.current_wp = wp_id
            existing_ctx.dependencies = declared_deps
            save_context(repo_root, existing_ctx)
    else:
        # Fresh creation — update frontmatter and create context.
        base_commit_sha = _rev_parse(repo_root, base_branch)
        created_at = datetime.now(timezone.utc).isoformat()

        from specify_cli.frontmatter import update_fields

        update_fields(
            wp_file,
            {
                "base_branch": base_branch,
                "base_commit": base_commit_sha,
                "created_at": created_at,
            },
        )

        context = WorkspaceContext(
            wp_id=wp_id,
            mission_slug=mission_slug,
            worktree_path=str(workspace_path.relative_to(repo_root)),
            branch_name=branch_name,
            base_branch=base_branch,
            base_commit=base_commit_sha,
            dependencies=declared_deps,
            created_at=created_at,
            created_by="implement-command-lane",
            vcs_backend=vcs_backend_value,
            lane_id=lane_id,
            lane_wp_ids=list(lane.wp_ids) if lane else [],
            current_wp=wp_id,
        )
        save_context(repo_root, context)

    return LaneWorkspaceResult(
        workspace_path=workspace_path,
        branch_name=branch_name,
        workspace_name=workspace_path.name,
        lane_id=lane_id,
        mission_branch=lanes_manifest.mission_branch,
        is_reuse=is_reuse,
        vcs_backend_value=vcs_backend_value,
        execution_mode=resolved_workspace.execution_mode,
        resolution_kind=resolved_workspace.resolution_kind,
    )


def _rev_parse(repo_root: Path, ref: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _has_commits_beyond_base(worktree_path: Path, base_branch: str) -> bool:
    """Check if the worktree branch has any commits beyond the base."""
    result = subprocess.run(
        ["git", "log", f"{base_branch}..HEAD", "--oneline", "-1"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())
