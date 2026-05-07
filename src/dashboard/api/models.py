"""Pydantic v2 response models for the FastAPI dashboard transport.

Each class mirrors a `TypedDict` in ``src/dashboard/api_types.py`` exactly:
field names, optional/required semantics, and value types are preserved so
the existing wire shape stays stable.

The TypedDicts in ``api_types.py`` remain the canonical contract for any
consumer that prefers the lighter representation; the Pydantic models here
exist so FastAPI can auto-generate the OpenAPI document and so
non-runtime consumers can validate payloads.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Leaf / reusable types
# ---------------------------------------------------------------------------


class _DashboardModel(BaseModel):
    """Base for every dashboard response model.

    ``extra="allow"`` is intentional. Production scanner code emits a
    superset of the originally declared TypedDict fields (see e.g.
    ``KanbanStats.weighted_percentage`` added by the event-log path).
    Forbidding extras here would crash ``/api/features`` whenever the
    scanner grows a new optional field — a strictly tighter behavior
    than the legacy ``BaseHTTPServer`` stack, which just serialised
    whatever ``json.dumps`` accepted.

    Schema drift is still caught by the OpenAPI snapshot test
    (``tests/test_dashboard/test_openapi_snapshot.py``); the model
    surface is the contract that matters at the API boundary, not the
    runtime input dict shape.
    """

    model_config = ConfigDict(extra="allow")


class ArtifactDirectoryFile(_DashboardModel):
    name: str
    path: str
    icon: str


class ArtifactDirectoryResponse(_DashboardModel):
    files: list[ArtifactDirectoryFile]


class ArtifactInfo(_DashboardModel):
    exists: bool
    mtime: float | None
    size: int | None


class ErrorResponse(_DashboardModel):
    error: str
    detail: str | None = None
    status: int | None = None


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class SyncInfo(_DashboardModel):
    """Nested sync block; all keys optional matching `total=False`."""

    running: bool | None = None
    last_sync: str | None = None
    consecutive_failures: int | None = None
    error: str | None = None


class HealthResponse(_DashboardModel):
    status: str | None = None
    project_path: str | None = None
    sync: SyncInfo | None = None
    websocket_status: str | None = None
    token: str | None = None


# ---------------------------------------------------------------------------
# Kanban endpoint
# ---------------------------------------------------------------------------


class KanbanTaskData(_DashboardModel):
    id: str | None = None
    title: str | None = None
    lane: str | None = None
    subtasks: list[Any] | None = None
    agent: str | None = None
    model: str | None = None
    agent_profile: str | None = None
    role: str | None = None
    assignee: str | None = None
    phase: str | None = None
    prompt_markdown: str | None = None
    prompt_path: str | None = None
    encoding_error: bool | None = None


class KanbanStats(_DashboardModel):
    total: int | None = None
    planned: int | None = None
    doing: int | None = None
    for_review: int | None = None
    approved: int | None = None
    done: int | None = None
    error: str | None = None
    # Optional weighted-progress field added by the event-log path
    # (specify_cli/dashboard/scanner.py:_build_event_log_kanban_stats).
    # Not declared on the original TypedDict but emitted in production
    # responses; declared optional here so /api/features serialises
    # without raising a Pydantic validation error.
    weighted_percentage: float | None = None


class KanbanResponse(_DashboardModel):
    lanes: dict[str, list[KanbanTaskData]]
    is_legacy: bool
    upgrade_needed: bool
    weighted_percentage: float | None = None


# ---------------------------------------------------------------------------
# Research endpoint
# ---------------------------------------------------------------------------


class ResearchArtifact(_DashboardModel):
    name: str
    path: str
    icon: str


class ResearchResponse(_DashboardModel):
    main_file: str | None = None
    artifacts: list[ResearchArtifact]


# ---------------------------------------------------------------------------
# Mission registry types
# ---------------------------------------------------------------------------


class MissionRecord(_DashboardModel):
    mission_id: str | None = None
    mission_slug: str | None = None
    display_number: int | None = None
    mid8: str | None = None
    feature_dir: str | None = None


# ---------------------------------------------------------------------------
# Features-list endpoint
# ---------------------------------------------------------------------------


class WorktreeInfo(_DashboardModel):
    path: str | None = None
    exists: bool


class WorkflowStatus(_DashboardModel):
    specify: str
    plan: str
    tasks: str
    implement: str


class FeatureItem(_DashboardModel):
    id: str
    name: str
    display_name: str
    path: str
    artifacts: dict[str, ArtifactInfo]
    workflow: WorkflowStatus
    kanban_stats: KanbanStats
    meta: dict[str, Any]
    worktree: WorktreeInfo
    is_legacy: bool


class MissionContext(_DashboardModel):
    name: str | None = None
    domain: str | None = None
    version: str | None = None
    slug: str | None = None
    description: str | None = None
    path: str | None = None
    feature: str | None = None


class FeaturesListResponse(_DashboardModel):
    features: list[FeatureItem]
    active_feature_id: str | None = None
    project_path: str | None = None
    worktrees_root: str | None = None
    active_worktree: str | None = None
    active_mission: MissionContext


class FeaturesListErrorResponse(_DashboardModel):
    error: str
    detail: str


# ---------------------------------------------------------------------------
# Glossary endpoints
# ---------------------------------------------------------------------------


class GlossaryTermRecord(_DashboardModel):
    """Pydantic transport model for a single glossary term.

    Canonical TypedDict: :class:`specify_cli.glossary.types.GlossaryTermRecord`.
    Field names and types must stay in sync with that TypedDict.
    """

    surface: str
    definition: str
    status: str
    confidence: float


class GlossaryHealthResponse(_DashboardModel):
    """Pydantic transport model for the glossary health endpoint.

    Canonical TypedDict: :class:`specify_cli.glossary.types.GlossaryHealthResponse`.
    Field names and types must stay in sync with that TypedDict.
    """

    total_terms: int | None = None
    active_count: int | None = None
    draft_count: int | None = None
    deprecated_count: int | None = None
    high_severity_drift_count: int | None = None
    orphaned_term_count: int | None = None
    entity_pages_generated: bool | None = None
    entity_pages_path: str | None = None
    last_conflict_at: str | None = None


# ---------------------------------------------------------------------------
# Decay watch tile
# ---------------------------------------------------------------------------


class DecayWatchTileResponse(_DashboardModel):
    """Pydantic transport model for the decay-watch tile.

    Canonical TypedDict: :class:`dashboard.api_types.DecayWatchTileResponse`.
    Field names and types must stay in sync with that TypedDict.
    """

    has_data: bool | None = None
    scanned_at: str | None = None
    orphan_count: int | None = None
    contradiction_count: int | None = None
    staleness_count: int | None = None
    reference_integrity_count: int | None = None
    high_severity_count: int | None = None
    total_count: int | None = None
    feature_scope: str | None = None
    duration_seconds: float | None = None


# ---------------------------------------------------------------------------
# Sync-trigger endpoint — discriminated union
# ---------------------------------------------------------------------------


class SyncTriggerScheduledResponse(_DashboardModel):
    status: Literal["scheduled"]


class SyncTriggerSkippedResponse(_DashboardModel):
    status: Literal["skipped"]
    manual_mode: bool
    reason: str | None = None


class SyncTriggerUnavailableResponse(_DashboardModel):
    error: str
    reason: str | None = None


class SyncTriggerFailedResponse(_DashboardModel):
    error: str


# Type alias used as the response_model on the sync_trigger route. FastAPI
# emits this as a `oneOf` in OpenAPI.
SyncTriggerResponse = (
    SyncTriggerScheduledResponse
    | SyncTriggerSkippedResponse
    | SyncTriggerUnavailableResponse
    | SyncTriggerFailedResponse
)


# ---------------------------------------------------------------------------
# Diagnostics endpoint (complex, many nested types)
# ---------------------------------------------------------------------------


class FileIntegrity(_DashboardModel):
    total_expected: int
    total_present: int
    total_missing: int
    missing_files: list[str]


class DiagnosticsFeatureStatus(_DashboardModel):
    name: str
    state: str
    branch_exists: bool
    branch_merged: bool
    worktree_exists: bool
    worktree_path: str | None = None
    # TypedDict declared bool, but production diagnostics returns the list
    # of artifact filenames (or [] when none). Accept both for compat.
    artifacts_in_main: bool | list[str]
    artifacts_in_worktree: bool | list[str]


class CurrentFeatureDetected(_DashboardModel):
    """Documented shape when ``detected`` is true.

    All fields are optional so production data that omits any field
    (e.g. when the diagnostics runner returns an empty dict for an
    indeterminate feature state) does not cause a 500.
    """

    detected: Literal[True] | None = None
    name: str | None = None
    state: str | None = None
    branch_exists: bool | None = None
    branch_merged: bool | None = None
    worktree_exists: bool | None = None
    worktree_path: str | None = None
    # TypedDict declared bool, but production diagnostics returns the list
    # of artifact filenames (or [] when none). Accept both for compat.
    artifacts_in_main: bool | list[str] | None = None
    artifacts_in_worktree: bool | list[str] | None = None


class CurrentFeatureNotDetected(_DashboardModel):
    detected: Literal[False] | None = None
    error: str | None = None


# Use a permissive dict alias so the production diagnostics handler that
# may return an empty {} or a free-form shape does not crash response_model
# validation. The Pydantic models above remain in the OpenAPI doc as the
# canonical documented shape; the runtime accepts whatever the legacy
# handler returned.
CurrentFeatureBlock = dict[str, Any]


class DashboardHealthInfo(_DashboardModel):
    metadata_exists: bool | None = None
    can_start: bool | None = None
    startup_test: str | None = None
    url: str | None = None
    port: int | None = None
    pid: int | None = None
    has_pid: bool | None = None
    responding: bool | None = None
    parse_error: str | None = None
    test_url: str | None = None
    test_port: int | None = None
    startup_error: str | None = None


class DiagnosticsResponse(_DashboardModel):
    project_path: str
    current_working_directory: str
    git_branch: str | None = None
    in_worktree: bool
    worktrees_exist: bool
    active_mission: str | None = None
    file_integrity: FileIntegrity
    worktree_overview: dict[str, Any]
    current_feature: CurrentFeatureBlock
    all_features: list[DiagnosticsFeatureStatus]
    dashboard_health: DashboardHealthInfo
    observations: list[str]
    issues: list[str]


class DiagnosticsErrorResponse(_DashboardModel):
    error: str
    traceback: str


# ---------------------------------------------------------------------------
# Shutdown endpoint
# ---------------------------------------------------------------------------


class ShutdownResponse(_DashboardModel):
    status: Literal["stopping"]


# --- HATEOAS-LITE marker classes (introduced by mission
# mission-registry-and-api-boundary-doctrine-01KQPDBB; mission B will
# subclass ResourceModel for the new resource-oriented endpoints) ---


class Link(BaseModel):
    """A single HATEOAS-LITE hyperlink. Subset of HAL's link object.

    See doctrine paradigm ``hateoas-lite`` (src/doctrine/paradigms/shipped/
    hateoas-lite.paradigm.yaml) for the full convention and future-graduation
    triggers (HAL / JSON:API).
    """

    href: str
    method: str = "GET"


class ResourceModel(BaseModel):
    """Marker base class for resource-oriented response models.

    Declares ``_links`` as a proper Pydantic field (alias ``_links``, stored
    internally as ``links``) so it appears in the OpenAPI schema and is
    visible to generated clients. Subclasses inherit this field and must also
    carry a ``_links: dict[str, Link]`` type annotation (for the arch test
    ``test_resource_models_have_links.py``).

    Construction: pass links via either keyword arg:
      - ``ResourceModel(**{"_links": {...}})``  (alias — existing pattern)
      - ``ResourceModel(links={...})``          (field name — with populate_by_name)
    """

    model_config = ConfigDict(populate_by_name=True)
    links: dict[str, Link] = Field(
        default_factory=dict,
        alias="_links",
        serialization_alias="_links",
    )


# ---------------------------------------------------------------------------
# HATEOAS-LITE resource models (introduced by mission
# resource-oriented-mission-api-01KQQRF2, WP01)
# ---------------------------------------------------------------------------


class ReviewEvidence(BaseModel):
    """Evidence from a review event (in_review -> approved/rejected)."""

    reviewed_by: str
    reviewed_at: datetime
    verdict: Literal["approved", "rejected"]
    notes: str | None = None


class WorkPackageAssignment(BaseModel):
    """Ownership contract for a single WP.

    The agent identity is decomposed for UI consumers (kanban badges, modal
    headers): `agent` is the tool (`claude`, `codex`, ...), `model` is the
    underlying model (`sonnet-4-6`, `gpt-4o`, ...), `agent_profile` is the
    doctrine profile (`python-pedro`), and `role` is the role label
    (`implementer`, `reviewer`, ...). Compound strings stored in WP frontmatter
    (e.g. `claude:sonnet-4-6:implementer:implementer`) are parsed at the
    transport boundary so consumers never have to split them.
    """

    wp_id: str
    lane: str
    agent: str | None = None
    model: str | None = None
    assignee: str | None = None
    agent_profile: str | None = None
    role: str | None = None
    claimed_at: datetime | None = None
    last_event_id: str | None = None
    blocked_reason: str | None = None
    review_evidence: ReviewEvidence | None = None


class LaneCounts(BaseModel):
    """Lane-keyed integer counts for a mission's work packages."""

    total: int = 0
    planned: int = 0
    claimed: int = 0
    in_progress: int = 0
    for_review: int = 0
    in_review: int = 0
    approved: int = 0
    done: int = 0
    blocked: int = 0
    canceled: int = 0


