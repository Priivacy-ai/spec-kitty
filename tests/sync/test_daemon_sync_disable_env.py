"""Regression guard: the sync daemon honors the operator disable env (#2573b).

The ``move-task --to for_review`` path had two synchronous latency sources
(issue #2573): the pre-review regression gate and the sync-daemon spawn
(``ensure_sync_daemon_running``). Ask (a) — a skip flag / disable env for the
pre-review gate — landed earlier. Ask (b), **#2573b**, landed here: the sync
daemon now honors ``SPEC_KITTY_SYNC_DISABLE`` / ``SPEC_KITTY_SYNC_MINIMAL_IMPORT``
in ``_daemon_start_skip_reason``, so an operator who explicitly disables sync no
longer pays the daemon-spawn latency that was the second half of the witnessed
multi-minute "hang". This test locks that contract in.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig
from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running

pytestmark = [pytest.mark.unit]


def _config(policy: BackgroundDaemonPolicy) -> SyncConfig:
    """Build a SyncConfig stub with a fixed background-daemon policy (no disk I/O)."""
    cfg = MagicMock(spec=SyncConfig)
    cfg.get_background_daemon.return_value = policy
    return cfg


class TestSyncDaemonHonorsDisableEnv:
    """``ensure_sync_daemon_running`` must not spawn the daemon when the operator
    sets a sync-disable env (#2573b)."""

    def test_sync_disable_env_skips_daemon_spawn(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """With the SaaS-sync rollout ON, AUTO policy, and a REMOTE_REQUIRED intent,
        an operator who sets ``SPEC_KITTY_SYNC_DISABLE=1`` must NOT have the
        background sync daemon spawned: ``_daemon_start_skip_reason`` honors the
        disable env (#2573b) and returns a skip reason before any spawn, so
        ``_ensure_sync_daemon_running_locked`` is never invoked and the outcome
        reports ``started=False``.
        """
        # Rollout ON (also autouse-set in tests/conftest.py) and REMOTE_REQUIRED +
        # AUTO would normally proceed to spawn — the operator disable must veto that.
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
        monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")

        # Stands in for the real daemon spawn so the test never launches a
        # subprocess; with the #2573b fix in place it must remain uncalled.
        inner = MagicMock(return_value=("http://127.0.0.1:9400", 9400, True))

        with (
            patch("specify_cli.sync.daemon._ensure_sync_daemon_running_locked", inner),
            patch("specify_cli.sync.daemon.DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock"),
            patch("specify_cli.sync.daemon.SPEC_KITTY_DIR", tmp_path),
        ):
            outcome = ensure_sync_daemon_running(
                intent=DaemonIntent.REMOTE_REQUIRED,
                config=_config(BackgroundDaemonPolicy.AUTO),
            )

        assert outcome.started is False, (
            "SPEC_KITTY_SYNC_DISABLE=1 must skip the background sync-daemon spawn "
            f"(#2573b), but the daemon was started: {outcome!r}"
        )
        inner.assert_not_called()
        assert outcome.skipped_reason is not None

    def test_force_explicit_bypasses_disable_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An explicit restart (``force_explicit=True``, e.g. ``doctor
        restart-daemon``) must respawn even when a disable env is set — those
        envs suppress only *implicit* auto-start, not a directly-requested
        restart. Guards the #2573b regression where the explicit restart began
        refusing on ``SPEC_KITTY_SYNC_MINIMAL_IMPORT``.
        """
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
        monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")

        inner = MagicMock(return_value=("http://127.0.0.1:9400", 9400, True))

        with (
            patch("specify_cli.sync.daemon._ensure_sync_daemon_running_locked", inner),
            patch("specify_cli.sync.daemon.DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock"),
            patch("specify_cli.sync.daemon.SPEC_KITTY_DIR", tmp_path),
        ):
            outcome = ensure_sync_daemon_running(
                intent=DaemonIntent.REMOTE_REQUIRED,
                config=_config(BackgroundDaemonPolicy.AUTO),
                force_explicit=True,
            )

        assert outcome.started is True, (
            "force_explicit=True must bypass the disable-env skip and respawn, "
            f"but the daemon was skipped: {outcome!r}"
        )
        inner.assert_called_once()
