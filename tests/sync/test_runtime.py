"""Tests for SyncRuntime lazy singleton lifecycle."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.runtime import (
    SyncRuntime,
    get_runtime,
    reset_runtime,
    _auto_start_enabled,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset runtime singleton before and after each test."""
    reset_runtime()
    yield
    reset_runtime()


class TestAutoStartEnabled:
    """Tests for _auto_start_enabled() config reading."""

    def test_returns_true_when_no_config(self, tmp_path, monkeypatch):
        """Returns True when .kittify/config.yaml doesn't exist."""
        monkeypatch.chdir(tmp_path)
        assert _auto_start_enabled() is True

    def test_returns_true_when_config_has_no_sync_section(self, tmp_path, monkeypatch):
        """Returns True when config exists but has no sync section."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("agents:\n  available: []\n")
        assert _auto_start_enabled() is True

    def test_returns_true_when_auto_start_not_set(self, tmp_path, monkeypatch):
        """Returns True when sync section exists but auto_start not set."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  server_url: https://example.com\n")
        assert _auto_start_enabled() is True

    def test_returns_true_when_auto_start_true(self, tmp_path, monkeypatch):
        """Returns True when auto_start is explicitly True."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: true\n")
        assert _auto_start_enabled() is True

    def test_returns_false_when_auto_start_false(self, tmp_path, monkeypatch):
        """Returns False when auto_start is explicitly False."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: false\n")
        assert _auto_start_enabled() is False

    def test_returns_true_on_invalid_yaml(self, tmp_path, monkeypatch):
        """Returns True when config file is invalid YAML."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("invalid: yaml: content: [")
        assert _auto_start_enabled() is True


class TestSyncRuntime:
    """Tests for SyncRuntime dataclass behavior."""

    def test_initial_state(self):
        """Runtime starts with all fields at default values."""
        runtime = SyncRuntime()
        assert runtime.background_service is None
        assert runtime.ws_client is None
        assert runtime.emitter is None
        assert runtime.started is False

    def test_start_is_idempotent(self, tmp_path, monkeypatch):
        """Multiple start() calls are safe."""
        monkeypatch.chdir(tmp_path)
        # Disable auto-start to avoid side effects
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: false\n")

        runtime = SyncRuntime()
        runtime.start()
        runtime.start()  # Should not raise
        runtime.start()  # Should not raise
        assert runtime.started is False  # Because auto_start is disabled

    def test_auto_start_disabled_prevents_start(self, tmp_path, monkeypatch):
        """When sync.auto_start: false, runtime doesn't start services."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: false\n")

        runtime = SyncRuntime()
        runtime.start()

        assert runtime.started is False
        assert runtime.background_service is None
        assert runtime.ws_client is None

    def test_starts_background_service(self, tmp_path, monkeypatch):
        """start() initializes BackgroundSyncService."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        # Mock auth to return unauthenticated (skip WebSocket)
        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                mock_auth = MagicMock()
                mock_auth.is_authenticated.return_value = False
                mock_auth_class.return_value = mock_auth

                runtime = SyncRuntime()
                runtime.start()

                assert runtime.started is True
                assert runtime.background_service is mock_service
                mock_get_service.assert_called_once()

    def test_attach_emitter_wires_ws_client(self):
        """attach_emitter wires existing ws_client to emitter."""
        runtime = SyncRuntime()
        mock_ws = MagicMock()
        runtime.ws_client = mock_ws

        mock_emitter = MagicMock()
        runtime.attach_emitter(mock_emitter)

        assert runtime.emitter is mock_emitter
        assert mock_emitter.ws_client is mock_ws

    def test_attach_emitter_without_ws_client(self):
        """attach_emitter stores emitter even without ws_client."""
        runtime = SyncRuntime()
        mock_emitter = MagicMock()
        runtime.attach_emitter(mock_emitter)

        assert runtime.emitter is mock_emitter
        # ws_client not set since it was None

    def test_stop_is_safe_when_not_started(self):
        """stop() is safe to call when not started."""
        runtime = SyncRuntime()
        runtime.stop()  # Should not raise
        assert runtime.started is False

    def test_stop_cleans_up_services(self, tmp_path, monkeypatch):
        """stop() cleans up background service and ws_client."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        # Mock auth to return unauthenticated (skip WebSocket)
        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                mock_auth = MagicMock()
                mock_auth.is_authenticated.return_value = False
                mock_auth_class.return_value = mock_auth

                runtime = SyncRuntime()
                runtime.start()
                assert runtime.started is True

                runtime.stop()

                assert runtime.started is False
                assert runtime.background_service is None
                mock_service.stop.assert_called_once()


