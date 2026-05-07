"""Canonical API response types for cross-cutting kernel concerns.

These TypedDicts define the read-only API surface for shared/cross-cutting
types used by multiple domain services. FR-016, FR-017, FR-019.

Types here are re-exported by dashboard/api_types.py for backward
compatibility.
"""
from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ErrorResponse(TypedDict):
    """Generic error envelope returned by ``_send_json`` on failure."""

    error: str
    detail: NotRequired[str]
    status: NotRequired[int]


class SyncInfo(TypedDict, total=False):
    """Nested sync block inside ``HealthResponse``."""

    running: bool
    last_sync: str | None
    consecutive_failures: int
    error: str  # present only on exception path


class HealthResponse(TypedDict, total=False):
    """Response from ``GET /api/health``."""

    status: str
    project_path: str
    sync: SyncInfo
    websocket_status: str
    token: str  # conditionally present


class SyncTriggerSuccess(TypedDict):
    """Successful response from ``POST /api/sync/trigger``."""

    status: str  # "scheduled"


class FileIntegrity(TypedDict):
    """File-integrity section of the diagnostics response."""

    total_expected: int
    total_present: int
    total_missing: int
    missing_files: list[str]


class DiagnosticsFeatureStatus(TypedDict):
    """Per-feature status in the diagnostics all_features list."""

    name: str
    state: str
    branch_exists: bool
    branch_merged: bool
    worktree_exists: bool
    worktree_path: str | None
    artifacts_in_main: bool
    artifacts_in_worktree: bool


class CurrentFeatureDetected(TypedDict):
    """current_feature block when detection succeeds."""

    detected: bool  # True
    name: str
    state: str
    branch_exists: bool
    branch_merged: bool
    worktree_exists: bool
    worktree_path: str | None
    artifacts_in_main: bool
    artifacts_in_worktree: bool


class CurrentFeatureNotDetected(TypedDict):
    """current_feature block when detection fails."""

    detected: bool  # False
    error: str


class DashboardHealthInfo(TypedDict, total=False):
    """Dashboard health section of the diagnostics response."""

    metadata_exists: bool
    can_start: bool | None
    startup_test: str | None
    url: str
    port: int
    pid: int | None
    has_pid: bool
    responding: bool
    parse_error: str
    test_url: str
    test_port: int
    startup_error: str


class DiagnosticsResponse(TypedDict):
    """Response from ``GET /api/diagnostics``."""

    project_path: str
    current_working_directory: str
    git_branch: str | None
    in_worktree: bool
    worktrees_exist: bool
    active_mission: str | None
    file_integrity: FileIntegrity
    worktree_overview: dict[str, Any]
    current_feature: CurrentFeatureDetected | CurrentFeatureNotDetected
    all_features: list[DiagnosticsFeatureStatus]
    dashboard_health: DashboardHealthInfo
    observations: list[str]
    issues: list[str]


class DiagnosticsErrorResponse(TypedDict):
    """Error variant of the diagnostics response (HTTP 500)."""

    error: str
    traceback: str
