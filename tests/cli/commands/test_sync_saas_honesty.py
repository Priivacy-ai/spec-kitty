"""SaaS-sync success-reporting honesty (#2264).

First-time SaaS sync could report success at every local touchpoint while the
remote project was an empty shell. Two honest-reporting fixes are covered here:

* ``sync opt-in`` states only that a LOCAL preference was recorded — it must not
  imply remote materialization or history import (the "Enabled SaaS sync"
  false-green that escalated #2264 to P1).
* ``sync status --check --json`` carries typed ``remote_sync`` fields for
  remote-project + historical-import state, so consumers read those rather than
  inferring remote population from ``ok`` (which stays boundary-coherence only).
  The honest-``unknown`` slice ships now; populated values follow #2262.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app
from specify_cli.core.saas_sync_config import saas_sync_opt_in_recorded_message
from specify_cli.sync.daemon import DaemonSingletonReport, SyncDaemonStatus
from unittest.mock import patch

pytestmark = pytest.mark.fast

runner = CliRunner()

_REMOTE_IMPLYING = ("enabled saas sync", "materialized", "history", "imported", "remote")


def test_opt_in_message_states_only_a_local_preference() -> None:
    msg = saas_sync_opt_in_recorded_message()
    lowered = msg.lower()
    assert "recorded" in lowered, msg
    for banned in _REMOTE_IMPLYING:
        assert banned not in lowered, f"opt-in message implies remote work: {banned!r} in {msg!r}"


def test_opt_in_message_includes_scope_without_overclaiming() -> None:
    msg = saas_sync_opt_in_recorded_message("acme/widgets")
    assert "acme/widgets" in msg
    assert "enabled saas sync" not in msg.lower()


def _healthy_status() -> SyncDaemonStatus:
    return SyncDaemonStatus(
        healthy=True,
        url="http://127.0.0.1:9400",
        port=9400,
        token="t",
        pid=4242,
        sync_running=True,
        last_sync=None,
        consecutive_failures=0,
        websocket_status="Connected",
        protocol_version=1,
        package_version="3.2.0",
    )


def _extract_json(output: str) -> dict[str, Any]:
    """Parse the JSON object from mixed CLI output (rich may prepend lines)."""
    start = output.index("{")
    payload: dict[str, Any] = json.loads(output[start:])
    return payload


def test_status_check_json_carries_honest_unknown_remote_sync(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--check --json exposes typed remote/import fields, honest-``unknown`` for now."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)

    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir(parents=True, exist_ok=True)
    (cred_dir / "credentials").write_text(
        "[user]\n"
        'username = "tester@example.com"\n'
        'team_slug = "t-private"\n'
        "[server]\n"
        'url = "https://spec-kitty-dev.fly.dev"\n',
        encoding="utf-8",
    )

    with (
        patch("specify_cli.sync.daemon.get_sync_daemon_status", return_value=_healthy_status()),
        patch(
            "specify_cli.sync.daemon.scan_sync_daemons",
            return_value=DaemonSingletonReport(state_pid=4242, state_file_present=True, orphan_processes=()),
        ),
        patch.object(sync_command, "_check_server_connection", return_value=("Reachable", None)),
    ):
        result = runner.invoke(app, ["status", "--check", "--json"])

    payload = _extract_json(result.output)
    remote_sync = payload["remote_sync"]
    assert remote_sync["remote_project_state"] == "unknown"
    assert remote_sync["historical_import_state"] == "unknown"
    assert remote_sync["materialized_at"] is None
    assert remote_sync["last_blocker_sample"] is None
    # Regression guard: ``ok`` remains boundary-coherence, independent of remote_sync.
    assert "ok" in payload
