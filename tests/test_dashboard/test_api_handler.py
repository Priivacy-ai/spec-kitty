"""Tests for dashboard API handler — specifically that health is read-only (Fix #9)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.mission import MissionError

pytestmark = pytest.mark.fast


class TestHealthEndpointNoSideEffects:
    """Fix #9: /api/health must NOT call ensure_sync_daemon_running."""

    def test_health_does_not_spawn_daemon(self, tmp_path):
        """handle_health should only observe daemon state, not spawn it."""
        from specify_cli.dashboard.handlers import api as api_module

        spawn_called = {"called": False}

        def boom(*args, **kwargs):
            spawn_called["called"] = True
            raise AssertionError("health endpoint must not call ensure_sync_daemon_running")

        with (
            patch.object(api_module, "ensure_sync_daemon_running", boom),
            patch.object(
                api_module,
                "get_sync_daemon_status",
                return_value=SyncDaemonStatus(healthy=False),
            ),
        ):
            handler = MagicMock()
            handler.project_dir = str(tmp_path)
            handler.project_token = "tok"
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            buf = io.BytesIO()
            handler.wfile = buf

            # Call the real handle_health method
            api_module.APIHandler.handle_health(handler)

        assert not spawn_called["called"]
        # Verify it wrote valid JSON
        buf.seek(0)
        data = json.loads(buf.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["sync"]["running"] is False


class TestFeaturesEndpointErrorHandling:
    """Feature list handler should return JSON errors, not partial responses."""

    def test_features_endpoint_returns_structured_error_on_scan_failure(self, tmp_path):
        from specify_cli.dashboard.handlers import features as features_module

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler._send_json = MagicMock()

        with patch.object(features_module, "scan_all_features", side_effect=RuntimeError("boom")):
            features_module.FeatureHandler.handle_features_list(handler)

        handler._send_json.assert_called_once()
        status_code, payload = handler._send_json.call_args.args
        assert status_code == 500
        assert payload["error"] == "failed_to_scan_features"
        assert "boom" in payload["detail"]

    def test_features_endpoint_returns_full_success_payload(self, tmp_path, monkeypatch):
        from specify_cli.dashboard.handlers import features as features_module

        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        worktree_dir = tmp_path / ".worktrees" / "001-test"
        worktree_dir.mkdir(parents=True)
        monkeypatch.chdir(worktree_dir)

        feature = {
            "id": "001-test",
            "name": "Test Feature",
            "path": "kitty-specs/001-test",
            "meta": {"mission": "software-dev"},
        }
        mission = SimpleNamespace(
            name="Software Dev",
            config=SimpleNamespace(domain="engineering", version="3.1", description="Build software"),
            path=tmp_path / ".kittify" / "missions" / "software-dev",
        )

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler._send_json = MagicMock()

        with (
            patch.object(features_module, "scan_all_features", return_value=[feature.copy()]),
            patch.object(features_module, "resolve_active_feature", return_value=feature),
            patch.object(features_module, "get_mission_by_name", return_value=mission),
            patch.object(features_module, "is_legacy_format", return_value=False),
        ):
            features_module.FeatureHandler.handle_features_list(handler)

        status_code, payload = handler._send_json.call_args.args
        assert status_code == 200
        assert payload["features"][0]["is_legacy"] is False
        assert payload["active_feature_id"] == "001-test"
        assert payload["active_mission"]["name"] == "Software Dev"
        assert payload["active_mission"]["feature"] == "Test Feature"
        assert payload["worktrees_root"] is not None
        assert payload["active_worktree"] is not None

    def test_features_endpoint_uses_unknown_mission_fallback(self, tmp_path, monkeypatch):
        from specify_cli.dashboard.handlers import features as features_module

        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        worktrees_root = tmp_path / ".worktrees"
        worktrees_root.mkdir(parents=True)
        outside_dir = tmp_path / "outside-worktree"
        outside_dir.mkdir()
        monkeypatch.chdir(outside_dir)

        feature = {
            "id": "001-test",
            "name": "Test Feature",
            "path": "kitty-specs/001-test",
            "meta": {"mission": "mystery-mission"},
        }

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler._send_json = MagicMock()

        with (
            patch.object(features_module, "scan_all_features", return_value=[feature.copy()]),
            patch.object(features_module, "resolve_active_feature", return_value=feature),
            patch.object(features_module, "get_mission_by_name", side_effect=MissionError("missing")),
            patch.object(features_module, "is_legacy_format", return_value=True),
        ):
            features_module.FeatureHandler.handle_features_list(handler)

        status_code, payload = handler._send_json.call_args.args
        assert status_code == 200
        assert payload["features"][0]["is_legacy"] is True
        assert payload["active_mission"]["name"] == "Unknown (mystery-mission)"
        assert payload["active_mission"]["feature"] == "Test Feature"
        assert payload["active_worktree"] is not None

    def test_features_endpoint_falls_back_when_path_resolution_breaks(self, tmp_path):
        from specify_cli.dashboard.handlers import features as features_module

        project_path = tmp_path.resolve()
        worktrees_root = project_path / ".worktrees"
        fallback_cwd = project_path / "cwd-fallback"
        fallback_cwd.mkdir()
        path_cls = type(project_path)
        original_resolve = path_cls.resolve

        def flaky_resolve(self, *args, **kwargs):
            if self == worktrees_root or self == fallback_cwd:
                raise RuntimeError("resolution failed")
            return original_resolve(self, *args, **kwargs)

        handler = MagicMock()
        handler.project_dir = str(project_path)
        handler._send_json = MagicMock()

        with (
            patch.object(features_module, "scan_all_features", return_value=[]),
            patch.object(features_module, "resolve_active_feature", return_value=None),
            patch.object(features_module.Path, "cwd", return_value=fallback_cwd),
            patch.object(path_cls, "resolve", flaky_resolve),
        ):
            features_module.FeatureHandler.handle_features_list(handler)

        status_code, payload = handler._send_json.call_args.args
        assert status_code == 200
        assert payload["features"] == []
        assert payload["worktrees_root"] is None
        assert payload["active_worktree"] is not None


class TestDossierEndpointRouting:
    def _make_handler(self, tmp_path, path: str):
        from specify_cli.dashboard.handlers import api as api_module

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler.project_token = "tok"
        handler.path = path
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()
        return api_module, handler

    def test_dossier_endpoint_requires_feature_query_param(self, tmp_path):
        api_module, handler = self._make_handler(tmp_path, "/api/dossier/overview")

        api_module.APIHandler.handle_dossier(handler, handler.path)

        handler.send_response.assert_called_once_with(400)
        handler.wfile.seek(0)
        payload = json.loads(handler.wfile.read().decode("utf-8"))
        assert payload["error"] == "Missing feature parameter"

    def test_dossier_overview_routes_with_mission_slug(self, tmp_path):
        api_module, handler = self._make_handler(
            tmp_path,
            "/api/dossier/overview?feature=064-complete-mission-identity-cutover",
        )
        response = {"overview": "ok"}

        with patch("specify_cli.dossier.api.DossierAPIHandler") as mock_cls:
            mock_cls.return_value.handle_dossier_overview.return_value = response
            api_module.APIHandler.handle_dossier(handler, handler.path)

        mock_cls.return_value.handle_dossier_overview.assert_called_once_with(
            "064-complete-mission-identity-cutover"
        )
        handler.send_response.assert_called_once_with(200)

    def test_dossier_artifacts_routes_with_filters(self, tmp_path):
        api_module, handler = self._make_handler(
            tmp_path,
            "/api/dossier/artifacts?feature=064-complete-mission-identity-cutover&class=decision&required_only=true",
        )
        response = {"artifacts": []}

        with patch("specify_cli.dossier.api.DossierAPIHandler") as mock_cls:
            mock_cls.return_value.handle_dossier_artifacts.return_value = response
            api_module.APIHandler.handle_dossier(handler, handler.path)

        mock_cls.return_value.handle_dossier_artifacts.assert_called_once_with(
            "064-complete-mission-identity-cutover",
            **{"class": "decision", "required_only": "true"},
        )
        handler.send_response.assert_called_once_with(200)

    def test_dossier_detail_and_export_routes_with_mission_slug(self, tmp_path):
        api_module, detail_handler = self._make_handler(
            tmp_path,
            "/api/dossier/artifacts/artifact-123?feature=064-complete-mission-identity-cutover",
        )
        _, export_handler = self._make_handler(
            tmp_path,
            "/api/dossier/snapshots/export?feature=064-complete-mission-identity-cutover",
        )

        with patch("specify_cli.dossier.api.DossierAPIHandler") as mock_cls:
            mock_cls.return_value.handle_dossier_artifact_detail.return_value = {"artifact": "ok"}
            mock_cls.return_value.handle_dossier_snapshot_export.return_value = {"export": "ok"}

            api_module.APIHandler.handle_dossier(detail_handler, detail_handler.path)
            api_module.APIHandler.handle_dossier(export_handler, export_handler.path)

        mock_cls.return_value.handle_dossier_artifact_detail.assert_called_once_with(
            "064-complete-mission-identity-cutover",
            "artifact-123",
        )
        mock_cls.return_value.handle_dossier_snapshot_export.assert_called_once_with(
            "064-complete-mission-identity-cutover"
        )

    def test_dossier_handler_hides_internal_errors(self, tmp_path):
        api_module, handler = self._make_handler(
            tmp_path,
            "/api/dossier/overview?feature=064-complete-mission-identity-cutover",
        )
        handler._send_json = MagicMock()

        with patch("specify_cli.dossier.api.DossierAPIHandler", side_effect=RuntimeError("secret traceback")):
            api_module.APIHandler.handle_dossier(handler, handler.path)

        handler._send_json.assert_called_once_with(500, {"error": "dossier_handler_failed"})


class TestDashboardApiSecurityHardening:
    def test_root_serves_preencoded_dashboard_html(self, tmp_path):
        from specify_cli.dashboard.handlers import api as api_module

        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        with patch.object(api_module, "get_dashboard_html_bytes", return_value=b"<html>ok</html>"):
            api_module.APIHandler.handle_root(handler)

        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_once_with("Content-type", "text/html; charset=utf-8")
        handler.wfile.seek(0)
        assert handler.wfile.read() == b"<html>ok</html>"

    def test_diagnostics_hides_internal_errors(self, tmp_path):
        from specify_cli.dashboard.handlers import api as api_module

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler._send_json = MagicMock()

        with patch.object(api_module, "run_diagnostics", side_effect=RuntimeError("boom")):
            api_module.APIHandler.handle_diagnostics(handler)

        handler._send_json.assert_called_once_with(500, {"error": "diagnostics_failed"})

    def test_charter_hides_internal_errors(self, tmp_path):
        from specify_cli.dashboard.handlers import api as api_module

        handler = MagicMock()
        handler.project_dir = str(tmp_path)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        with patch.object(api_module, "resolve_project_charter_path", side_effect=RuntimeError("secret")):
            api_module.APIHandler.handle_charter(handler)

        handler.send_response.assert_called_once_with(500)
        handler.wfile.seek(0)
        assert handler.wfile.read().decode("utf-8") == "Error loading charter"

    def test_sync_trigger_request_requires_loopback_origin(self):
        from specify_cli.dashboard.handlers.api import _build_sync_trigger_request

        request = _build_sync_trigger_request("http://127.0.0.1:8765/status", "tok")
        assert request.full_url == "http://127.0.0.1:8765/api/sync/trigger"
        assert request.get_method() == "POST"

        with pytest.raises(ValueError, match="http"):
            _build_sync_trigger_request("https://127.0.0.1:8765/status", "tok")

        with pytest.raises(ValueError, match="loopback"):
            _build_sync_trigger_request("http://example.com:8765/status", "tok")

    def test_sync_trigger_uses_validated_loopback_request(self, tmp_path):
        from specify_cli.dashboard.handlers import api as api_module

        handler = MagicMock()
        handler.path = "/api/sync/trigger?token=tok"
        handler.project_token = "tok"
        handler._send_json = MagicMock()

        mock_response = MagicMock()
        mock_response.__enter__.return_value.status = 202
        mock_response.__exit__.return_value = None

        with (
            patch.object(api_module, "ensure_sync_daemon_running"),
            patch.object(
                api_module,
                "get_sync_daemon_status",
                return_value=SyncDaemonStatus(
                    healthy=True,
                    url="http://127.0.0.1:8765/status",
                    token="daemon-token",
                ),
            ),
            patch.object(api_module.urllib.request, "urlopen", return_value=mock_response) as mock_urlopen,
        ):
            api_module.APIHandler.handle_sync_trigger(handler)

        request = mock_urlopen.call_args.args[0]
        assert request.full_url == "http://127.0.0.1:8765/api/sync/trigger"
        handler._send_json.assert_called_once_with(202, {"status": "scheduled"})
