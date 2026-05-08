"""Canonical API response types for the status domain service.

These TypedDicts define the read-only API surface for kanban/status
endpoints. FR-019.
"""
from __future__ import annotations

from typing import Any, TypedDict


class KanbanTaskData(TypedDict, total=False):
    """Single work-package card on the kanban board.

    The ``encoding_error`` variant (produced when ``read_file_resilient``
    fails) omits ``agent_profile`` and ``role`` and adds
    ``encoding_error: True``.
    """

    id: str
    title: str
    lane: str
    subtasks: list[Any]
    agent: str
    model: str
    agent_profile: str
    role: str
    assignee: str
    phase: str
    prompt_markdown: str
    prompt_path: str
    encoding_error: bool  # present only on decode-failure variant


class KanbanStats(TypedDict, total=False):
    """Per-feature kanban summary counts.

    ``error`` is present only when the event log is missing or unreadable.
    """

    total: int
    planned: int
    doing: int
    for_review: int
    approved: int
    done: int
    error: str


class KanbanResponse(TypedDict):
    """Response from ``GET /api/kanban/{feature_id}``."""

    lanes: dict[str, list[KanbanTaskData]]
    is_legacy: bool
    upgrade_needed: bool
    weighted_percentage: float | None
