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

__all__: list[str] = []
