#!/usr/bin/env python3
"""Thin re-export shim for Spec Kitty task prompt management.

All logic has been consolidated into ``specify_cli.task_utils.support``
(FR-007 / mission single-authority-topology-cleanup-01KVRJ6P WP11).
This module re-exports every previously-public name so existing importers
remain unaffected.

The two task_helpers-specific items that have no twin in support.py are
kept here:

* ``_normalize_status_path`` — private helper used only by ``path_has_changes``
* ``path_has_changes`` — public API with no equivalent in support.py
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.task_utils.support import (
    LANES,
    TIMESTAMP_FORMAT,
    TaskCliError,
    WorkPackage,
    activity_entries,
    append_activity_log,
    build_document,
    detect_conflicting_wp_status,
    ensure_lane,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    git_status_lines,
    load_meta,
    locate_work_package,
    normalize_note,
    now_utc,
    run_git,
    set_scalar,
    split_frontmatter,
)

__all__ = [
    "LANES",
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
    "load_meta",
    "locate_work_package",
    "normalize_note",
    "now_utc",
    "path_has_changes",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]


# ---------- task_helpers-specific: no twin in support.py ----------


def _normalize_status_path(raw: str) -> str:
    candidate = raw.split(" -> ", 1)[0].strip()
    candidate = candidate.lstrip("./")
    return candidate.replace("\\", "/")


def path_has_changes(status_lines: list[str], path: Path) -> bool:
    """Return True if git status indicates modifications for the given path."""
    normalized = _normalize_status_path(str(path))
    for line in status_lines:
        if len(line) < 4:
            continue
        candidate = _normalize_status_path(line[3:])
        if candidate == normalized:
            return True
    return False
