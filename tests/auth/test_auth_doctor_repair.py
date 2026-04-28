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
from specify_cli.core.file_lock import LockRecord
from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.sync.orphan_sweep import OrphanDaemon, SweepReport


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


def _patch_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: StoredSession | None,
    lock_path: Path,
    lock_record: LockRecord | None = None,
    daemon_state_exists: bool = False,
    orphans: list[OrphanDaemon] | None = None,
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
    monkeypatch.setattr(
        _auth_doctor, "get_sync_daemon_status", lambda: SyncDaemonStatus(healthy=False)
    )
    monkeypatch.setattr(
        _auth_doctor, "enumerate_orphans", lambda: list(orphans or [])
    )
    import sys

    fake_rollout = type(sys)("specify_cli.saas.rollout")
    fake_rollout.is_saas_sync_enabled = lambda: False  # type: ignore[attr-defined]
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
    """Orphan present; ``--reset`` invokes ``sweep_orphans``."""
    session = _make_session()
    orphan = OrphanDaemon(port=9401, pid=12345, package_version="3.2.0a4", protocol_version=1)

    sweep_calls: list[list[OrphanDaemon]] = []

    def fake_sweep(orphans: list[OrphanDaemon]) -> SweepReport:
        sweep_calls.append(list(orphans))
        return SweepReport(swept=list(orphans), failed=[], duration_s=0.01)

    monkeypatch.setattr(_auth_doctor, "sweep_orphans", fake_sweep)

    # Non-existent lock path keeps F-003 from firing.
    _patch_state(
        monkeypatch,
        session=session,
        lock_path=tmp_path / "auth" / "refresh.lock",
        orphans=[orphan],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0
    )

    assert sweep_calls == [[orphan]]
    # Warn-severity F-002 shouldn't drive exit-code 1.
    assert exit_code == 0


def test_reset_noop_when_no_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No orphans ⇒ ``--reset`` does NOT call ``sweep_orphans``."""
    session = _make_session()

    sweep_called = []

    def fake_sweep(orphans: list[OrphanDaemon]) -> SweepReport:
        sweep_called.append(orphans)
        return SweepReport(swept=[], failed=[], duration_s=0.0)

    monkeypatch.setattr(_auth_doctor, "sweep_orphans", fake_sweep)
    _patch_state(
        monkeypatch,
        session=session,
        lock_path=tmp_path / "auth" / "refresh.lock",
        orphans=[],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0
    )

    assert sweep_called == []
    assert exit_code == 0


# ---------------------------------------------------------------------------
# --unstick-lock
# ---------------------------------------------------------------------------


def test_unstick_drops_old_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """120-second-old lock + ``--unstick-lock`` ⇒ lock file removed."""
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

    assert not lock_path.exists()
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
    orphan = OrphanDaemon(port=9402, pid=22222, package_version="3.2.0a4", protocol_version=1)
    lock_path = tmp_path / "auth" / "refresh.lock"
    _write_lock_record(lock_path, age_s=120.0)

    sweep_calls: list[list[OrphanDaemon]] = []

    def fake_sweep(orphans: list[OrphanDaemon]) -> SweepReport:
        sweep_calls.append(list(orphans))
        return SweepReport(swept=list(orphans), failed=[], duration_s=0.01)

    monkeypatch.setattr(_auth_doctor, "sweep_orphans", fake_sweep)

    _patch_state(
        monkeypatch,
        session=session,
        lock_path=lock_path,
        orphans=[orphan],
    )

    exit_code = doctor_impl(
        json_output=True, reset=True, unstick_lock=True, stuck_threshold=60.0
    )

    assert sweep_calls == [[orphan]]
    assert not lock_path.exists()
    # After both repairs nothing critical remains.
    assert exit_code == 0
