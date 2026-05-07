"""Backward-compat shim — all types have moved to canonical locations.

removal_release: FastAPI transport migration milestone
"""
# ruff: noqa: F401
from dashboard.api.presentation_types import (  # noqa: F401
    ArtifactDirectoryFile,
    ArtifactDirectoryResponse,
)
from kernel.api_types import (  # noqa: F401
    CurrentFeatureDetected,
    CurrentFeatureNotDetected,
    DashboardHealthInfo,
    DiagnosticsErrorResponse,
    DiagnosticsFeatureStatus,
    DiagnosticsResponse,
    ErrorResponse,
    FileIntegrity,
    HealthResponse,
    SyncInfo,
    SyncTriggerSuccess,
)
from specify_cli.charter_lint.types import DecayWatchTileResponse  # noqa: F401
from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord  # noqa: F401
from specify_cli.missions.api_types import (  # noqa: F401
    ArtifactInfo,
    FeatureItem,
    FeaturesListErrorResponse,
    FeaturesListResponse,
    MissionContext,
    MissionRecord,
    ResearchArtifact,
    ResearchResponse,
    WorkflowStatus,
    WorktreeInfo,
)
from specify_cli.status.api_types import (  # noqa: F401
    KanbanResponse,
    KanbanStats,
    KanbanTaskData,
)

__all__ = [
    "ArtifactDirectoryFile",
    "ArtifactDirectoryResponse",
    "ArtifactInfo",
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
    "SyncInfo",
    "SyncTriggerSuccess",
    "WorkflowStatus",
    "WorktreeInfo",
]

__removal_release__ = "FastAPI transport migration milestone"
