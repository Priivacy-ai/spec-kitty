"""Canonical API response types for the charter lint domain service.

These TypedDicts define the read-only API surface for FR-017.
Callers in dashboard/api/routers/lint.py import from here.
"""
from __future__ import annotations

from typing import TypedDict


class DecayWatchTileResponse(TypedDict, total=False):
    """Response from ``GET /api/charter-lint``."""

    has_data: bool
    scanned_at: str | None
    orphan_count: int
    contradiction_count: int
    staleness_count: int
    reference_integrity_count: int
    high_severity_count: int
    total_count: int
    feature_scope: str | None
    duration_seconds: float | None
