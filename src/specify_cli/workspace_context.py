"""Backward-compat shim — canonical home is specify_cli.workspace.context."""

from specify_cli.workspace.context import (  # noqa: F401
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
