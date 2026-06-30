"""Tests for ``spec-kitty auth doctor`` opt-in repair flags (WP06 / T028).

Covers ``--reset`` (sweep orphans via WP05) and ``--unstick-lock``
(force-release the refresh lock via WP01). Both flags are independent
(C-008); there is intentionally no ``--auto-fix``.

The age-guard inside :func:`force_release` (``only_if_age_s``) is the
WP01-enforced safety belt — :func:`doctor_impl` must pass the
``stuck_threshold`` through unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import _auth_doctor
from specify_cli.cli.commands._auth_doctor import doctor_impl
from specify_cli.core.file_lock import LockRecord, read_lock_record
from specify_cli.sync.classification import (
    CleanupClass,
    DaemonIdentityRecord,
    IdentitySource,
)
from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.sync.orphan_sweep import (
    ResetResult,
    SweptEntry,
)


pytestmark = [pytest.mark.integration]

def _make_session() -> StoredSession:
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
        refresh_token_expires_at=now + timedelta(days=30),
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
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session
        self._storage = _FakeStorage(session)

    def get_current_session(self) -> StoredSession | None:
        return self._session


def _make_identity_record(port: int, *, pid: int | None = 12345) -> DaemonIdentityRecord:
    """Return a minimal safe_auto DaemonIdentityRecord for a given port."""
    return DaemonIdentityRecord(
        daemon_family="sync",
        pid=pid,
        port=port,
        protocol_version=1,
        package_version="3.2.0a4",
        singleton_scope_id=None,
        daemon_root=None,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
        owner_present=False,
        identity_source=IdentitySource.health_self_report,
        executable_summary=None,
        spawn_shape_ok=True,
        self_report_matches_listener=True,
        is_recorded_singleton=False,
        cleanup_class=CleanupClass.SAFE_AUTO,
        skip_reason=None,
    )


def _patch_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: StoredSession | None,
    lock_path: Path,
    lock_record: LockRecord | None = None,
    daemon_state_exists: bool = False,
    daemon_status: SyncDaemonStatus | None = None,
    # WP05 repoint: _auth_doctor now calls enumerate_identity_records (not
    # enumerate_orphans); callers pass DaemonIdentityRecord lists here.
    orphans: list[DaemonIdentityRecord] | None = None,
) -> None:
    """Wire ``_auth_doctor``'s upstream calls to deterministic fakes.

    Important: ``read_lock_record`` is NOT patched — the test wants
    ``--unstick-lock`` to read the *real* file at ``lock_path`` so the
    ``force_release`` age guard is exercised end-to-end.
    """
    monkeypatch.setattr(
        _auth_doctor,
        "get_token_manager",
        lambda: _FakeTokenManager(session),
    )
    monkeypatch.setattr(_auth_doctor, "_refresh_lock_path", lambda: lock_path)

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
    # WP05 repoint: enumerate_orphans removed from _auth_doctor; mock the new
    # enumerate_identity_records symbol that assemble_report() now calls.
    monkeypatch.setattr(
        _auth_doctor, "enumerate_identity_records", lambda: list(orphans or [])
    )
    import sys

    fake_rollout = type(sys)("specify_cli.saas.rollout")
    fake_rollout.is_saas_sync_enabled = lambda: False  # type: ignore[attr-defined]  # stub attr on a dynamically-built ModuleType; mypy cannot see it
    monkeypatch.setitem(sys.modules, "specify_cli.saas.rollout", fake_rollout)


def _write_lock_record(path: Path, *, age_s: float) -> None:
    """Write a JSON lock record at ``path`` with started_at = now - age_s."""
    started = datetime.now(UTC) - timedelta(seconds=age_s)
    payload = {
        "schema_version": 1,
        "pid": 99999,
        "started_at": started.isoformat(),
        "host": "localhost",
        "version": "3.2.0a5",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# --reset
# ---------------------------------------------------------------------------


def test_reset_sweeps_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Orphan present; ``--reset`` invokes ``reset_orphans``."""
    session = _make_session()
    # WP05 repoint: _auth_doctor now passes DaemonIdentityRecord lists to
    # reset_orphans (not OrphanDaemon lists to sweep_orphans). The mock must
    # match the new signature and return a ResetResult.
    orphan_record = _make_identity_record(9401, pid=12345)

    reset_calls: list[list[DaemonIdentityRecord]] = []

    def fake_reset(
        records: list[DaemonIdentityRecord], *, include_operator_required: bool = False
    ) -> ResetResult:
        reset_calls.append(list(records))
        swept = [
            SweptEntry(
                pid=r.pid,
                port=r.port,
                package_version=r.package_version,
                protocol_version=r.protocol_version,
                cleanup_path="http_shutdown",
                reason="safe_auto",
            )
            for r in records
        ]
        return ResetResult(swept=swept, skipped=[], failed=[])

    monkeypatch.setattr(_auth_doctor, "reset_orphans", fake_reset)

    # Non-existent lock path keeps F-003 from firing.
    _patch_state(
        monkeypatch,
        session=session,
        lock_path=tmp_path / "auth" / "refresh.lock",
        orphans=[orphan_record],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0
    )

    assert reset_calls == [[orphan_record]]
    # Warn-severity F-002 shouldn't drive exit-code 1.
    assert exit_code == 0


