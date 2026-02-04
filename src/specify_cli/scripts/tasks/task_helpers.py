#!/usr/bin/env python3
"""Standalone helpers for Spec Kitty task prompt management.

Implementation note (v0.13+):
    All helper logic now lives in ``task_helpers_shared.py``.
    This module imports and re-exports every public symbol from the shared
    module so that ``tasks_cli.py`` and other scripts continue to work
    unchanged via ``from task_helpers import ...``.

    Import resolution finds the shared module file by checking:

    1. Installed package (``specify_cli.task_helpers_shared``).
    2. Sibling file (``task_helpers_shared.py`` alongside this file,
       e.g. in ``.kittify/scripts/tasks/``).
    3. Source tree (``../../task_helpers_shared.py`` relative to this
       file's location in ``src/specify_cli/scripts/tasks/``).
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SHARED_SYMBOLS = [
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


def _load_module_from_file(filepath: Path, module_name: str) -> ModuleType:
    """Load a Python module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {filepath}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_shared() -> ModuleType:
    """Import the shared module from the best available source."""
    # Strategy 1: installed package
    try:
        mod = importlib.import_module("specify_cli.task_helpers_shared")
        if hasattr(mod, "find_repo_root"):
            return mod
    except ImportError:
        pass

    script_dir = Path(__file__).resolve().parent

    # Strategy 2: sibling file (.kittify/scripts/tasks/task_helpers_shared.py)
    local_shared = script_dir / "task_helpers_shared.py"
    if local_shared.is_file():
        return _load_module_from_file(local_shared, "task_helpers_shared")

    # Strategy 3: source tree (src/specify_cli/scripts/tasks/ -> src/specify_cli/)
    source_shared = script_dir.parents[1] / "task_helpers_shared.py"
    if source_shared.is_file():
        return _load_module_from_file(
            source_shared, "specify_cli.task_helpers_shared"
        )

    raise ImportError(
        "Cannot locate task_helpers_shared module. "
        "Ensure spec-kitty-cli is installed (pip install spec-kitty-cli) "
        "or that the source tree is intact."
    )


_shared = _import_shared()

# Pull all symbols into this module's namespace
for _name in _SHARED_SYMBOLS:
    globals()[_name] = getattr(_shared, _name)

__all__ = list(_SHARED_SYMBOLS)
