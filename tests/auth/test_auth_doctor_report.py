"""Tests for the read-only ``spec-kitty auth doctor`` report (WP06 / T028).

Covers the contract surface in ``contracts/auth-doctor.md``:
section rendering, finding triggers, exit-code policy, the legacy
session string, the NFR-006 wall-clock ceiling, and JSON schema shape.

Also covers the ``--server`` flag (WP04 / T019):
- ServerSessionStatus dataclass construction
- _check_server_session() async function (200, 401, network error)
- doctor_impl server=False makes no outbound calls
- doctor_impl server=True renders active/re-authenticate output

All tests use ``monkeypatch`` to inject deterministic state for
``assemble_report``'s upstream dependencies — no SaaS, no real daemon.
"""

from __future__ import annotations

import io
import json
import time
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import _auth_doctor
from specify_cli.cli.commands._auth_doctor import (
    DoctorReport,
    ServerSessionStatus,
    _check_server_session,
    assemble_report,
    compute_exit_code,
    doctor_impl,
    render_report,
    render_report_json,
)
from specify_cli.core.file_lock import LockRecord
from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.sync.orphan_sweep import OrphanDaemon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(
    *,
    refresh_token_expires_at: datetime | None,
) -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-abc",
        email="rob@example.com",
        name="Rob",
        teams=[Team(id="t1", name="Personal", role="owner", is_private_teamspace=True)],
        default_team_id="t1",
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="session-xyz",
        issued_at=now,
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=refresh_token_expires_at,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class _FakeStorage:
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session


class _FakeTokenManager:
    """Test double for :class:`TokenManager` matching the public API used here."""

    def __init__(self, session: StoredSession | None) -> None:
        self._session = session
        self._storage = _FakeStorage(session)

    def get_current_session(self) -> StoredSession | None:
        return self._session


def _patch_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: StoredSession | None,
    lock_record: LockRecord | None = None,
    daemon_status: SyncDaemonStatus | None = None,
    daemon_state_exists: bool = False,
    orphans: list[OrphanDaemon] | None = None,
    auth_root: Path | None = None,
    rollout_enabled: bool = False,
) -> None:
    """Wire ``_auth_doctor``'s upstream calls to deterministic fakes."""
    monkeypatch.setattr(
        _auth_doctor,
        "get_token_manager",
        lambda: _FakeTokenManager(session),
    )
    monkeypatch.setattr(_auth_doctor, "read_lock_record", lambda _path: lock_record)
    if auth_root is None:
        auth_root = Path("/tmp/spec-kitty-doctor-test/auth/refresh.lock")
    monkeypatch.setattr(_auth_doctor, "_refresh_lock_path", lambda: auth_root)

    class _FakeStateFile:
        def __init__(self, exists: bool) -> None:
            self._exists = exists

        def exists(self) -> bool:
            return self._exists

    monkeypatch.setattr(
        _auth_doctor, "DAEMON_STATE_FILE", _FakeStateFile(daemon_state_exists)
    )
    if daemon_status is None:
        daemon_status = SyncDaemonStatus(healthy=False)
    monkeypatch.setattr(
        _auth_doctor, "get_sync_daemon_status", lambda: daemon_status
    )
    monkeypatch.setattr(
        _auth_doctor, "enumerate_orphans", lambda: list(orphans or [])
    )
    # Disable rollout-enabled finding F-005 unless the test asks for it.
    import sys

    fake_rollout_module = type(sys)("specify_cli.saas.rollout")
    fake_rollout_module.is_saas_sync_enabled = lambda: rollout_enabled  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.saas.rollout", fake_rollout_module)


def _capture_render(report: DoctorReport) -> str:
    """Render the report to a string by feeding Rich into a StringIO."""
    buf = io.StringIO()
    console = Console(file=buf, width=120, record=False, force_terminal=False)
    render_report(report, console)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_renders_authenticated_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Healthy state ⇒ all 7 sections render; findings empty; exit 0."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    report = assemble_report()

    assert report.session is not None
    assert report.session.present is True
    assert report.findings == []
    assert compute_exit_code(report.findings) == 0

    rendered = _capture_render(report)
    for section in (
        "Identity",
        "Tokens",
        "Storage",
        "Refresh Lock",
        "Daemon",
        "Orphans",
        "Findings",
    ):
        assert section in rendered, f"section {section!r} missing from rendered output"
    assert "No problems detected." in rendered


def test_renders_unauthenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    """No session ⇒ F-001 critical; exit 1."""
    _patch_state(monkeypatch, session=None)

    report = assemble_report()

    assert report.session is None
    assert any(f.id == "F-001" and f.severity == "critical" for f in report.findings)
    assert compute_exit_code(report.findings) == 1

    rendered = _capture_render(report)
    assert "Not authenticated" in rendered
    assert "F-001" in rendered


