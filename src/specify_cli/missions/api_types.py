"""Canonical API response types for the missions domain service.

These TypedDicts define the read-only API surface for mission/feature
registry and features-list endpoints. FR-019.
"""
from __future__ import annotations

from typing import Any, TypedDict

from specify_cli.status.api_types import KanbanStats


class ArtifactInfo(TypedDict):
    """Per-artifact existence / stat metadata produced by ``scanner.py``."""

    exists: bool
    mtime: float | None
    size: int | None


class ResearchArtifact(TypedDict):
    """Single artifact entry in the research response."""

    name: str
    path: str
    icon: str


class ResearchResponse(TypedDict):
    """Response from ``GET /api/research/{feature_id}``."""

    main_file: str | None
    artifacts: list[ResearchArtifact]


class MissionRecord(TypedDict, total=False):
    """Single mission record from :func:`scanner.build_mission_registry`.

    This is the canonical wire shape for per-mission data keyed by
    ``mission_id`` (a ULID) or a pseudo-key (``legacy:<slug>`` or
    ``orphan:<path.name>``).

    Fields
    ------
    mission_id
        The registry key itself.  For assigned/pending missions this is the
        ULID from ``meta.json``.  For legacy missions it is ``legacy:<slug>``;
        for orphan missions it is ``orphan:<dir-name>``.
    mission_slug
        Directory name (e.g. ``"080-foo"``).  Used for display and URL routing.
    display_number
        Integer numeric prefix (e.g. ``80`` for ``080-foo``), or ``None`` for
        pre-merge missions.  This is a *display* metadata field — it is NOT
        the identity key.
    mid8
        First 8 characters of the ULID ``mission_id``, precomputed for compact
        display.  ``None`` for pseudo-key (legacy/orphan) records.
    feature_dir
        Absolute path to the mission directory as a string.
    """

    mission_id: str  # ULID or pseudo-key
    mission_slug: str  # directory name
    display_number: int | None  # numeric prefix for display sort; None = pre-merge
    mid8: str | None  # first 8 chars of mission_id; None for pseudo-keys
    feature_dir: str  # absolute path as string


class WorktreeInfo(TypedDict):
    """Per-feature worktree metadata."""

    path: str | None
    exists: bool


class WorkflowStatus(TypedDict):
    """Workflow progression status (specify → plan → tasks → implement)."""

    specify: str
    plan: str
    tasks: str
    implement: str


class FeatureItem(TypedDict):
    """Single feature entry produced by ``scan_all_features``."""

    id: str
    name: str
    display_name: str
    path: str
    artifacts: dict[str, ArtifactInfo]
    workflow: WorkflowStatus
    kanban_stats: KanbanStats
    meta: dict[str, Any]
    worktree: WorktreeInfo
    is_legacy: bool  # added by handler, not scanner


class MissionContext(TypedDict, total=False):
    """Active mission context block in the features-list response.

    ``feature`` is present only when an active feature is detected.
    ``path`` may be ``None`` when produced by ``format_path_for_display``.
    """

    name: str
    domain: str
    version: str
    slug: str
    description: str
    path: str | None
    feature: str  # absent when no active feature


class FeaturesListResponse(TypedDict):
    """Response from ``GET /api/features``."""

    features: list[FeatureItem]
    active_feature_id: str | None
    project_path: str | None
    worktrees_root: str | None
    active_worktree: str | None
    active_mission: MissionContext


class FeaturesListErrorResponse(TypedDict):
    """Error variant of the features-list response (HTTP 500)."""

    error: str
    detail: str
