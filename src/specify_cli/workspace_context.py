"""Workspace context management for runtime visibility.

This module manages persistent workspace context files stored in .kittify/workspaces/.
These files provide runtime visibility into workspace state for LLM agents and CLI tools.

Context files are:
- Created during `spec-kitty implement` command
- Stored in main repo's .kittify/workspaces/ directory
- Readable from both main repo and worktrees (via relative path)
- Cleaned up during merge or explicit workspace deletion

Lane worktrees are the only supported execution topology. One context file is
stored per lane, and sequential WPs in that lane reuse the same worktree.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from specify_cli.core.atomic import atomic_write


_FEATURE_CONTEXT_INDEX_CACHE: dict[tuple[str, str], dict[str, "WorkspaceContext"]] = {}


def _clear_feature_context_index_cache() -> None:
    """Invalidate the process-local feature context index cache."""
    _FEATURE_CONTEXT_INDEX_CACHE.clear()


@dataclass
class WorkspaceContext:
    """
    Runtime context for a work package workspace.

    Provides all information an agent needs to understand workspace state.
    Stored as JSON in .kittify/workspaces/###-feature-lane-x.json
    """

    # Identity
    wp_id: str  # e.g., "WP02"
    feature_slug: str  # e.g., "010-lane-only-runtime"

    # Paths
    worktree_path: str  # Relative path from repo root (e.g., ".worktrees/010-feature-lane-a")
    branch_name: str  # Git branch name (e.g., "kitty/mission-010-feature-lane-a")

    # Base tracking
    base_branch: str  # Branch this was created from (e.g., "kitty/mission-010-feature-lane-a" or "main")
    base_commit: str  # Git SHA this was created from

    # Dependencies
    dependencies: list[str]  # List of WP IDs this depends on (e.g., ["WP01"])

    # Metadata
    created_at: str  # ISO timestamp when workspace was created
    created_by: str  # Command that created this (e.g., "implement-command")
    vcs_backend: str  # "git" or "jj"

    # Lane fields
    lane_id: str  # e.g., "lane-a"
    lane_wp_ids: list[str]  # All WPs assigned to this lane
    current_wp: str | None = None  # Which WP is currently active in the lane

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkspaceContext:
        """Create from dictionary (JSON deserialization).

        """
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        if not filtered.get("lane_id"):
            raise ValueError("Workspace context is missing required lane_id")
        if not isinstance(filtered.get("lane_wp_ids"), list):
            raise ValueError("Workspace context is missing required lane_wp_ids")
        return cls(**filtered)


@dataclass(frozen=True)
class ResolvedWorkspace:
    """Resolved workspace contract for a work package.

    This describes the lane worktree that owns a work package.
    """

    feature_slug: str
    wp_id: str
    workspace_name: str
    worktree_path: Path
    branch_name: str
    lane_id: str
    lane_wp_ids: list[str]
    context: WorkspaceContext | None = None

    @property
    def exists(self) -> bool:
        """Return True when the resolved worktree currently exists on disk."""
        return self.worktree_path.exists()


def get_workspaces_dir(repo_root: Path) -> Path:
    """Get or create the workspaces context directory.

    Args:
        repo_root: Repository root path

    Returns:
        Path to .kittify/workspaces/ directory
    """
    workspaces_dir = repo_root / ".kittify" / "workspaces"
    workspaces_dir.mkdir(parents=True, exist_ok=True)
    return workspaces_dir


def get_context_path(repo_root: Path, workspace_name: str) -> Path:
    """Get path to workspace context file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        Path to context JSON file
    """
    workspaces_dir = get_workspaces_dir(repo_root)
    return workspaces_dir / f"{workspace_name}.json"


def save_context(repo_root: Path, context: WorkspaceContext) -> Path:
    """Save workspace context to JSON file.

    Args:
        repo_root: Repository root path
        context: Workspace context to save

    Returns:
        Path to saved context file
    """
    workspace_name = f"{context.feature_slug}-{context.lane_id}"
    context_path = get_context_path(repo_root, workspace_name)

    # Write JSON with pretty formatting
    content = json.dumps(context.to_dict(), indent=2) + "\n"
    atomic_write(context_path, content)
    _clear_feature_context_index_cache()

    return context_path


def load_context(repo_root: Path, workspace_name: str) -> WorkspaceContext | None:
    """Load workspace context from JSON file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        WorkspaceContext if file exists, None otherwise
    """
    context_path = get_context_path(repo_root, workspace_name)

    if not context_path.exists():
        return None

    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
        return WorkspaceContext.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        # Malformed context file
        return None


def delete_context(repo_root: Path, workspace_name: str) -> bool:
    """Delete workspace context file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-lane-a")

    Returns:
        True if deleted, False if didn't exist
    """
    context_path = get_context_path(repo_root, workspace_name)

    if context_path.exists():
        context_path.unlink()
        _clear_feature_context_index_cache()
        return True

    return False


def list_contexts(repo_root: Path) -> list[WorkspaceContext]:
    """List all workspace contexts.

    Args:
        repo_root: Repository root path

    Returns:
        List of all workspace contexts (empty if none exist)
    """
    workspaces_dir = get_workspaces_dir(repo_root)

    if not workspaces_dir.exists():
        return []

    contexts = []
    for context_file in workspaces_dir.glob("*.json"):
        workspace_name = context_file.stem
        context = load_context(repo_root, workspace_name)
        if context:
            contexts.append(context)

    return contexts


def build_feature_context_index(
    repo_root: Path,
    feature_slug: str,
) -> dict[str, WorkspaceContext]:
    """Index feature contexts by WP ID, expanding lane contexts to all WPs.

    Lane-mode contexts are stored one-per-lane and retain `lane_wp_ids`, so a
    caller asking for WP01 should still find the lane context even after the
    active WP in that lane has advanced to WP02.
    """
    cache_key = (str(repo_root.resolve()), feature_slug)
    cached = _FEATURE_CONTEXT_INDEX_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    index: dict[str, WorkspaceContext] = {}

    for context in list_contexts(repo_root):
        if context.feature_slug != feature_slug:
            continue

        if context.lane_wp_ids:
            for lane_wp_id in context.lane_wp_ids:
                index.setdefault(lane_wp_id, context)

        if context.current_wp:
            index[context.current_wp] = context
        if context.wp_id:
            index.setdefault(context.wp_id, context)

    _FEATURE_CONTEXT_INDEX_CACHE[cache_key] = dict(index)
    return index


def find_context_for_wp(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
) -> WorkspaceContext | None:
    """Return the lane workspace context for a work package."""
    return build_feature_context_index(repo_root, feature_slug).get(wp_id)


def resolve_workspace_for_wp(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
) -> ResolvedWorkspace:
    """Resolve the real workspace/branch contract for a work package.

    Resolution order:
    1. Existing lane workspace context
    2. `lanes.json` lane mapping for the WP

    The returned path may not exist yet; callers can inspect `.exists`.
    """
    context = find_context_for_wp(repo_root, feature_slug, wp_id)
    if context is not None:
        worktree_path = repo_root / context.worktree_path
        return ResolvedWorkspace(
            feature_slug=feature_slug,
            wp_id=wp_id,
            workspace_name=worktree_path.name,
            worktree_path=worktree_path,
            branch_name=context.branch_name,
            lane_id=context.lane_id,
            lane_wp_ids=list(context.lane_wp_ids),
            context=context,
        )

    feature_dir = repo_root / "kitty-specs" / feature_slug
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.persistence import require_lanes_json

    lanes_manifest = require_lanes_json(feature_dir)
    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None:
        raise ValueError(f"{wp_id} is not assigned to any lane in {feature_dir / 'lanes.json'}")

    workspace_name = f"{feature_slug}-{lane.lane_id}"
    return ResolvedWorkspace(
        feature_slug=feature_slug,
        wp_id=wp_id,
        workspace_name=workspace_name,
        worktree_path=repo_root / ".worktrees" / workspace_name,
        branch_name=lane_branch_name(feature_slug, lane.lane_id),
        lane_id=lane.lane_id,
        lane_wp_ids=list(lane.wp_ids),
        context=None,
    )


def resolve_feature_worktree(repo_root: Path, feature_slug: str) -> Path | None:
    """Find a deterministic worktree to operate on for a feature.

    Prefer active lane workspace contexts first, then lane paths inferred from
    `lanes.json`.
    """
    for context in list_contexts(repo_root):
        if context.feature_slug != feature_slug:
            continue
        candidate = repo_root / context.worktree_path
        if candidate.is_dir():
            return candidate

    feature_dir = repo_root / "kitty-specs" / feature_slug
    from specify_cli.lanes.persistence import read_lanes_json

    lanes_manifest = read_lanes_json(feature_dir)

    if lanes_manifest is not None:
        for lane in lanes_manifest.lanes:
            candidate = repo_root / ".worktrees" / f"{feature_slug}-{lane.lane_id}"
            if candidate.is_dir():
                return candidate
    return None


def find_orphaned_contexts(repo_root: Path) -> list[tuple[str, WorkspaceContext]]:
    """Find context files for workspaces that no longer exist.

    Args:
        repo_root: Repository root path

    Returns:
        List of (workspace_name, context) tuples for orphaned contexts
    """
    orphaned = []

    for context in list_contexts(repo_root):
        workspace_path = repo_root / context.worktree_path
        if not workspace_path.exists():
            workspace_name = f"{context.feature_slug}-{context.lane_id}"
            orphaned.append((workspace_name, context))

    return orphaned


def cleanup_orphaned_contexts(repo_root: Path) -> int:
    """Remove context files for deleted workspaces.

    Args:
        repo_root: Repository root path

    Returns:
        Number of orphaned contexts cleaned up
    """
    orphaned = find_orphaned_contexts(repo_root)

    for workspace_name, _ in orphaned:
        delete_context(repo_root, workspace_name)

    return len(orphaned)


__all__ = [
    "ResolvedWorkspace",
    "WorkspaceContext",
    "build_feature_context_index",
    "get_workspaces_dir",
    "get_context_path",
    "save_context",
    "load_context",
    "delete_context",
    "list_contexts",
    "find_context_for_wp",
    "resolve_workspace_for_wp",
    "resolve_feature_worktree",
    "find_orphaned_contexts",
    "cleanup_orphaned_contexts",
]
