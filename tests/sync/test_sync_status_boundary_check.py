"""Tests for ``sync status --check`` boundary coherence gate (WP03 / FR-009).

The gate must exit 0 when the identity boundary is coherent and non-zero
when ANY of the three FR-009 conditions hold:

* foreground/daemon disagree on any D-3 field;
* legacy DB has ≥1 row in any migration table for the active scope;
* ≥1 orphan daemon owner record on disk.

Tests use a per-test ``HOME`` so that ``~/.spec-kitty`` and the daemon
owner directory live under ``tmp_path``.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

pytestmark = pytest.mark.fast


runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin HOME / LOCALAPPDATA to ``tmp_path`` so all global state is scoped."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    # Operate from a tmp cwd so the FR-013 workspace detector returns None
    # by default; tests that need a mission slug override cwd locally.
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _isolate_external_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out external network / heavy probes used inside ``sync status``."""
    # Avoid every test having to mock _check_server_connection.
    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._check_server_connection",
        lambda url: ("[green]Connected[/green]", "Server reachable."),
    )
    # The teamspace recovery path consults a token manager + network; keep
    # ``auth_recovery_pending`` False for all tests in this file.
    from unittest.mock import MagicMock

    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = None

    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: tm,
    )
    # Daemon-process scanner spawns subprocesses to enumerate live
    # ``run_sync_daemon`` PIDs; force it to an empty report.
    from specify_cli.sync.daemon import DaemonSingletonReport

    monkeypatch.setattr(
        "specify_cli.sync.daemon.scan_sync_daemons",
        lambda: DaemonSingletonReport(
            state_pid=None,
            state_file_present=False,
            orphan_processes=(),
        ),
    )
    # Stub the SyncDaemonStatus probe so it returns a healthy stationary
    # value without consulting the dashboard file.
    from specify_cli.sync.daemon import SyncDaemonStatus

    monkeypatch.setattr(
        "specify_cli.sync.daemon.get_sync_daemon_status",
        lambda: SyncDaemonStatus(
            healthy=True,
            url=None,
            port=None,
            sync_running=False,
            last_sync=None,
            consecutive_failures=0,
            websocket_status="Disconnected",
        ),
    )


def _legacy_db_path() -> Path:
    """Return the canonical legacy queue DB path under the current HOME."""
    from specify_cli.sync.queue import _legacy_queue_db_path

    return _legacy_queue_db_path()


def _build_owner_record(**overrides: Any):
    """Construct a :class:`DaemonOwnerRecord` matching the live foreground.

    By default the record agrees with the foreground on every D-3 field, so
    individual tests only have to override the dimension under test.
    """
    from specify_cli.sync.owner import DaemonOwnerRecord, compute_foreground_identity

    identity = compute_foreground_identity()
    defaults: dict[str, Any] = dict(
        pid=os.getpid(),
        port=9400,
        token="deadbeefcafebabe",
        package_version=str(identity["package_version"]),
        executable_path=str(identity["executable_path"]),
        source_checkout_path=str(identity["source_checkout_path"]),
        server_url=str(identity["server_url"]),
        auth_principal=identity.get("auth_principal"),
        auth_team=identity.get("auth_team"),
        auth_scope=identity.get("auth_scope"),
        queue_db_path=str(identity["queue_db_path"]),
        started_at="2026-05-17T16:42:00+00:00",
    )
    defaults.update(overrides)
    return DaemonOwnerRecord(**defaults)