def test_renders_orphan_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """One orphan present ⇒ F-002 warn; exit 0 (warn is not critical)."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    orphan = OrphanDaemon(
        port=9401, pid=12345, package_version="3.2.0a4", protocol_version=1
    )
    _patch_state(monkeypatch, session=session, orphans=[orphan])

    report = assemble_report()

    assert any(f.id == "F-002" and f.severity == "warn" for f in report.findings)
    assert all(f.severity != "critical" for f in report.findings)
    assert compute_exit_code(report.findings) == 0

    rendered = _capture_render(report)
    assert "F-002" in rendered
    assert "9401" in rendered


def test_renders_stuck_lock_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lock record 120 s old ⇒ F-003 critical; exit 1."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    lock = LockRecord(
        schema_version=1,
        pid=99999,
        started_at=datetime.now(UTC) - timedelta(seconds=120),
        host="localhost",
        version="3.2.0a5",
    )
    # Force the holder_host to match local socket so F-007 doesn't fire.
    import socket

    lock = LockRecord(
        schema_version=1,
        pid=99999,
        started_at=datetime.now(UTC) - timedelta(seconds=120),
        host=socket.gethostname(),
        version="3.2.0a5",
    )
    _patch_state(monkeypatch, session=session, lock_record=lock)

    report = assemble_report(stuck_threshold_s=60.0)

    assert any(
        f.id == "F-003" and f.severity == "critical" for f in report.findings
    )
    assert compute_exit_code(report.findings) == 1


def test_renders_legacy_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """``refresh_token_expires_at is None`` ⇒ "server-managed (legacy)" line; no extra finding."""
    session = _make_session(refresh_token_expires_at=None)
    _patch_state(monkeypatch, session=session)

    report = assemble_report()
    rendered = _capture_render(report)

    assert "server-managed (legacy)" in rendered
    # No F-001 or other critical finding for a legacy session.
    assert all(f.severity != "critical" for f in report.findings)


def test_runs_under_three_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Healthy state + simulated 50-port scan ⇒ wall-clock < 3 s.

    NFR-006 verifies ``assemble_report`` returns within 3 seconds. Real
    ``enumerate_orphans`` is fast (50 ms TCP connect-check pre-filter)
    but for this unit test we patch it with a tiny synthetic delay so
    we exercise the *whole* pipeline rather than the network layer.
    """
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )

    def fake_enumerate() -> list[OrphanDaemon]:
        # Simulate the worst-case 50-port scan completing very quickly.
        time.sleep(0.05)
        return []

    _patch_state(monkeypatch, session=session)
    monkeypatch.setattr(_auth_doctor, "enumerate_orphans", fake_enumerate)

    started = time.monotonic()
    report = assemble_report()
    elapsed = time.monotonic() - started

    assert elapsed < 3.0, f"assemble_report took {elapsed:.2f}s (NFR-006 ceiling = 3s)"
    assert report.findings == []


def test_renders_held_fresh_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh held lock ⇒ section renders holder PID, age, host; no F-003."""
    import socket

    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    lock = LockRecord(
        schema_version=1,
        pid=42,
        started_at=datetime.now(UTC) - timedelta(seconds=2),
        host=socket.gethostname(),
        version="3.2.0a5",
    )
    _patch_state(monkeypatch, session=session, lock_record=lock)

    report = assemble_report()
    rendered = _capture_render(report)

    assert "Held by PID:" in rendered
    assert "42" in rendered
    # Fresh lock ⇒ no F-003
    assert all(f.id != "F-003" for f in report.findings)


def test_renders_active_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Healthy daemon ⇒ section prints PID/Port/Package/Protocol."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    daemon_status = SyncDaemonStatus(
        healthy=True,
        url="http://127.0.0.1:9400",
        port=9400,
        token="tok",
        pid=12345,
        package_version="3.2.0a5",
        protocol_version=1,
    )
    _patch_state(
        monkeypatch,
        session=session,
        daemon_status=daemon_status,
        daemon_state_exists=True,
    )

    report = assemble_report()
    rendered = _capture_render(report)

    assert "Active:" in rendered
    assert "9400" in rendered
    assert "12345" in rendered
    assert report.daemon is not None
    assert report.daemon.active is True


def test_renders_recorded_unhealthy_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Daemon state file exists but health probe fails ⇒ "recorded but not healthy"."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    daemon_status = SyncDaemonStatus(
        healthy=False, port=9400, pid=12345
    )
    _patch_state(
        monkeypatch,
        session=session,
        daemon_status=daemon_status,
        daemon_state_exists=True,
    )

    report = assemble_report()
    rendered = _capture_render(report)

    assert "recorded but not healthy" in rendered
    assert "12345" in rendered


def test_nfs_holder_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """F-007 fires when the lock holder host differs from the local hostname."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    lock = LockRecord(
        schema_version=1,
        pid=42,
        started_at=datetime.now(UTC) - timedelta(seconds=2),
        host="some-other-host.example.com",
        version="3.2.0a5",
    )
    _patch_state(monkeypatch, session=session, lock_record=lock)

    report = assemble_report()

    assert any(f.id == "F-007" and f.severity == "warn" for f in report.findings)


