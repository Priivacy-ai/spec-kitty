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
    """Pin HOME / LOCALAPPDATA to ``tmp_path`` so all global state is scoped.

    SaaS-sync is left **disabled** by default so the FR-004 auth-required
    refusal does not trip across every existing boundary test. Tests that
    exercise the auth-required contract explicitly set the env var.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
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
    defaults: dict[str, Any] = {
        "pid": os.getpid(),
        "port": 9400,
        "token": "deadbeefcafebabe",
        "package_version": str(identity["package_version"]),
        "executable_path": str(identity["executable_path"]),
        "source_checkout_path": str(identity["source_checkout_path"]),
        "server_url": str(identity["server_url"]),
        "auth_principal": identity.get("auth_principal"),
        "auth_team": identity.get("auth_team"),
        "auth_scope": identity.get("auth_scope"),
        "queue_db_path": str(identity["queue_db_path"]),
        "started_at": "2026-05-17T16:42:00+00:00",
    }
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


# ---------------------------------------------------------------------------
# T016: parametrized per-canonical-field mismatch tests (FR-009)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides, token",
    [
        # Canonical: daemon_package_version
        ({"package_version": "0.0.0-stale"}, "package_version"),
        # Canonical: daemon_executable_path (always mismatches in CI test
        # env anyway due to compute_foreground_identity vs collect_foreground
        # drift; the assertion is that the canonical field name surfaces).
        ({"executable_path": "/no/such/python-binary"}, "executable_path"),
        # Canonical: daemon_source_path
        ({"source_checkout_path": "/no/such/source-checkout"}, "source_path"),
        # Canonical: daemon_server_url
        ({"server_url": "https://other.example.com"}, "server_url"),
        # Canonical: daemon_team_or_user (set both principal+team so the
        # rendered daemon team_or_user differs from foreground None).
        (
            {"auth_principal": "alice@example.com", "auth_team": "team-x"},
            "team_or_user",
        ),
        # Canonical: daemon_queue_db_path
        ({"queue_db_path": "/tmp/some-other-queue.db"}, "queue_db_path"),
    ],
)
def test_check_fails_per_canonical_field(overrides: dict[str, Any], token: str) -> None:
    """Each canonical mismatch field, when mutated, must trip --check.

    Parametrized to lock the FR-009 contract: any one of the six canonical
    fields disagreeing between foreground and daemon yields a non-zero
    exit code with that field's bare name appearing in the rendered
    failure line.
    """
    from specify_cli.sync.owner import write_owner_record

    record = _build_owner_record(**overrides)
    write_owner_record(record)

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    assert "Identity boundary check FAILED" in flat
    # The bare canonical field name (daemon_ prefix stripped per the
    # legacy failure-line format) is one of the listed mismatched fields.
    assert token in flat


# ---------------------------------------------------------------------------
# T016: legacy_rows_for_scope (event + body) failures
# ---------------------------------------------------------------------------


def _seed_legacy_event_row() -> None:
    """Insert one row into the legacy event ``queue`` table.

    Uses the canonical schema written by ``OfflineQueue._init_db`` so the
    subsequent open of ``OfflineQueue()`` in the CLI under test does not
    fail when it tries to (re-)create the table's indexes.
    """
    db_path = _legacy_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0,
                coalesce_key TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO queue (event_id, event_type, data, timestamp, "
            "retry_count, coalesce_key) VALUES "
            "('evt-1', 'TestEvent', '{}', 1, 0, NULL)"
        )
        conn.commit()
    finally:
        conn.close()


def test_check_fails_on_legacy_event_rows_for_scope() -> None:
    """Legacy event-class rows alone (no body uploads) → exit non-zero."""
    _seed_legacy_event_row()
    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    flat_nows = flat.replace(" ", "")
    assert "Identity boundary check FAILED" in flat
    assert "queue.db" in flat_nows
    # The event subtotal is surfaced as ``queue=<N>`` in the failure line.
    assert "queue=1" in flat_nows


def test_check_fails_on_legacy_body_upload_rows_for_scope() -> None:
    """Legacy body-upload rows alone (no event rows) → exit non-zero."""
    _seed_legacy_body_upload(mission_slug="some-other-mission")
    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code != 0, result.stdout
    flat = " ".join(result.stdout.split())
    flat_nows = flat.replace(" ", "")
    assert "Identity boundary check FAILED" in flat
    assert "body_upload_queue" in flat_nows


# ---------------------------------------------------------------------------
# T016: --check --json shape (T014)
# ---------------------------------------------------------------------------


def test_check_json_mode_emits_documented_shape_for_coherent_host() -> None:
    """``--check --json`` on a coherent host emits the documented JSON shape.

    All top-level keys from ``contracts/sync-status-output.md`` are
    present; ``ok`` is ``true``; ``mismatches`` and ``orphan_records``
    are empty lists; exit code is 0.
    """
    import json

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code == 0, result.stdout
    # The JSON object is the only thing on stdout — no Rich markup.
    parsed = json.loads(result.stdout.strip())

    expected_keys = {
        "ok",
        "exit_code",
        "foreground",
        "daemon_owner_record",
        "active_queue",
        "legacy_queue",
        "mismatches",
        "orphan_records",
    }
    assert expected_keys.issubset(parsed.keys())
    assert parsed["ok"] is True
    assert parsed["exit_code"] == 0
    assert parsed["mismatches"] == []
    assert parsed["orphan_records"] == []
    # Foreground subfields per contract.
    fg = parsed["foreground"]
    for key in (
        "package_version",
        "executable_path",
        "source_path",
        "server_url",
        "team_or_user",
        "queue_db_path",
        "pid",
    ):
        assert key in fg
    # Daemon owner record: status is "absent" when no record on disk.
    daemon = parsed["daemon_owner_record"]
    assert daemon["status"] == "absent"
    # Legacy queue subfields per contract.
    legacy = parsed["legacy_queue"]
    for key in ("path", "event_count", "body_upload_count", "rows_in_scope"):
        assert key in legacy


def test_check_json_mode_emits_non_empty_mismatches_for_split_brain_host() -> None:
    """``--check --json`` on a split-brain host has non-empty ``mismatches``."""
    import json

    from specify_cli.sync.owner import write_owner_record

    record = _build_owner_record(package_version="0.0.0-stale")
    write_owner_record(record)

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code == 2, result.stdout
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is False
    assert parsed["exit_code"] == 2
    assert len(parsed["mismatches"]) >= 1
    # The mismatch entry carries the canonical field name with the
    # ``daemon_`` prefix per the contract Domain Language.
    fields = {m["field"] for m in parsed["mismatches"]}
    assert "daemon_package_version" in fields
    # Each mismatch entry exposes the four documented keys.
    for m in parsed["mismatches"]:
        assert set(m.keys()) == {
            "field",
            "foreground_value",
            "daemon_value",
            "remediation_hint",
        }


# ---------------------------------------------------------------------------
# T016: status prints the full FR-005 field set (default human view)
# ---------------------------------------------------------------------------


def test_status_prints_all_fr005_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync status --check`` prints every label from the status-output contract.

    This locks the FR-005 printed-field coverage: each label in
    ``contracts/sync-status-output.md`` shows up somewhere in stdout.
    """
    # The FR-005 label set is independent of SaaS sync state; keep the
    # feature flag off so the auth-required refusal does not short-circuit
    # the rendered table before the labels are printed.
    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
    result = runner.invoke(app, ["status", "--check"])
    # Exit code may be 0 or 2 depending on the live boundary state, but
    # the printed labels MUST appear either way.
    flat = " ".join(result.stdout.split())
    flat_nows = flat.replace(" ", "")
    # The section headers from the contract.
    assert "Foreground" in flat
    assert "Daemonownerrecord" in flat_nows or "Daemon owner record" in flat
    assert "Activequeue" in flat_nows or "Active queue" in flat
    assert "Legacyqueue" in flat_nows or "Legacy queue" in flat
    # Per-field labels — verify presence; the exact human form is
    # subject to Rich wrapping so we collapse whitespace before checking.
    for label in (
        "Package version",
        "Executable path",
        "Source path",
        "Server URL",
        "Team/User",
        "Queue DB path",
        "Event count",
        "Body upload",
        "Rows in scope",
        "Mismatches",
        "Orphan records",
    ):
        compact = label.replace(" ", "")
        assert compact in flat_nows, (
            f"missing FR-005 label {label!r} in --check output"
        )


