"""Workspace context management for runtime visibility.

This module manages persistent workspace context files stored in .kittify/workspaces/.
These files provide runtime visibility into workspace state for LLM agents and CLI tools.

Context files are:
- Created during `spec-kitty implement` command
- Stored in main repo's .kittify/workspaces/ directory
- Readable from both main repo and worktrees (via relative path)
- Cleaned up during merge or explicit workspace deletion
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class WorkspaceContext:
    """
    Runtime context for a work package workspace.

    Provides all information an agent needs to understand workspace state.
    Stored as JSON in .kittify/workspaces/###-feature-WP##.json
    """

    # Identity
    wp_id: str  # e.g., "WP02"
    feature_slug: str  # e.g., "010-workspace-per-wp"

    # Paths
    worktree_path: str  # Relative path from repo root (e.g., ".worktrees/010-feature-WP02")
    branch_name: str  # Git branch name (e.g., "010-feature-WP02")

    # Base tracking
    base_branch: str  # Branch this was created from (e.g., "010-feature-WP01" or "main")
    base_commit: str  # Git SHA this was created from

    # Dependencies
    dependencies: list[str]  # List of WP IDs this depends on (e.g., ["WP01"])

    # Metadata
    created_at: str  # ISO timestamp when workspace was created
    created_by: str  # Command that created this (e.g., "implement-command")
    vcs_backend: str  # "git" or "jj"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkspaceContext:
        """Create from dictionary (JSON deserialization)."""
        return cls(**data)


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
        workspace_name: Workspace name (e.g., "010-feature-WP02")

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
    workspace_name = f"{context.feature_slug}-{context.wp_id}"
    context_path = get_context_path(repo_root, workspace_name)

    # Write JSON with pretty formatting
    context_path.write_text(json.dumps(context.to_dict(), indent=2) + "\n", encoding="utf-8")

    return context_path


def load_context(repo_root: Path, workspace_name: str) -> WorkspaceContext | None:
    """Load workspace context from JSON file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-WP02")

    Returns:
        WorkspaceContext if file exists, None otherwise
    """
    context_path = get_context_path(repo_root, workspace_name)

    if not context_path.exists():
        return None

    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
        return WorkspaceContext.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        # Malformed context file
        return None


def delete_context(repo_root: Path, workspace_name: str) -> bool:
    """Delete workspace context file.

    Args:
        repo_root: Repository root path
        workspace_name: Workspace name (e.g., "010-feature-WP02")

    Returns:
        True if deleted, False if didn't exist
    """
    context_path = get_context_path(repo_root, workspace_name)

    if context_path.exists():
        context_path.unlink()
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
            workspace_name = f"{context.feature_slug}-{context.wp_id}"
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
    "WorkspaceContext",
    "get_workspaces_dir",
    "get_context_path",
    "save_context",
    "load_context",
    "delete_context",
    "list_contexts",
    "find_orphaned_contexts",
    "cleanup_orphaned_contexts",
]
