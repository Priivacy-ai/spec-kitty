"""Lane-mode workspace creation support for the implement command.

Extracted from implement.py to keep the command clean.
This module handles the lane-mode path: reading lanes.json,
allocating the lane worktree, and creating the workspace context.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.lanes.models import LanesManifest
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree
from specify_cli.workspace_context import WorkspaceContext, save_context


@dataclass
class LaneWorkspaceResult:
    """Result of lane-mode workspace creation."""

    workspace_path: Path
    branch_name: str
    workspace_name: str
    lane_id: str
    mission_branch: str
    is_reuse: bool
    vcs_backend_value: str


def try_lane_mode(feature_dir: Path) -> LanesManifest | None:
    """Check if a feature uses lane-based execution.

    Returns the LanesManifest if lanes.json exists, None otherwise.
    """
    return read_lanes_json(feature_dir)


def create_lane_workspace(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
    wp_file: Path,
    lanes_manifest: LanesManifest,
    declared_deps: list[str],
    vcs_backend_value: str,
) -> LaneWorkspaceResult:
    """Create or reuse a lane worktree for the given WP.

    This is the lane-mode equivalent of the legacy workspace creation
    in implement.py. It:
    1. Allocates the lane worktree (creating mission branch if needed).
    2. Detects reuse vs fresh creation.
    3. Updates WP frontmatter with base tracking.
    4. Creates workspace context.

    Args:
        repo_root: Repository root.
        feature_slug: Feature slug.
        wp_id: Work package ID.
        wp_file: Path to the WP markdown file (for frontmatter updates).
        lanes_manifest: The computed lanes manifest.
        declared_deps: Declared dependencies for this WP.
        vcs_backend_value: VCS backend value string (e.g., "git").

    Returns:
        LaneWorkspaceResult with workspace info.
    """
    workspace_path, branch_name = allocate_lane_worktree(
        repo_root=repo_root,
        feature_slug=feature_slug,
        wp_id=wp_id,
        lanes_manifest=lanes_manifest,
    )

    lane = lanes_manifest.lane_for_wp(wp_id)
    lane_id = lane.lane_id if lane else "unknown"

    # Detect reuse: if the worktree has a .git file it was pre-existing
    # and allocate_lane_worktree just validated it was clean.
    git_marker = workspace_path / ".git"
    is_reuse = git_marker.exists() and _has_commits_beyond_base(
        workspace_path, lanes_manifest.mission_branch,
    )

    if not is_reuse:
        # Fresh creation — update frontmatter and create context.
        base_branch = lanes_manifest.mission_branch
        base_commit_sha = _rev_parse(repo_root, base_branch)
        created_at = datetime.now(timezone.utc).isoformat()

        from specify_cli.frontmatter import update_fields

        update_fields(wp_file, {
            "base_branch": base_branch,
            "base_commit": base_commit_sha,
            "created_at": created_at,
        })

        context = WorkspaceContext(
            wp_id=wp_id,
            feature_slug=feature_slug,
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
    )


def _rev_parse(repo_root: Path, ref: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(repo_root), capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _has_commits_beyond_base(worktree_path: Path, base_branch: str) -> bool:
    """Check if the worktree branch has any commits beyond the base."""
    result = subprocess.run(
        ["git", "log", f"{base_branch}..HEAD", "--oneline", "-1"],
        cwd=str(worktree_path), capture_output=True, text=True, check=False,
    )
    return bool(result.stdout.strip())