# ---------------------------------------------------------------------------
# FR-004 (review cycle 2): auth-required refusal under SPEC_KITTY_ENABLE_SAAS_SYNC=1
# ---------------------------------------------------------------------------


def test_check_human_exits_two_when_saas_enabled_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``sync status --check`` exits 2 when SAAS sync enabled and no auth.

    Contract reference: ``contracts/sync-status-output.md`` —
    "SPEC_KITTY_ENABLE_SAAS_SYNC=1 set but no authenticated identity
    available" maps to exit code 2.

    Previously the human ``--check`` path short-circuited through the
    ``handle_unauthenticated_with_teamspace`` recovery branch with exit
    code 4. The boundary gate now owns this case and exits 2 with the
    auth-absent reason named in the rendered failure block.
    """
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code == 2, result.stdout
    flat = " ".join(result.stdout.split())
    assert "Identity boundary check FAILED" in flat
    # The auth-absent line names the reason explicitly.
    assert "no authenticated identity" in flat or "auth login" in flat


def test_check_json_exits_two_when_saas_enabled_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``sync status --check --json`` exits 2 with ok=false when auth absent.

    The JSON body MUST carry ``ok=false``, ``exit_code=2``,
    ``auth_required=true``, and ``auth_present=false`` so external
    automation can distinguish auth-absent failures from structural
    boundary failures.

    Previously this path emitted ``ok=true`` and exited 0 because the
    JSON short-circuit only consulted the structural ``BoundaryFailureSet``.
    """
    import json

    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code == 2, result.stdout
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is False
    assert parsed["exit_code"] == 2
    assert parsed["auth_required"] is True
    assert parsed["auth_present"] is False


def test_check_json_exits_zero_when_saas_disabled_and_unauthenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SAAS sync is disabled, auth absence does NOT trip the gate.

    ``auth_required`` reflects the feature-flag state; with the flag off,
    a coherent boundary plus absent auth still yields exit 0.
    """
    import json

    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is True
    assert parsed["auth_required"] is False
    assert parsed["auth_present"] is False
