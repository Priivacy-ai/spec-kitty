"""Merge subpackage for spec-kitty merge operations.

This package provides functionality for merging work package branches
back into the main branch with pre-flight validation, conflict forecasting,
and automatic status file resolution.

Modules:
    preflight: Pre-flight validation before merge
    forecast: Conflict prediction for dry-run mode
    ordering: Dependency-based merge ordering
    status_resolver: Auto-resolution of status file conflicts
    state: Merge state persistence and resume
    executor: Core merge execution logic
"""

from __future__ import annotations

from specify_cli.merge.executor import (
    MergeExecutionError,
    MergeResult,
    execute_legacy_merge,
    execute_merge,
)
from specify_cli.merge.forecast import ConflictPrediction, is_status_file, predict_conflicts
from specify_cli.merge.ordering import MergeOrderError, get_merge_order, has_dependency_info
from specify_cli.merge.preflight import PreflightResult, WPStatus, run_preflight
from specify_cli.merge.state import (
    MergeState,
    clear_state,
    has_active_merge,
    load_state,
    save_state,
)
from specify_cli.merge.status_resolver import ResolutionResult, resolve_status_conflicts

__all__ = [
    # Executor
    "execute_merge",
    "execute_legacy_merge",
    "MergeResult",
    "MergeExecutionError",
    # Forecast
    "predict_conflicts",
    "ConflictPrediction",
    "is_status_file",
    # Ordering
    "get_merge_order",
    "MergeOrderError",
    "has_dependency_info",
    # Preflight
    "run_preflight",
    "PreflightResult",
    "WPStatus",
    # Status resolver
    "resolve_status_conflicts",
    "ResolutionResult",
    # State persistence
    "MergeState",
    "save_state",
    "load_state",
    "clear_state",
    "has_active_merge",
]