def test_json_output_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--json`` payload validates against ``data-model.md`` §5 schema."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    report = assemble_report()
    payload = json.loads(render_report_json(report))

    # Top-level keys.
    for key in (
        "schema_version",
        "generated_at",
        "auth_root",
        "session",
        "refresh_lock",
        "daemon",
        "orphans",
        "findings",
    ):
        assert key in payload

    assert payload["schema_version"] == 1
    # ISO-8601 datetime
    datetime.fromisoformat(payload["generated_at"])
    # auth_root is a string path
    assert isinstance(payload["auth_root"], str)

    # Session payload shape.
    session_payload = payload["session"]
    for key in (
        "present",
        "session_id",
        "user_email",
        "access_token_remaining_s",
        "refresh_token_remaining_s",
        "storage_backend",
        "in_memory_drift",
    ):
        assert key in session_payload

    # Refresh-lock payload shape.
    lock_payload = payload["refresh_lock"]
    for key in (
        "held",
        "holder_pid",
        "started_at",
        "age_s",
        "stuck",
        "stuck_threshold_s",
    ):
        assert key in lock_payload

    # Findings list (empty in healthy state).
    assert payload["findings"] == []


# ---------------------------------------------------------------------------
# T019: ServerSessionStatus dataclass
# ---------------------------------------------------------------------------


def test_server_session_status_active() -> None:
    """ServerSessionStatus(active=True, session_id='abc') constructs without error."""
    s = ServerSessionStatus(active=True, session_id="abc")
    assert s.active is True
    assert s.session_id == "abc"
    assert s.error is None


def test_server_session_status_inactive() -> None:
    """ServerSessionStatus(active=False, error='re-authenticate') constructs without error."""
    s = ServerSessionStatus(active=False, error="re-authenticate")
    assert s.active is False
    assert s.session_id is None
    assert s.error == "re-authenticate"


def test_server_session_status_frozen() -> None:
    """ServerSessionStatus is frozen — mutation raises FrozenInstanceError."""
    import dataclasses

    s = ServerSessionStatus(active=True, session_id="abc")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.active = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T019: _check_server_session async tests
# ---------------------------------------------------------------------------


