#!/usr/bin/env python3
"""Shared utilities for manipulating Spec Kitty task prompts.

DEPRECATED: This module is deprecated as of v0.10.0.
Use `spec-kitty agent tasks` commands instead.

This file will be removed in the next release.
See: src/specify_cli/cli/commands/agent/tasks.py

Migration Guide:
- tasks_cli.py update → spec-kitty agent tasks move-task
- For all other operations, use the new agent tasks commands

Implementation note (v0.13+):
    All helper logic now lives in ``specify_cli.task_helpers_shared``.
    This module re-exports every public symbol from the shared module and
    adds the ``locate_work_package`` override that resolves via the main
    repository root (worktree-aware).
"""

from __future__ import annotations

from pathlib import Path

# Re-export everything from the shared module so existing callers that do
# ``from specify_cli.tasks_support import X`` continue to work unchanged.
from specify_cli.task_helpers_shared import (  # noqa: F401
    LANES,
    LEGACY_LANE_DIRS,
    TIMESTAMP_FORMAT,
    TaskCliError,
    WorkPackage,
    append_activity_log,
    activity_entries,
    build_document,
    detect_conflicting_wp_status,
    ensure_lane,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    git_status_lines,
    is_legacy_format,
    load_meta,
    match_frontmatter_line,
    normalize_note,
    now_utc,
    path_has_changes,
    run_git,
    set_scalar,
    split_frontmatter,
)

# Re-export the shared locate_work_package as the base implementation
from specify_cli.task_helpers_shared import locate_work_package as _shared_locate_work_package


def locate_work_package(repo_root: Path, feature: str, wp_id: str) -> WorkPackage:
    """Locate a work package by ID, supporting both legacy and new formats.

    Always uses main repo's kitty-specs/ regardless of current directory.
    Worktrees should not contain kitty-specs/ (excluded via sparse checkout).

    This override resolves the main repository root via
    ``specify_cli.core.paths.get_main_repo_root`` before delegating to the
    shared implementation.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    from specify_cli.core.paths import get_main_repo_root

    # Always use main repo's kitty-specs - it's the source of truth.
    # This fixes the bug where worktree's stale kitty-specs/ would be used.
    main_root = get_main_repo_root(repo_root)
    return _shared_locate_work_package(main_root, feature, wp_id)


__all__ = [
    "LANES",
    "LEGACY_LANE_DIRS",
    "TIMESTAMP_FORMAT",
    "TaskCliError",
    "WorkPackage",
    "append_activity_log",
    "activity_entries",
    "build_document",
    "detect_conflicting_wp_status",
    "ensure_lane",
    "extract_scalar",
    "find_repo_root",
    "get_lane_from_frontmatter",
    "git_status_lines",
    "is_legacy_format",
    "load_meta",
    "locate_work_package",
    "match_frontmatter_line",
    "normalize_note",
    "now_utc",
    "path_has_changes",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]