class MissionSummary(ResourceModel):
    """Lightweight mission representation for list responses."""

    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    is_legacy: bool = False
    # _links keys: self, status, workpackages
    _links: dict[str, Link]


class Mission(ResourceModel):
    """Full mission detail representation."""

    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    created_at: datetime | None = None
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    is_legacy: bool = False
    purpose_tldr: str | None = None
    purpose_context: str | None = None
    # _links keys: self, status, workpackages
    _links: dict[str, Link]


class MissionStatus(ResourceModel):
    """Lane counts and progress for a single mission — polling-friendly."""

    mission_id: str
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    done_count: int
    total_count: int
    current_phase: int = 2
    # _links keys: self, mission
    _links: dict[str, Link]


class WorkPackageSummary(ResourceModel):
    """Lightweight WP representation for list responses."""

    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    # _links keys: self, mission
    _links: dict[str, Link]


class WorkPackage(ResourceModel):
    """Full WP detail representation."""

    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    subtasks_done: int
    subtasks_total: int
    dependencies: list[str]
    requirement_refs: list[str]
    phase: str | None = None
    prompt_path: str | None = None
    prompt_markdown: str | None = None
    prompt_ref: str | None = None
    # _links keys: self, mission, workpackages
    _links: dict[str, Link]


__all__ = [
    "ArtifactDirectoryFile",
    "ArtifactDirectoryResponse",
    "ArtifactInfo",
    "CurrentFeatureBlock",
    "CurrentFeatureDetected",
    "CurrentFeatureNotDetected",
    "DashboardHealthInfo",
    "DecayWatchTileResponse",
    "DiagnosticsErrorResponse",
    "DiagnosticsFeatureStatus",
    "DiagnosticsResponse",
    "ErrorResponse",
    "FeatureItem",
    "FeaturesListErrorResponse",
    "FeaturesListResponse",
    "FileIntegrity",
    "GlossaryHealthResponse",
    "GlossaryTermRecord",
    "HealthResponse",
    "KanbanResponse",
    "KanbanStats",
    "KanbanTaskData",
    "MissionContext",
    "MissionRecord",
    "ResearchArtifact",
    "ResearchResponse",
    "ShutdownResponse",
    "SyncInfo",
    "SyncTriggerFailedResponse",
    "SyncTriggerResponse",
    "SyncTriggerScheduledResponse",
    "SyncTriggerSkippedResponse",
    "SyncTriggerUnavailableResponse",
    "WorkflowStatus",
    "WorktreeInfo",
    "Link",
    "ResourceModel",
    "ReviewEvidence",
    "WorkPackageAssignment",
    "LaneCounts",
    "MissionSummary",
    "Mission",
    "MissionStatus",
    "WorkPackageSummary",
    "WorkPackage",
]
