"""Focused tests for daemon-aware sync status rendering."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console

from specify_cli.cli.commands import sync as sync_module
from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.sync.queue import QueueStats

pytestmark = pytest.mark.fast


def test_status_reads_dashboard_daemon_state_without_booting_local_runtime(monkeypatch, tmp_path: Path):
    """sync status should report daemon health without starting disposable services."""
    output = io.StringIO()
    monkeypatch.setattr(sync_module, "console", Console(file=output, force_terminal=False, width=120))

    fake_queue = type(
        "FakeQueue",
        (),
        {
            "size": lambda self: 3,
            "get_queue_stats": lambda self: QueueStats(total_queued=3, max_queue_size=100_000),
        },
    )()

    class FakeConfig:
        config_file = tmp_path / "config.toml"

        def get_server_url(self) -> str:
            return "https://spec-kitty-dev.fly.dev"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("status() should not start local background sync services")

    monkeypatch.setattr("specify_cli.sync.queue.OfflineQueue", lambda: fake_queue)
    monkeypatch.setattr("specify_cli.sync.config.SyncConfig", FakeConfig)
    # Mission 080: the legacy ``specify_cli.sync.auth.AuthClient`` no longer
    # exists. ``sync status`` now reads auth state via
    # ``specify_cli.auth.get_token_manager``; this test exercises the code
    # path where the status panel does not even consult the token manager
    # (no local runtime is booted).
    monkeypatch.setattr(
        "specify_cli.sync.daemon.get_sync_daemon_status",
        lambda: SyncDaemonStatus(
            healthy=True,
            url="http://127.0.0.1:9400",
            port=9400,
            sync_running=True,
            last_sync="2026-04-04T12:00:00+00:00",
            consecutive_failures=2,
            websocket_status="Connected",
        ),
    )
    monkeypatch.setattr("specify_cli.sync.background.get_sync_service", fail_if_called)
    monkeypatch.setattr("specify_cli.sync.events.get_emitter", fail_if_called)

    sync_module.status()

    rendered = output.getvalue()
    assert "Daemon" in rendered
    assert "Running" in rendered
    assert "Global daemon" in rendered
    assert "Connected" in rendered
    assert "2026-04-04 12:00:00 UTC" in rendered
    assert "Background" not in rendered