def _seed_legacy_body_upload(
    *,
    mission_slug: str = "irrelevant",
    project_uuid: str = "11111111-1111-1111-1111-111111111111",
    target_branch: str = "main",
) -> None:
    """Insert one row into the legacy ``body_upload_queue`` table."""
    db_path = _legacy_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        # Mirror the production schema closely enough for the row to
        # satisfy the NOT NULL + UNIQUE constraints used by callers.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS body_upload_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_uuid TEXT NOT NULL,
                mission_slug TEXT NOT NULL,
                target_branch TEXT NOT NULL,
                mission_type TEXT NOT NULL,
                manifest_version TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
                content_body TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0.0,
                created_at REAL NOT NULL,
                last_error TEXT,
                UNIQUE(project_uuid, mission_slug, target_branch, mission_type,
                       manifest_version, artifact_path, content_hash)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO body_upload_queue
                (project_uuid, mission_slug, target_branch, mission_type,
                 manifest_version, artifact_path, content_hash, hash_algorithm,
                 content_body, size_bytes, retry_count, next_attempt_at,
                 created_at, last_error)
            VALUES (?, ?, ?, 'software-dev', '1', 'plan.md',
                    'abc', 'sha256', 'payload', 7, 0, 0.0, 1.0, NULL)
            """,
            (project_uuid, mission_slug, target_branch),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Scenario 1: healthy → exit 0
# ---------------------------------------------------------------------------


def test_check_exits_zero_when_boundary_is_coherent() -> None:
    """No daemon record, empty legacy DB, no orphans → exit 0."""
    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code == 0, result.stdout
    assert "Identity boundary check FAILED" not in result.stdout


# ---------------------------------------------------------------------------
# Scenario 2: stale daemon version → exit non-zero, names ``package_version``
# ---------------------------------------------------------------------------


def test_check_fails_when_daemon_version_disagrees() -> None:
    """A daemon record with a stale package_version trips the D-3 gate."""
    from specify_cli.sync.owner import write_owner_record

    record = _build_owner_record(package_version="0.0.0-stale")
    write_owner_record(record)

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    assert "package_version" in flat
    assert "Identity boundary check FAILED" in flat


# ---------------------------------------------------------------------------
# Scenario 3: legacy body-upload backlog → exit non-zero, FR-013 tag present
# ---------------------------------------------------------------------------


def test_check_fails_when_legacy_body_upload_backlog_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy DB with a body-upload row → exit non-zero and surface the path.

    When the row carries a mission slug that matches the active mission
    context (derived from cwd), the FR-013 stranded-tag must appear in
    the rendered output.
    """
    # Establish a mission slug derivable from cwd via _detect_workspace_context.
    mission_slug = "012-my-mission"
    worktree_dir = tmp_path / "repo" / ".worktrees" / f"{mission_slug}-lane-a"
    worktree_dir.mkdir(parents=True)
    monkeypatch.chdir(worktree_dir)

    _seed_legacy_body_upload(mission_slug=mission_slug)

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout

    # Rich wraps long lines on the terminal width chosen by the runner;
    # collapse newlines + extra spaces before substring checks so the
    # contract is "these tokens appear in the rendered output in order"
    # rather than "these tokens land on the same source line".
    flat = " ".join(result.stdout.split())
    # Strip-all-whitespace view tolerates wraps that insert a space mid-token
    # (e.g. Rich wrapping `queue.db` as `queue` + newline + `.db` produces
    # `queue .db` after the split-join above). The CI runner uses a narrower
    # terminal than dev workstations and triggers this case.
    flat_nows = flat.replace(" ", "")
    assert "Identity boundary check FAILED" in flat
    assert "queue.db" in flat_nows
    assert "body_upload_queue" in flat_nows
    # FR-013 tag for the active mission.
    assert f"setup-plan stranded mission slug {mission_slug}" in flat
    # And the legacy DB filename should land verbatim.
    assert _legacy_db_path().name in flat_nows


# ---------------------------------------------------------------------------
# Scenario 4: orphan daemon → exit non-zero, names orphan count
# ---------------------------------------------------------------------------


def test_check_fails_when_orphan_daemon_record_exists() -> None:
    """A daemon record whose PID is dead → orphan → exit non-zero."""
    from specify_cli.sync.owner import write_owner_record

    # Use a PID that is extremely unlikely to be alive. PID 0 is reserved
    # on POSIX (returns False from kill(0) → ESRCH), and the
    # owner.executable_path defaults to ``sys.executable`` which exists,
    # so the orphan trigger is the dead PID alone.
    dead_pid = 999_999
    record = _build_owner_record(pid=dead_pid)
    write_owner_record(record)

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    assert "orphan daemon record" in flat
    # Avoid an off-by-one assertion: the exact count is in the rendered line.
    assert "1 orphan" in flat


def test_check_fails_when_live_orphan_daemon_process_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live unregistered ``run_sync_daemon`` process trips --check."""
    from specify_cli.sync.daemon import DaemonSingletonReport, OrphanDaemonInfo

    monkeypatch.setattr(
        "specify_cli.sync.daemon.scan_sync_daemons",
        lambda: DaemonSingletonReport(
            state_pid=None,
            state_file_present=False,
            orphan_processes=(
                OrphanDaemonInfo(
                    pid=424242,
                    cmdline=(sys.executable, "-c", "run_sync_daemon(9401)"),
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    assert "live orphan run_sync_daemon" in flat
    assert "Identity boundary check FAILED" in flat


# ---------------------------------------------------------------------------
# Regression: sync status (no --check) stays exit 0 even when the boundary
# would trip --check. This protects the read-only surface contract.
# ---------------------------------------------------------------------------


def test_status_without_check_is_read_only_even_when_incoherent() -> None:
    """``sync status`` (no flag) must not enforce the FR-009 gate."""
    from specify_cli.sync.owner import write_owner_record

    record = _build_owner_record(package_version="0.0.0-stale")
    write_owner_record(record)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.stdout
    assert "Identity boundary check FAILED" not in result.stdout
