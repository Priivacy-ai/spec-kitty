"""Backward-compat shim — all types have moved to dashboard.api_types.

removal_release: FastAPI transport migration milestone
"""
# ruff: noqa: F401
from dashboard.api_types import (  # noqa: F401
    ArtifactDirectoryFile,
    ArtifactDirectoryResponse,
    ArtifactInfo,
    CurrentFeatureDetected,
    CurrentFeatureNotDetected,
    DashboardHealthInfo,
    DecayWatchTileResponse,
    DiagnosticsErrorResponse,
    DiagnosticsFeatureStatus,
    DiagnosticsResponse,
    ErrorResponse,
    FeatureItem,
    FeaturesListErrorResponse,
    FeaturesListResponse,
    FileIntegrity,
    GlossaryHealthResponse,
    GlossaryTermRecord,
    HealthResponse,
    KanbanResponse,
    KanbanStats,
    KanbanTaskData,
    MissionContext,
    MissionRecord,
    ResearchArtifact,
    ResearchResponse,
    SyncInfo,
    SyncTriggerSuccess,
    WorkflowStatus,
    WorktreeInfo,
    __all__,
)

__removal_release__ = "FastAPI transport migration milestone"
