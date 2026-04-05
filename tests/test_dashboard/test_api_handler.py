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
