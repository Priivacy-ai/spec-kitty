"""Canonical API response types for the glossary domain service.

These TypedDicts define the read-only API surface for FR-016.
Callers in dashboard/api/routers/glossary.py and dashboard/api/models.py
import from here.
"""
from __future__ import annotations

from typing import TypedDict


class GlossaryTermRecord(TypedDict):
    """Single glossary term returned by ``GET /api/glossary-terms``."""

    surface: str
    definition: str
    status: str  # "active" | "draft" | "deprecated"
    confidence: float  # 0.0–1.0


class GlossaryHealthResponse(TypedDict, total=False):
    """Response from ``GET /api/glossary-health``."""

    total_terms: int
    active_count: int
    draft_count: int
    deprecated_count: int
    high_severity_drift_count: int
    orphaned_term_count: int
    entity_pages_generated: bool
    entity_pages_path: str | None
    last_conflict_at: str | None