def test_reset_noop_when_no_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No orphans ⇒ ``--reset`` does NOT call ``reset_orphans``."""
    session = _make_session()

    # WP05 repoint: reset_orphans replaces sweep_orphans; verify it is not
    # called when the orphan list is empty (no F-002 finding active).
    reset_called: list[list[DaemonIdentityRecord]] = []

    def fake_reset(
        records: list[DaemonIdentityRecord], *, include_operator_required: bool = False
    ) -> ResetResult:
        reset_called.append(list(records))
        return ResetResult(swept=[], skipped=[], failed=[])

    monkeypatch.setattr(_auth_doctor, "reset_orphans", fake_reset)
    _patch_state(
        monkeypatch,
        session=session,
        lock_path=tmp_path / "auth" / "refresh.lock",
        orphans=[],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0
    )

    assert reset_called == []
    assert exit_code == 0


def test_reset_repairs_recorded_unhealthy_daemon(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Recorded-but-unhealthy singleton daemon is repaired by ``--reset``."""
    session = _make_session()
    stop_calls: list[None] = []

    def fake_stop_sync_daemon() -> tuple[bool, str]:
        stop_calls.append(None)
        return True, "Unhealthy sync daemon process stopped. Metadata has been cleared."

    monkeypatch.setattr(_auth_doctor, "stop_sync_daemon", fake_stop_sync_daemon)
    _patch_state(
        monkeypatch,
        session=session,
        lock_path=tmp_path / "auth" / "refresh.lock",
        daemon_state_exists=True,
        daemon_status=SyncDaemonStatus(healthy=False, port=9402, pid=12835),
        orphans=[],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0
    )

    assert stop_calls == [None]
    assert exit_code == 0


# ---------------------------------------------------------------------------
# --unstick-lock
# ---------------------------------------------------------------------------


def test_unstick_drops_old_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """120-second-old lock + ``--unstick-lock`` ⇒ lock record cleared."""
    session = _make_session()
    lock_path = tmp_path / "auth" / "refresh.lock"
    _write_lock_record(lock_path, age_s=120.0)
    assert lock_path.exists()

    _patch_state(
        monkeypatch,
        session=session,
        lock_path=lock_path,
    )

    exit_code = doctor_impl(
        json_output=True, reset=False, unstick_lock=True, stuck_threshold=60.0
    )

    assert read_lock_record(lock_path) is None
    # F-003 was the only critical finding; after the unstick repair the
    # second pass finds nothing critical so exit 0.
    assert exit_code == 0


def test_unstick_preserves_fresh_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """5-second-old lock + ``--unstick-lock`` ⇒ no-op; lock still present."""
    session = _make_session()
    lock_path = tmp_path / "auth" / "refresh.lock"
    _write_lock_record(lock_path, age_s=5.0)
    assert lock_path.exists()

    _patch_state(
        monkeypatch,
        session=session,
        lock_path=lock_path,
    )

    exit_code = doctor_impl(
        json_output=True, reset=False, unstick_lock=True, stuck_threshold=60.0
    )

    assert lock_path.exists(), "Fresh lock must not be removed"
    # No F-003 (lock not stuck), no other critical findings, exit 0.
    assert exit_code == 0


def test_combined_flags_run_both(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--reset --unstick-lock`` runs both repairs."""
    session = _make_session()
    # WP05 repoint: _auth_doctor passes DaemonIdentityRecord to reset_orphans.
    orphan_record = _make_identity_record(9402, pid=22222)
    lock_path = tmp_path / "auth" / "refresh.lock"
    _write_lock_record(lock_path, age_s=120.0)

    reset_calls: list[list[DaemonIdentityRecord]] = []

    def fake_reset(
        records: list[DaemonIdentityRecord], *, include_operator_required: bool = False
    ) -> ResetResult:
        reset_calls.append(list(records))
        swept = [
            SweptEntry(
                pid=r.pid,
                port=r.port,
                package_version=r.package_version,
                protocol_version=r.protocol_version,
                cleanup_path="http_shutdown",
                reason="safe_auto",
            )
            for r in records
        ]
        return ResetResult(swept=swept, skipped=[], failed=[])

    monkeypatch.setattr(_auth_doctor, "reset_orphans", fake_reset)

    _patch_state(
        monkeypatch,
        session=session,
        lock_path=lock_path,
        orphans=[orphan_record],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=True, stuck_threshold=60.0
    )

    assert reset_calls == [[orphan_record]]
    assert read_lock_record(lock_path) is None
    # After both repairs nothing critical remains.
    assert exit_code == 0