async def test_check_server_session_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/v1/session-status 200 → ServerSessionStatus(active=True, session_id='abc')."""
    mock_tm = AsyncMock()
    mock_tm.get_access_token = AsyncMock(return_value="tok")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"session_id": "abc", "status": "active"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    # _check_server_session imports get_token_manager locally from specify_cli.auth
    import specify_cli.auth as _auth_module
    monkeypatch.setattr(_auth_module, "get_token_manager", lambda: mock_tm)

    with (
        patch("specify_cli.auth.config.get_saas_base_url", return_value="https://saas.example.com"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await _check_server_session()

    assert result.active is True
    assert result.session_id == "abc"
    assert result.error is None


async def test_check_server_session_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/v1/session-status 401 → ServerSessionStatus(active=False, error='re-authenticate')."""
    mock_tm = AsyncMock()
    mock_tm.get_access_token = AsyncMock(return_value="tok")

    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    import specify_cli.auth as _auth_module
    monkeypatch.setattr(_auth_module, "get_token_manager", lambda: mock_tm)

    with (
        patch("specify_cli.auth.config.get_saas_base_url", return_value="https://saas.example.com"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await _check_server_session()

    assert result.active is False
    assert result.error == "re-authenticate"
    # The error must not contain any token content.
    assert "tok" not in (result.error or "")


async def test_check_server_session_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network error → ServerSessionStatus(active=False, error contains type name)."""
    import httpx

    mock_tm = AsyncMock()
    mock_tm.get_access_token = AsyncMock(return_value="tok")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    import specify_cli.auth as _auth_module
    monkeypatch.setattr(_auth_module, "get_token_manager", lambda: mock_tm)

    with (
        patch("specify_cli.auth.config.get_saas_base_url", return_value="https://saas.example.com"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await _check_server_session()

    assert result.active is False
    assert result.error is not None
    assert "ConnectError" in result.error
    # Access token must not appear in the error.
    assert "tok" not in result.error


@pytest.mark.asyncio
async def test_check_server_session_refresh_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    """RefreshTokenExpiredError → user-friendly re-authenticate error, not class name."""
    from specify_cli.auth.errors import RefreshTokenExpiredError

    mock_tm = AsyncMock()
    mock_tm.get_access_token = AsyncMock(side_effect=RefreshTokenExpiredError("expired"))

    import specify_cli.auth as _auth_module
    monkeypatch.setattr(_auth_module, "get_token_manager", lambda: mock_tm)

    result = await _check_server_session()

    assert result.active is False
    assert result.error is not None
    assert "re-authenticate" in result.error
    # Must NOT expose the class name as raw diagnostic output.
    assert "RefreshTokenExpiredError" not in result.error


@pytest.mark.asyncio
async def test_check_server_session_session_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """SessionInvalidError → user-friendly re-authenticate error, not class name."""
    from specify_cli.auth.errors import SessionInvalidError

    mock_tm = AsyncMock()
    mock_tm.get_access_token = AsyncMock(side_effect=SessionInvalidError("invalidated"))

    import specify_cli.auth as _auth_module
    monkeypatch.setattr(_auth_module, "get_token_manager", lambda: mock_tm)

    result = await _check_server_session()

    assert result.active is False
    assert result.error is not None
    assert "re-authenticate" in result.error
    assert "SessionInvalidError" not in result.error


# ---------------------------------------------------------------------------
# T019: doctor_impl server flag tests
# ---------------------------------------------------------------------------


def test_doctor_impl_server_false_no_outbound_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """server=False must not call asyncio.run or _check_server_session."""
    import asyncio

    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    asyncio_run_called = []

    def _fail_asyncio_run(coro, *args, **kwargs):  # type: ignore[no-untyped-def]
        asyncio_run_called.append(True)
        raise AssertionError("asyncio.run called with server=False — C-007 violation")

    monkeypatch.setattr(asyncio, "run", _fail_asyncio_run)

    exit_code = doctor_impl(
        json_output=True,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
        server=False,
    )

    assert asyncio_run_called == [], "asyncio.run must not be called with server=False"
    assert exit_code == 0


def test_doctor_impl_server_true_renders_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """server=True + active session → output contains 'active' and session id."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    fake_status = ServerSessionStatus(active=True, session_id="s1")

    import asyncio

    def _fake_run(coro):  # type: ignore[no-untyped-def]
        coro.close()  # Prevent "coroutine never awaited" warning.
        return fake_status

    monkeypatch.setattr(asyncio, "run", _fake_run)

    buf = io.StringIO()
    monkeypatch.setattr(
        _auth_doctor,
        "console",
        Console(file=buf, width=120, record=False, force_terminal=False),
    )

    exit_code = doctor_impl(
        json_output=False,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
        server=True,
    )

    output = buf.getvalue()
    assert "active" in output
    assert "s1" in output
    assert exit_code == 0


def test_doctor_impl_server_true_renders_reauthenticate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """server=True + 401 → output contains 're-authenticate' guidance."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    fake_status = ServerSessionStatus(active=False, error="re-authenticate")

    import asyncio

    def _fake_run(coro):  # type: ignore[no-untyped-def]
        coro.close()
        return fake_status

    monkeypatch.setattr(asyncio, "run", _fake_run)

    buf = io.StringIO()
    monkeypatch.setattr(
        _auth_doctor,
        "console",
        Console(file=buf, width=120, record=False, force_terminal=False),
    )

    exit_code = doctor_impl(
        json_output=False,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
        server=True,
    )

    output = buf.getvalue()
    assert "re-authenticate" in output or "login" in output.lower()
    assert exit_code == 0


def test_doctor_impl_server_true_json_includes_server_session(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """server=True + --json → payload includes server_session key."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    fake_status = ServerSessionStatus(active=True, session_id="s2")

    import asyncio

    def _fake_run(coro):  # type: ignore[no-untyped-def]
        coro.close()
        return fake_status

    monkeypatch.setattr(asyncio, "run", _fake_run)

    exit_code = doctor_impl(
        json_output=True,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
        server=True,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "server_session" in payload
    assert payload["server_session"]["active"] is True
    assert payload["server_session"]["session_id"] == "s2"
    assert exit_code == 0


def test_default_doctor_output_has_server_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default auth doctor output ends with the --server hint line."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    report = assemble_report()
    rendered = _capture_render(report)

    assert "spec-kitty auth doctor --server" in rendered


def test_server_doctor_output_no_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auth doctor --server output does NOT show the hint."""
    session = _make_session(
        refresh_token_expires_at=datetime.now(UTC) + timedelta(days=30)
    )
    _patch_state(monkeypatch, session=session)

    report = assemble_report()
    buf = io.StringIO()
    con = Console(file=buf, width=120, record=False, force_terminal=False)
    render_report(report, con, show_server_hint=False)
    output = buf.getvalue()

    assert "spec-kitty auth doctor --server" not in output
