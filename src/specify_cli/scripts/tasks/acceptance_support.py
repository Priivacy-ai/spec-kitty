"""Thin compatibility wrapper for standalone tasks_cli.py usage.

All logic lives in specify_cli.acceptance. This module re-exports
the public API for backwards compatibility with standalone scripts.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Add repo src/ root so specify_cli.* is importable from checkout or local copies.
_bootstrap_marker = SCRIPT_DIR.parent / ".spec-kitty-src-root"
if _bootstrap_marker.exists():
    try:
        _marker_src = Path(_bootstrap_marker.read_text(encoding="utf-8").strip()).expanduser()
    except OSError:
        _marker_src = None
    if _marker_src and (_marker_src / "specify_cli").is_dir() and str(_marker_src) not in sys.path:
        sys.path.insert(0, str(_marker_src))

# Fall back to walking parents when running from a source checkout.
# Always break on the first matching src/ to avoid traversing past
# a git worktree into the main repo (which has its own src/specify_cli).
_candidate = SCRIPT_DIR
for _ in range(6):
    _candidate = _candidate.parent
    _src = _candidate / "src"
    if (_src / "specify_cli").is_dir():
        if str(_src) not in sys.path:
            sys.path.insert(0, str(_src))
        break

_EXPORT_NAMES = (
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_mission_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
)


def _load_acceptance_api():
    core = importlib.import_module("specify_cli.acceptance")
    if all(hasattr(core, name) for name in _EXPORT_NAMES):
        return {name: getattr(core, name) for name in _EXPORT_NAMES}

    legacy = importlib.import_module("specify_cli.scripts.tasks.acceptance_support")
    return {name: getattr(legacy, name) for name in _EXPORT_NAMES}


globals().update(_load_acceptance_api())

__all__ = [
    "AcceptanceError",
    "AcceptanceMode",
    "AcceptanceResult",
    "AcceptanceSummary",
    "ArtifactEncodingError",
    "WorkPackageState",
    "choose_mode",
    "collect_feature_summary",
    "detect_mission_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
