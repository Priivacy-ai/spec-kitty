"""Seam delegation tests: CLI adapter → service layer.

Each test verifies that the handler method:
  1. Delegates to the expected service object
  2. Calls the expected service method with correct args
  3. Returns the service response as JSON

Following DIRECTIVE_036: tests exercise the adapter through its HTTP
interface; external I/O is stubbed at the service layer boundary.

The service classes are patched at their source module path (e.g.,
``dashboard.services.mission_scan.MissionScanService``) because the
handler methods use lazy function-body imports, not module-level bindings.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.fast


@pytest.fixture
def mock_feature_handler(tmp_path: Path):
    """Handler stub wired for FeatureHandler seam tests."""
    from specify_cli.dashboard.handlers.features import FeatureHandler

    handler = MagicMock(spec=FeatureHandler)
    handler.project_dir = str(tmp_path)
    handler.project_token = None
    handler.path = "/api/features"
    # Capture _send_json calls so tests can inspect the written payload
    sent: list[tuple[int, dict]] = []
    handler._send_json.side_effect = lambda status, data: sent.append((status, data))
    handler._sent = sent
    return handler


@pytest.fixture
def mock_api_handler(tmp_path: Path):
    """Handler stub wired for APIHandler seam tests."""
    from specify_cli.dashboard.handlers.api import APIHandler

    handler = MagicMock(spec=APIHandler)
    handler.project_dir = str(tmp_path)
    handler.project_token = None
    handler.path = "/api/health"

    buf = io.BytesIO()
    handler.wfile = buf

    sent: list[tuple[int, dict]] = []
    handler._send_json.side_effect = lambda status, data: sent.append((status, data))
    handler._sent = sent
    return handler


# ---------------------------------------------------------------------------
# MissionScanService seams
# ---------------------------------------------------------------------------


class TestMissionScanServiceSeams:
    """Verify FeatureHandler delegates to MissionScanService."""

    def test_features_list_delegates_to_mission_scan_service(
        self, mock_feature_handler, tmp_path: Path
    ) -> None:
        """handle_features_list must delegate to MissionScanService.get_features_list."""
        expected = {
            "features": [],
            "active_feature_id": None,
            "project_path": str(tmp_path),
            "worktrees_root": None,
            "active_worktree": None,
            "active_mission": {
                "name": "No active feature",
                "domain": "unknown",
                "version": "",
                "slug": "",
                "description": "",
                "path": "",
            },
        }

        with patch("dashboard.services.mission_scan.MissionScanService") as MockService:
            MockService.return_value.get_features_list.return_value = expected
            from specify_cli.dashboard.handlers.features import FeatureHandler

            FeatureHandler.handle_features_list(mock_feature_handler)

        MockService.assert_called_once()
        MockService.return_value.get_features_list.assert_called_once()
        status, payload = mock_feature_handler._sent[0]
        assert status == 200
        assert payload["features"] == []

    def test_kanban_delegates_to_mission_scan_service(
        self, mock_feature_handler, tmp_path: Path
    ) -> None:
        """handle_kanban must delegate to MissionScanService.get_kanban."""
        expected = {
            "lanes": {},
            "is_legacy": False,
            "upgrade_needed": False,
            "weighted_percentage": None,
        }

        with patch("dashboard.services.mission_scan.MissionScanService") as MockService:
            MockService.return_value.get_kanban.return_value = expected
            from specify_cli.dashboard.handlers.features import FeatureHandler

            FeatureHandler.handle_kanban(
                mock_feature_handler, "/api/kanban/my-feature-01KQMCA6"
            )

        MockService.return_value.get_kanban.assert_called_once_with("my-feature-01KQMCA6")
        status, payload = mock_feature_handler._sent[0]
        assert status == 200
        assert payload["is_legacy"] is False

    def test_kanban_returns_404_on_short_path(self, mock_feature_handler) -> None:
        """handle_kanban must reject paths missing the feature segment without invoking the service."""
        mock_feature_handler.send_response = MagicMock()
        mock_feature_handler.end_headers = MagicMock()

        with patch("dashboard.services.mission_scan.MissionScanService") as MockService:
            from specify_cli.dashboard.handlers.features import FeatureHandler

            FeatureHandler.handle_kanban(mock_feature_handler, "/api/kanban")

        MockService.return_value.get_kanban.assert_not_called()
        mock_feature_handler.send_response.assert_called_once_with(404)

    def test_features_list_returns_500_on_error(self, mock_feature_handler) -> None:
        """handle_features_list must return 500 JSON if MissionScanService raises."""
        with patch("dashboard.services.mission_scan.MissionScanService") as MockService:
            MockService.return_value.get_features_list.side_effect = RuntimeError("scan_boom")
            from specify_cli.dashboard.handlers.features import FeatureHandler

            FeatureHandler.handle_features_list(mock_feature_handler)

        status, payload = mock_feature_handler._sent[0]
        assert status == 500
        assert payload["error"] == "failed_to_scan_features"
        assert "scan_boom" in payload["detail"]


# ---------------------------------------------------------------------------
# ProjectStateService seams
# ---------------------------------------------------------------------------


class TestProjectStateServiceSeams:
    """Verify APIHandler delegates to ProjectStateService."""

    def test_health_delegates_to_project_state_service(self, mock_api_handler) -> None:
        """handle_health must delegate to ProjectStateService.get_health."""
        expected = {
            "status": "ok",
            "project_path": "/tmp/project",
            "sync": {"running": False, "last_sync": None, "consecutive_failures": 0},
            "websocket_status": "Offline",
        }

        with patch("dashboard.services.project_state.ProjectStateService") as MockService:
            MockService.return_value.get_health.return_value = expected
            from specify_cli.dashboard.handlers.api import APIHandler

            APIHandler.handle_health(mock_api_handler)

        MockService.assert_called_once()
        MockService.return_value.get_health.assert_called_once()
        mock_api_handler.wfile.seek(0)
        payload = json.loads(mock_api_handler.wfile.read().decode("utf-8"))
        assert payload["status"] == "ok"

    def test_health_passes_token_to_service(self, mock_api_handler) -> None:
        """handle_health must forward project_token to ProjectStateService.get_health."""
        mock_api_handler.project_token = "my-secret-token"

        with patch("dashboard.services.project_state.ProjectStateService") as MockService:
            MockService.return_value.get_health.return_value = {
                "status": "ok",
                "project_path": "/tmp/project",
            }
            from specify_cli.dashboard.handlers.api import APIHandler

            APIHandler.handle_health(mock_api_handler)

        _, kwargs = MockService.return_value.get_health.call_args
        assert kwargs.get("token") == "my-secret-token"


# ---------------------------------------------------------------------------
# SyncService seams
# ---------------------------------------------------------------------------


class TestSyncServiceSeams:
    """Verify APIHandler delegates to SyncService."""

    def test_sync_trigger_delegates_to_sync_service_on_success(
        self, mock_api_handler
    ) -> None:
        """handle_sync_trigger must delegate to SyncService.trigger_sync on success."""
        from dashboard.services.sync import SyncTriggerResult

        result = SyncTriggerResult(status="scheduled", http_status=202)
        mock_api_handler.path = "/api/sync/trigger"

        with patch("dashboard.services.sync.SyncService") as MockService:
            MockService.return_value.trigger_sync.return_value = result
            from specify_cli.dashboard.handlers.api import APIHandler

            APIHandler.handle_sync_trigger(mock_api_handler)

        MockService.return_value.trigger_sync.assert_called_once()
        status, payload = mock_api_handler._sent[0]
        assert status == 202
        assert payload["status"] == "scheduled"

    def test_sync_trigger_returns_403_before_delegating_on_bad_token(
        self, mock_api_handler
    ) -> None:
        """handle_sync_trigger must reject wrong token before calling SyncService."""
        mock_api_handler.project_token = "expected-token"
        mock_api_handler.path = "/api/sync/trigger?token=wrong-token"

        with patch("dashboard.services.sync.SyncService") as MockService:
            from specify_cli.dashboard.handlers.api import APIHandler

            APIHandler.handle_sync_trigger(mock_api_handler)

        MockService.return_value.trigger_sync.assert_not_called()
        status, payload = mock_api_handler._sent[0]
        assert status == 403
        assert payload["error"] == "invalid_token"

    @pytest.mark.parametrize(
        "result_kwargs,expected_status,expected_body",
        [
            (
                {"status": "scheduled", "http_status": 202},
                202,
                {"status": "scheduled"},
            ),
            (
                {
                    "status": "skipped",
                    "http_status": 202,
                    "manual_mode": True,
                    "reason": "policy_manual",
                },
                202,
                {"status": "skipped", "manual_mode": True, "reason": "policy_manual"},
            ),
            (
                {
                    "status": "unavailable",
                    "http_status": 503,
                    "error": "sync_daemon_unavailable",
                    "reason": "start_failed:port busy",
                },
                503,
                {"error": "sync_daemon_unavailable", "reason": "start_failed:port busy"},
            ),
            (
                {
                    "status": "failed",
                    "http_status": 500,
                    "error": "sync_trigger_failed",
                },
                500,
                {"error": "sync_trigger_failed"},
            ),
        ],
        ids=["scheduled", "skipped", "unavailable", "failed"],
    )
    def test_sync_trigger_dispatches_all_result_branches(
        self, mock_api_handler, result_kwargs, expected_status, expected_body
    ) -> None:
        """handle_sync_trigger must turn every SyncTriggerResult into the right HTTP body via result.body()."""
        from dashboard.services.sync import SyncTriggerResult

        mock_api_handler.path = "/api/sync/trigger"
        result = SyncTriggerResult(**result_kwargs)

        with patch("dashboard.services.sync.SyncService") as MockService:
            MockService.return_value.trigger_sync.return_value = result
            from specify_cli.dashboard.handlers.api import APIHandler

            APIHandler.handle_sync_trigger(mock_api_handler)

        status, payload = mock_api_handler._sent[0]
        assert status == expected_status
        assert payload == expected_body


# ---------------------------------------------------------------------------
# Pure helpers (no handler involvement)
# ---------------------------------------------------------------------------


class TestPureHelpers:
    """Cover module-level helpers that the thin adapters depend on."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("/api/kanban/my-feature-01KQMCA6", "my-feature-01KQMCA6"),
            ("/api/kanban/another-mission/extra-segment", "another-mission"),
            ("/api/kanban", None),
            ("/api", None),
            ("", None),
        ],
    )
    def test_parse_kanban_path(self, path: str, expected: str | None) -> None:
        from dashboard.services.mission_scan import parse_kanban_path

        assert parse_kanban_path(path) == expected

    def test_sync_trigger_result_body_scheduled(self) -> None:
        from dashboard.services.sync import SyncTriggerResult

        assert SyncTriggerResult(status="scheduled", http_status=202).body() == {
            "status": "scheduled",
        }

    def test_sync_trigger_result_body_skipped(self) -> None:
        from dashboard.services.sync import SyncTriggerResult

        result = SyncTriggerResult(
            status="skipped",
            http_status=202,
            manual_mode=True,
            reason="policy_manual",
        )
        assert result.body() == {
            "status": "skipped",
            "manual_mode": True,
            "reason": "policy_manual",
        }

    def test_sync_trigger_result_body_unavailable_with_reason(self) -> None:
        from dashboard.services.sync import SyncTriggerResult

        result = SyncTriggerResult(
            status="unavailable",
            http_status=503,
            error="sync_daemon_unavailable",
            reason="rollout_disabled",
        )
        assert result.body() == {
            "error": "sync_daemon_unavailable",
            "reason": "rollout_disabled",
        }

    def test_sync_trigger_result_body_unavailable_without_reason(self) -> None:
        from dashboard.services.sync import SyncTriggerResult

        result = SyncTriggerResult(
            status="unavailable",
            http_status=503,
            error="sync_daemon_unavailable",
        )
        assert result.body() == {"error": "sync_daemon_unavailable"}

    def test_sync_trigger_result_body_failed(self) -> None:
        from dashboard.services.sync import SyncTriggerResult

        result = SyncTriggerResult(
            status="failed",
            http_status=500,
            error="sync_trigger_failed",
        )
        assert result.body() == {"error": "sync_trigger_failed"}
