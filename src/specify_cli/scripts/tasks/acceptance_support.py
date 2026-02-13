#!/usr/bin/env python3
"""Acceptance workflow utilities for standalone script usage.

This module is the script entrypoint for acceptance workflows, used by
``tasks_cli.py``.  All core logic is delegated to
``specify_cli.core.acceptance_core`` via the same import-resolution strategy
used by ``task_helpers.py`` (installed package -> sibling file -> source tree).

This module adds:
- Standalone ``detect_feature_slug`` that does **not** depend on
  ``specify_cli.core.feature_detection`` (keeping the script self-contained).
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Mapping, Optional

from task_helpers import (
    TaskCliError,
    run_git,
)


# ---------------------------------------------------------------------------
# Core module import resolution
# ---------------------------------------------------------------------------

def _load_module_from_file(filepath: Path, module_name: str) -> ModuleType:
    """Load a Python module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {filepath}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_acceptance_core() -> ModuleType:
    """Import the acceptance core module from the best available source."""
    # Strategy 1: installed package
    try:
        mod = importlib.import_module("specify_cli.core.acceptance_core")
        if hasattr(mod, "collect_feature_summary"):
            return mod
    except ImportError:
        pass

    script_dir = Path(__file__).resolve().parent

    # Strategy 2: sibling file (.kittify/scripts/tasks/acceptance_core.py)
    local_core = script_dir / "acceptance_core.py"
    if local_core.is_file():
        return _load_module_from_file(local_core, "acceptance_core")

    # Strategy 3: source tree (src/specify_cli/scripts/tasks/ -> src/specify_cli/core/)
    source_core = script_dir.parents[1] / "core" / "acceptance_core.py"
    if source_core.is_file():
        return _load_module_from_file(
            source_core, "specify_cli.core.acceptance_core"
        )

    raise ImportError(
        "Cannot locate acceptance_core module. "
        "Ensure spec-kitty-cli is installed (pip install spec-kitty-cli) "
        "or that the source tree is intact."
    )


_core = _import_acceptance_core()

# ---------------------------------------------------------------------------
# Re-export core symbols
# ---------------------------------------------------------------------------

AcceptanceMode = _core.AcceptanceMode
AcceptanceError = _core.AcceptanceError
ArtifactEncodingError = _core.ArtifactEncodingError
WorkPackageState = _core.WorkPackageState
AcceptanceSummary = _core.AcceptanceSummary
AcceptanceResult = _core.AcceptanceResult

collect_feature_summary = _core.collect_feature_summary
choose_mode = _core.choose_mode
perform_acceptance = _core.perform_acceptance
normalize_feature_encoding = _core.normalize_feature_encoding


# ---------------------------------------------------------------------------
# Standalone feature detection (no dependency on core.feature_detection)
# ---------------------------------------------------------------------------

def detect_feature_slug(
    repo_root: Path,
    *,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Detect feature slug from environment, git branch, or current directory.

    This is a standalone implementation that does **not** depend on
    ``specify_cli.core.feature_detection``, keeping the script entrypoint
    self-contained for use in packaged user projects.

    Priority:
    1. ``SPECIFY_FEATURE`` environment variable
    2. Git branch name (if starts with ``###-``)
    3. Current directory path (walks up looking for ``.worktrees`` or
       ``###-`` pattern)

    Raises:
        AcceptanceError: If feature cannot be auto-detected
    """
    env = env or os.environ
    if "SPECIFY_FEATURE" in env and env["SPECIFY_FEATURE"].strip():
        return env["SPECIFY_FEATURE"].strip()

    try:
        branch = (
            run_git(
                ["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, check=True
            )
            .stdout.strip()
        )
        if branch and branch != "HEAD" and re.match(r"^\d{3}-", branch):
            return branch
    except TaskCliError:
        pass

    cwd = (cwd or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if parent.name.startswith(".worktrees"):
            parts = list(parent.parts)
            try:
                idx = parts.index(".worktrees")
                candidate = parts[idx + 1]
                if re.match(r"^\d{3}-", candidate):
                    return candidate
            except (ValueError, IndexError):
                continue
        if parent.name.startswith("0") and re.match(r"^\d{3}-", parent.name):
            return parent.name

    raise AcceptanceError(
        "Unable to determine feature slug automatically. Provide --feature explicitly."
    )


__all__ = [
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_feature_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
