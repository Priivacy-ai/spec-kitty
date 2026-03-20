#!/usr/bin/env python3
"""Thin compatibility wrapper for standalone tasks_cli.py usage.

All logic lives in specify_cli.acceptance. This module re-exports
the public API for backwards compatibility with standalone scripts.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Add repo src/ root so specify_cli.* is importable from checkout.
# NOTE: Always break on the first matching src/ to avoid traversing past
# a git worktree into the main repo (which has its own src/specify_cli).
_candidate = SCRIPT_DIR
for _ in range(6):
    _candidate = _candidate.parent
    _src = _candidate / "src"
    if (_src / "specify_cli").is_dir():
        if str(_src) not in sys.path:
            sys.path.insert(0, str(_src))
        break

from specify_cli.acceptance import (  # noqa: E402
    AcceptanceError,
    AcceptanceMode,
    AcceptanceResult,
    AcceptanceSummary,
    ArtifactEncodingError,
    WorkPackageState,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    normalize_feature_encoding,
    perform_acceptance,
)

# Re-export task_helpers utilities that callers historically accessed
# through this module (e.g. acc.run_git in tests).
from task_helpers import run_git  # noqa: E402, F401

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