class TestGetRuntime:
    """Tests for get_runtime() singleton accessor."""

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_returns_singleton(self, mock_start):
        """get_runtime returns same instance on repeated calls."""
        r1 = get_runtime()
        r2 = get_runtime()
        r3 = get_runtime()

        assert r1 is r2
        assert r2 is r3
        # start() only called once
        assert mock_start.call_count == 1

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_auto_starts_on_first_access(self, mock_start):
        """get_runtime calls start() on first access."""
        runtime = get_runtime()
        mock_start.assert_called_once()


class TestResetRuntime:
    """Tests for reset_runtime() test helper."""

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_stops_existing_runtime(self, mock_start):
        """reset_runtime stops existing runtime before clearing."""
        runtime = get_runtime()
        with patch.object(runtime, "stop") as mock_stop:
            reset_runtime()
            mock_stop.assert_called_once()

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_creates_new_instance_after_reset(self, mock_start):
        """After reset, get_runtime returns a new instance."""
        r1 = get_runtime()
        reset_runtime()
        r2 = get_runtime()

        assert r1 is not r2


class TestUnauthenticatedBehavior:
    """Tests for behavior when user is not authenticated."""

    def test_no_websocket_when_unauthenticated(self, tmp_path, monkeypatch):
        """WebSocket is not created when not authenticated."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                mock_auth = MagicMock()
                mock_auth.is_authenticated.return_value = False
                mock_auth_class.return_value = mock_auth

                runtime = SyncRuntime()
                runtime.start()

                assert runtime.ws_client is None
                assert runtime.background_service is not None  # Queue still works

    def test_websocket_created_when_authenticated(self, tmp_path, monkeypatch):
        """WebSocket client is created when authenticated."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()
        mock_ws = MagicMock()

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.client.WebSocketClient") as mock_ws_class:
                mock_ws_class.return_value = mock_ws

                with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                    mock_auth = MagicMock()
                    mock_auth.is_authenticated.return_value = True
                    mock_auth_class.return_value = mock_auth

                    with patch("specify_cli.sync.config.SyncConfig") as mock_config_class:
                        mock_config = MagicMock()
                        mock_config.get_server_url.return_value = "https://example.com"
                        mock_config_class.return_value = mock_config

                        # Synchronous context: no running loop, no auto-connect.
                        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
                            with patch("asyncio.ensure_future") as mock_ensure_future:
                                runtime = SyncRuntime()
                                runtime.start()

                                mock_ws_class.assert_called_once()
                                assert runtime.ws_client is mock_ws
                                mock_ensure_future.assert_not_called()

    def test_websocket_connect_scheduled_with_running_loop(
        self, tmp_path, monkeypatch
    ):
        """When an event loop is running, runtime schedules async connect."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()
        mock_ws = MagicMock()
        mock_connect_coro = MagicMock()
        mock_ws.connect.return_value = mock_connect_coro

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.client.WebSocketClient") as mock_ws_class:
                mock_ws_class.return_value = mock_ws
                with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                    mock_auth = MagicMock()
                    mock_auth.is_authenticated.return_value = True
                    mock_auth_class.return_value = mock_auth
                    with patch("specify_cli.sync.config.SyncConfig") as mock_config_class:
                        mock_config = MagicMock()
                        mock_config.get_server_url.return_value = "https://example.com"
                        mock_config_class.return_value = mock_config

                        with patch("asyncio.get_running_loop", return_value=MagicMock()):
                            with patch("asyncio.ensure_future") as mock_ensure_future:
                                runtime = SyncRuntime()
                                runtime.start()

                                mock_ws_class.assert_called_once()
                                mock_ensure_future.assert_called_once_with(mock_connect_coro)
