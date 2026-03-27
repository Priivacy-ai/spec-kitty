"""Merge subpackage for spec-kitty merge operations.

This package provides functionality for merging work package branches
back into the main branch with pre-flight validation and state management.

Modules:
    workspace: Dedicated merge worktree lifecycle (.kittify/runtime/merge/)
    preflight: Pre-flight validation before merge
    ordering: Dependency-based merge ordering
    state: Per-mission merge state persistence and resume
"""

from __future__ import annotations

from specify_cli.merge.ordering import MergeOrderError, get_merge_order, has_dependency_info
from specify_cli.merge.preflight import (
    PreflightResult,
    WPStatus,
    run_preflight,
    run_preflight_from_context,
)
from specify_cli.merge.state import (
    MergeState,
    acquire_merge_lock,
    clear_state,
    has_active_merge,
    is_merge_locked,
    load_state,
    release_merge_lock,
    save_state,
)
from specify_cli.merge.workspace import (
    cleanup_merge_workspace,
    create_merge_workspace,
    get_merge_workspace,
    get_merge_workspace_path,
)

__all__ = [
    # Ordering
    "get_merge_order",
    "MergeOrderError",
    "has_dependency_info",
    # Preflight
    "run_preflight",
    "run_preflight_from_context",
    "PreflightResult",
    "WPStatus",
    # State persistence
    "MergeState",
    "save_state",
    "load_state",
    "clear_state",
    "has_active_merge",
    "acquire_merge_lock",
    "release_merge_lock",
    "is_merge_locked",
    # Workspace
    "create_merge_workspace",
    "cleanup_merge_workspace",
    "get_merge_workspace",
    "get_merge_workspace_path",
]
