"""Workspace utilities for spec-kitty.

This package owns the canonical helpers that resolve "where on disk does
the mission live?" from any cwd, including cwds inside a git worktree.

WP07 (mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``) owns
``assert_initialized.py`` and is intentionally not re-exported here.
"""

from __future__ import annotations

from .root_resolver import (
    WorkspaceRootNotFound,
    canonicalize_feature_dir,
    resolve_canonical_root,
)
from .context import (
    NormalizedWorkPackage,
    ResolvedWorkspace,
    WorkspaceContext,
    build_feature_context_index,
    build_normalized_wp_index,
    clear_workspace_resolution_caches,
    cleanup_orphaned_contexts,
    delete_context,
    find_context_for_wp,
    find_orphaned_contexts,
    get_context_path,
    get_normalized_wp,
    get_workspaces_dir,
    list_contexts,
    load_context,
    resolve_feature_worktree,
    resolve_workspace_for_wp,
    save_context,
)

__all__ = [
    # root_resolver
    "WorkspaceRootNotFound",
    "canonicalize_feature_dir",
    "resolve_canonical_root",
    # context
    "NormalizedWorkPackage",
    "ResolvedWorkspace",
    "WorkspaceContext",
    "build_feature_context_index",
    "build_normalized_wp_index",
    "clear_workspace_resolution_caches",
    "cleanup_orphaned_contexts",
    "delete_context",
    "find_context_for_wp",
    "find_orphaned_contexts",
    "get_context_path",
    "get_normalized_wp",
    "get_workspaces_dir",
    "list_contexts",
    "load_context",
    "resolve_feature_worktree",
    "resolve_workspace_for_wp",
    "save_context",
]
