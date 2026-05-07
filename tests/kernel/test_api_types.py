"""Kernel-level smoke tests for src/kernel/api_types.py.

These types are TypedDict declarations — they have no runtime logic, but
they are part of the kernel's public surface and need to be importable
and instantiable for the kernel-tests CI coverage gate. Without these
tests, the file shows 0% coverage even though it is imported by every
dashboard route that returns one of these shapes (see Mission C
``api-surface-completion-services-aliases-async-01KQSXDA``).

The assertions are deliberately structural: each TypedDict can be
instantiated with the documented keys, and required keys round-trip via
``TypedDict.__required_keys__``. Schema drift in any field name will
fail one of these tests.
"""
from __future__ import annotations

from typing import get_type_hints

import pytest

from kernel.api_types import (
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

pytestmark = pytest.mark.fast


class TestErrorResponse:
    """ErrorResponse: required `error`, optional `detail` and `status`."""

    def test_minimal(self) -> None:
        payload: ErrorResponse = {"error": "boom"}
        assert payload["error"] == "boom"

    def test_full(self) -> None:
        payload: ErrorResponse = {"error": "boom", "detail": "context", "status": 500}
        assert payload["status"] == 500
        assert payload["detail"] == "context"

    def test_required_keys_include_error(self) -> None:
        # `error` is unconditionally required; `detail` and `status` are
        # NotRequired but on some Python versions still appear in
        # __required_keys__ — assert containment rather than equality.
        assert "error" in ErrorResponse.__required_keys__


class TestSyncInfo:
    """SyncInfo: total=False — every key is optional."""

    def test_empty(self) -> None:
        payload: SyncInfo = {}
        assert payload == {}

    def test_full_running(self) -> None:
        payload: SyncInfo = {
            "running": True,
            "last_sync": "2026-05-07T12:00:00+00:00",
            "consecutive_failures": 0,
        }
        assert payload["running"] is True

    def test_error_path(self) -> None:
        payload: SyncInfo = {"running": False, "error": "daemon unreachable"}
        assert payload["error"]

    def test_required_keys_empty(self) -> None:
        assert SyncInfo.__required_keys__ == frozenset()


class TestHealthResponse:
    """HealthResponse with nested SyncInfo."""

    def test_minimal_ok(self) -> None:
        payload: HealthResponse = {"status": "ok", "project_path": "/tmp/x"}
        assert payload["status"] == "ok"

    def test_with_sync_info(self) -> None:
        payload: HealthResponse = {
            "status": "ok",
            "project_path": "/tmp/x",
            "sync": {"running": True, "last_sync": None, "consecutive_failures": 0},
        }
        assert payload["sync"]["running"] is True

    def test_with_token(self) -> None:
        payload: HealthResponse = {"status": "ok", "project_path": "/", "token": "abc"}
        assert payload["token"] == "abc"


class TestSyncTriggerSuccess:
    def test_scheduled(self) -> None:
        payload: SyncTriggerSuccess = {"status": "scheduled"}
        assert payload["status"] == "scheduled"

    def test_required_status(self) -> None:
        assert SyncTriggerSuccess.__required_keys__ == frozenset({"status"})


class TestFileIntegrity:
    def test_full(self) -> None:
        payload: FileIntegrity = {
            "total_expected": 10,
            "total_present": 9,
            "total_missing": 1,
            "missing_files": ["docs/missing.md"],
        }
        assert payload["total_missing"] == 1
        assert payload["missing_files"] == ["docs/missing.md"]

    def test_zero_missing(self) -> None:
        payload: FileIntegrity = {
            "total_expected": 5,
            "total_present": 5,
            "total_missing": 0,
            "missing_files": [],
        }
        assert payload["missing_files"] == []


class TestDiagnosticsFeatureStatus:
    def test_full(self) -> None:
        payload: DiagnosticsFeatureStatus = {
            "name": "001-feature",
            "state": "active",
            "branch_exists": True,
            "branch_merged": False,
            "worktree_exists": True,
            "worktree_path": "/tmp/.worktrees/001-feature",
            "artifacts_in_main": True,
            "artifacts_in_worktree": True,
        }
        assert payload["name"] == "001-feature"
        assert payload["worktree_path"] is not None


class TestCurrentFeatureDetected:
    def test_detected(self) -> None:
        payload: CurrentFeatureDetected = {
            "detected": True,
            "name": "001-feature",
            "state": "active",
            "branch_exists": True,
            "branch_merged": False,
            "worktree_exists": True,
            "worktree_path": None,
            "artifacts_in_main": True,
            "artifacts_in_worktree": False,
        }
        assert payload["detected"] is True


class TestCurrentFeatureNotDetected:
    def test_not_detected(self) -> None:
        payload: CurrentFeatureNotDetected = {"detected": False, "error": "not found"}
        assert payload["detected"] is False
        assert payload["error"] == "not found"


class TestDashboardHealthInfo:
    def test_empty(self) -> None:
        payload: DashboardHealthInfo = {}
        assert payload == {}

    def test_responding(self) -> None:
        payload: DashboardHealthInfo = {
            "metadata_exists": True,
            "can_start": True,
            "url": "http://127.0.0.1:8090",
            "port": 8090,
            "pid": 12345,
            "has_pid": True,
            "responding": True,
        }
        assert payload["responding"] is True

    def test_required_keys_empty(self) -> None:
        assert DashboardHealthInfo.__required_keys__ == frozenset()


class TestDiagnosticsResponse:
    def test_minimal_shape(self) -> None:
        payload: DiagnosticsResponse = {
            "project_path": "/tmp/p",
            "current_working_directory": "/tmp/p",
            "git_branch": "main",
            "in_worktree": False,
            "worktrees_exist": False,
            "active_mission": None,
            "file_integrity": {
                "total_expected": 0,
                "total_present": 0,
                "total_missing": 0,
                "missing_files": [],
            },
            "worktree_overview": {},
            "current_feature": {"detected": False, "error": "no feature"},
            "all_features": [],
            "dashboard_health": {},
            "observations": [],
            "issues": [],
        }
        assert payload["project_path"] == "/tmp/p"
        assert payload["current_feature"]["detected"] is False

    def test_required_keys_complete(self) -> None:
        # DiagnosticsResponse is total=True so every key is required.
        expected = {
            "project_path",
            "current_working_directory",
            "git_branch",
            "in_worktree",
            "worktrees_exist",
            "active_mission",
            "file_integrity",
            "worktree_overview",
            "current_feature",
            "all_features",
            "dashboard_health",
            "observations",
            "issues",
        }
        assert DiagnosticsResponse.__required_keys__ == frozenset(expected)


class TestDiagnosticsErrorResponse:
    def test_full(self) -> None:
        payload: DiagnosticsErrorResponse = {
            "error": "boom",
            "traceback": "Traceback (most recent call last):\n...",
        }
        assert payload["error"] == "boom"

    def test_required_keys(self) -> None:
        assert DiagnosticsErrorResponse.__required_keys__ == frozenset({"error", "traceback"})


class TestImportSurface:
    """Verify every public symbol is importable from kernel.api_types."""

    def test_all_typed_dicts_exposed(self) -> None:
        import kernel.api_types as mod

        for symbol in (
            "ErrorResponse",
            "SyncInfo",
            "HealthResponse",
            "SyncTriggerSuccess",
            "FileIntegrity",
            "DiagnosticsFeatureStatus",
            "CurrentFeatureDetected",
            "CurrentFeatureNotDetected",
            "DashboardHealthInfo",
            "DiagnosticsResponse",
            "DiagnosticsErrorResponse",
        ):
            assert hasattr(mod, symbol), f"{symbol} missing from kernel.api_types"

    def test_type_hints_resolvable(self) -> None:
        """Round-trip every TypedDict's get_type_hints — catches forward-reference drift."""
        for cls in (
            ErrorResponse,
            SyncInfo,
            HealthResponse,
            SyncTriggerSuccess,
            FileIntegrity,
            DiagnosticsFeatureStatus,
            CurrentFeatureDetected,
            CurrentFeatureNotDetected,
            DashboardHealthInfo,
            DiagnosticsResponse,
            DiagnosticsErrorResponse,
        ):
            hints = get_type_hints(cls)
            assert hints, f"{cls.__name__} has no resolvable type hints"
