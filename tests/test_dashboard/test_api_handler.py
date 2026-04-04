"""Tests for dashboard API handler — specifically that health is read-only (Fix #9)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.daemon import SyncDaemonStatus

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

        with patch.object(api_module, "ensure_sync_daemon_running", boom):
            with patch.object(
                api_module,
                "get_sync_daemon_status",
                return_value=SyncDaemonStatus(healthy=False),
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
