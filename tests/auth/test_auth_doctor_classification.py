"""Tests for ``spec-kitty auth doctor`` classification rendering and reset reporting (WP05).

Coverage:
- T022: ``--json`` emits ``schema_version==2`` and per-record ``cleanup_class``
- T023: ``--reset --json`` emits ``reset_result`` with swept/skipped/failed arrays
- T023: default ``--reset`` skips ``operator_required`` and prints the ``--force`` hint
- T021: ``--force`` includes ``operator_required`` daemons in the sweep
- T024: plain ``auth doctor`` (no ``--reset``) performs no sweep at all

All tests patch ``enumerate_identity_records`` / ``reset_orphans`` with fakes
and follow the offline pattern in ``tests/auth/test_auth_doctor_offline.py``.
No real daemons are involved.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, UTC
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import _auth_doctor
from specify_cli.cli.commands._auth_doctor import doctor_impl
from specify_cli.sync.classification import (
    CleanupClass,
    DaemonIdentityRecord,
    IdentitySource,
    SkipReason,
)
from specify_cli.sync.daemon import SyncDaemonStatus
from specify_cli.sync.orphan_sweep import (
    FailedEntry,
    ResetResult,
    SkippedEntry,
    SweptEntry,
)


pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


class _FakeTokenManager:
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session

    def get_current_session(self) -> StoredSession | None:
        return self._session


def _make_safe_auto_record(port: int = 9401) -> DaemonIdentityRecord:
    """Return a DaemonIdentityRecord with cleanup_class == safe_auto."""
    return DaemonIdentityRecord(
        daemon_family="sync",
        pid=5001,
        port=port,
        protocol_version=1,
        package_version="3.2.2",
        singleton_scope_id="/Users/u/.spec-kitty",
        daemon_root="/Users/u/.spec-kitty",
        queue_db_path="/Users/u/.spec-kitty/queues/queue-aaaaaaaa.db",
        auth_scope="https://app.example.com|u@example.com|t-private",
        server_url="https://app.example.com",
        owner_present=True,
        identity_source=IdentitySource.health_self_report,
        executable_summary="/usr/local/bin/python",
        spawn_shape_ok=True,
        self_report_matches_listener=True,
        is_recorded_singleton=False,
        cleanup_class=CleanupClass.SAFE_AUTO,
        skip_reason=None,
    )


def _make_operator_required_record(port: int = 9405) -> DaemonIdentityRecord:
    """Return a DaemonIdentityRecord with cleanup_class == operator_required."""
    return DaemonIdentityRecord(
        daemon_family="sync",
        pid=None,
        port=port,
        protocol_version=1,
        package_version="3.2.3",
        singleton_scope_id=None,
        daemon_root=None,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
        owner_present=False,
        identity_source=IdentitySource.cmdline_marker,
        executable_summary=None,
        spawn_shape_ok=False,
        self_report_matches_listener=False,
        is_recorded_singleton=False,
        cleanup_class=CleanupClass.OPERATOR_REQUIRED,
        skip_reason=SkipReason.pre_marker,
    )


def _patch_doctor_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    lock_path: Path,
    orphans: list[DaemonIdentityRecord] | None = None,
) -> None:
    """Wire _auth_doctor upstreams to deterministic fakes."""
    session = _make_session()
    monkeypatch.setattr(
        _auth_doctor,
        "get_token_manager",
        lambda: _FakeTokenManager(session),
    )
    monkeypatch.setattr(_auth_doctor, "_refresh_lock_path", lambda: lock_path)

    class _FakeStateFile:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(_auth_doctor, "DAEMON_STATE_FILE", _FakeStateFile())
    monkeypatch.setattr(
        _auth_doctor, "get_sync_daemon_status", lambda: SyncDaemonStatus(healthy=False)
    )

    records = orphans if orphans is not None else []
    monkeypatch.setattr(_auth_doctor, "enumerate_identity_records", lambda: records)

    fake_rollout = type(sys)("specify_cli.saas.rollout")
    fake_rollout.is_saas_sync_enabled = lambda: False  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.saas.rollout", fake_rollout)


# ---------------------------------------------------------------------------
# T022: schema_version == 2 and per-record cleanup_class in --json
# ---------------------------------------------------------------------------


def test_json_schema_version_2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--json`` emits schema_version==2 (FR-004 / T022)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[])

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=False, unstick_lock=False, stuck_threshold=60.0)

    payload = json.loads(output.getvalue())
    assert payload["schema_version"] == 2


def test_json_orphan_record_has_cleanup_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--json`` orphans[] entries include ``cleanup_class`` (FR-004 / T022)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    safe_rec = _make_safe_auto_record(port=9401)
    op_rec = _make_operator_required_record(port=9405)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[safe_rec, op_rec])

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=False, unstick_lock=False, stuck_threshold=60.0)

    payload = json.loads(output.getvalue())
    orphans = payload["orphans"]
    assert len(orphans) == 2

    ports_to_class = {o["port"]: o["cleanup_class"] for o in orphans}
    assert ports_to_class[9401] == "safe_auto"
    assert ports_to_class[9405] == "operator_required"

    # Also verify pre-existing keys are present (back-compat)
    for entry in orphans:
        assert "pid" in entry
        assert "port" in entry
        assert "package_version" in entry
        assert "protocol_version" in entry


def test_json_orphan_record_has_full_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--json`` orphans[] use the full DaemonIdentityRecord.to_dict() (T022)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    rec = _make_safe_auto_record(port=9401)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[rec])

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=False, unstick_lock=False, stuck_threshold=60.0)

    payload = json.loads(output.getvalue())
    orphan = payload["orphans"][0]

    # Fields from DaemonIdentityRecord.to_dict() that were NOT in the old v1 shape
    assert "daemon_family" in orphan
    assert "cleanup_class" in orphan
    assert "skip_reason" in orphan
    assert "identity_source" in orphan
    assert "spawn_shape_ok" in orphan


# ---------------------------------------------------------------------------
# T023: --reset --json emits reset_result with swept/skipped/failed
# ---------------------------------------------------------------------------


def _make_reset_result(
    *,
    swept: list[SweptEntry] | None = None,
    skipped: list[SkippedEntry] | None = None,
    failed: list[FailedEntry] | None = None,
) -> ResetResult:
    return ResetResult(
        swept=swept or [],
        skipped=skipped or [],
        failed=failed or [],
    )


def test_reset_json_has_reset_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--reset --json`` adds a top-level ``reset_result`` object (FR-005 / T023)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    safe_rec = _make_safe_auto_record(port=9401)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[safe_rec])

    swept_entry = SweptEntry(
        pid=5001,
        port=9401,
        package_version="3.2.2",
        protocol_version=1,
        cleanup_path="http_shutdown",
        reason="safe_auto stale-version",
    )
    fake_reset_result = _make_reset_result(swept=[swept_entry])

    monkeypatch.setattr(
        _auth_doctor,
        "reset_orphans",
        lambda records, *, include_operator_required=False: fake_reset_result,
    )
    # Re-scan after reset returns empty
    call_count = {"n": 0}
    original_enumerate = lambda: (  # noqa: E731
        [safe_rec] if call_count["n"] == 0 else []
    )
    monkeypatch.setattr(_auth_doctor, "enumerate_identity_records", original_enumerate)

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0)

    payload = json.loads(output.getvalue())
    assert "reset_result" in payload

    rr = payload["reset_result"]
    assert "swept" in rr
    assert "skipped" in rr
    assert "failed" in rr

    assert len(rr["swept"]) == 1
    assert rr["swept"][0]["port"] == 9401
    assert rr["swept"][0]["cleanup_path"] == "http_shutdown"
    assert rr["swept"][0]["reason"] == "safe_auto stale-version"
    assert len(rr["skipped"]) == 0
    assert len(rr["failed"]) == 0


def test_reset_json_skipped_has_cleanup_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--reset --json`` skipped[] entries carry cleanup_class and skip_reason (T023)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    op_rec = _make_operator_required_record(port=9405)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[op_rec])

    skipped_entry = SkippedEntry(
        pid=None,
        port=9405,
        cleanup_class="operator_required",
        skip_reason="pre_marker",
    )
    fake_reset_result = _make_reset_result(skipped=[skipped_entry])

    monkeypatch.setattr(
        _auth_doctor,
        "reset_orphans",
        lambda records, *, include_operator_required=False: fake_reset_result,
    )

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=True, unstick_lock=False, stuck_threshold=60.0)

    payload = json.loads(output.getvalue())
    skipped = payload["reset_result"]["skipped"]
    assert len(skipped) == 1
    assert skipped[0]["cleanup_class"] == "operator_required"
    assert skipped[0]["skip_reason"] == "pre_marker"
    assert skipped[0]["port"] == 9405


# ---------------------------------------------------------------------------
# T023: default --reset skips operator_required and prints --force hint
# ---------------------------------------------------------------------------


def test_reset_human_prints_force_hint_when_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default ``--reset`` skips operator_required and prints the --force hint (FR-009 / T023)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    op_rec = _make_operator_required_record(port=9405)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[op_rec])

    skipped_entry = SkippedEntry(
        pid=None,
        port=9405,
        cleanup_class="operator_required",
        skip_reason="pre_marker",
    )
    fake_reset_result = _make_reset_result(skipped=[skipped_entry])

    seen_force_arg: list[bool] = []

    def _fake_reset_orphans(
        records: object, *, include_operator_required: bool = False
    ) -> ResetResult:
        seen_force_arg.append(include_operator_required)
        return fake_reset_result

    monkeypatch.setattr(_auth_doctor, "reset_orphans", _fake_reset_orphans)

    doctor_impl(json_output=False, reset=True, force=False, unstick_lock=False, stuck_threshold=60.0)

    captured = capsys.readouterr()
    combined = captured.out + captured.err

    # --force was NOT passed
    assert seen_force_arg == [False]
    # The hint must mention --force
    assert "--force" in combined
    assert "operator_required" in combined


# ---------------------------------------------------------------------------
# T021: --force includes operator_required daemons
# ---------------------------------------------------------------------------


def test_force_flag_passes_include_operator_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--force`` passes ``include_operator_required=True`` to ``reset_orphans`` (T021)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    op_rec = _make_operator_required_record(port=9405)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[op_rec])

    swept_entry = SweptEntry(
        pid=None,
        port=9405,
        package_version="3.2.3",
        protocol_version=1,
        cleanup_path="http_shutdown",
        reason="operator_required stale-version",
    )
    fake_reset_result_with_force = _make_reset_result(swept=[swept_entry])
    seen_args: list[bool] = []

    def _fake_reset_orphans(
        records: object, *, include_operator_required: bool = False
    ) -> ResetResult:
        seen_args.append(include_operator_required)
        return fake_reset_result_with_force

    monkeypatch.setattr(_auth_doctor, "reset_orphans", _fake_reset_orphans)

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    doctor_impl(json_output=True, reset=True, force=True, unstick_lock=False, stuck_threshold=60.0)

    assert seen_args == [True], "reset_orphans must be called with include_operator_required=True"

    payload = json.loads(output.getvalue())
    assert payload["reset_result"]["swept"][0]["port"] == 9405
    assert len(payload["reset_result"]["skipped"]) == 0


def test_force_without_reset_is_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--force`` alone (no ``--reset``) performs no sweep (T021 / T024)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[])

    def _fail_reset_orphans(*args: object, **kwargs: object) -> ResetResult:
        raise AssertionError("reset_orphans must not be called without --reset")

    monkeypatch.setattr(_auth_doctor, "reset_orphans", _fail_reset_orphans)

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    # --force=True but reset=False
    exit_code = doctor_impl(json_output=True, reset=False, force=True, unstick_lock=False, stuck_threshold=60.0)

    # No reset_result in payload
    payload = json.loads(output.getvalue())
    assert "reset_result" not in payload
    assert exit_code == 0


# ---------------------------------------------------------------------------
# T024: plain auth doctor (no --reset) performs no sweep
# ---------------------------------------------------------------------------


def test_no_reset_performs_no_sweep(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Plain ``auth doctor`` without ``--reset`` never calls ``reset_orphans`` (T024)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    safe_rec = _make_safe_auto_record(port=9401)
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[safe_rec])

    def _fail_reset_orphans(*args: object, **kwargs: object) -> ResetResult:
        raise AssertionError("reset_orphans called on read-only path — T024 violation")

    monkeypatch.setattr(_auth_doctor, "reset_orphans", _fail_reset_orphans)

    output = StringIO()
    monkeypatch.setattr("builtins.print", lambda *args, **kw: output.write(str(args[0]) + "\n"))

    # Default read-only invocation
    doctor_impl(json_output=True, reset=False, unstick_lock=False, stuck_threshold=60.0)

    # No reset_result key at all
    payload = json.loads(output.getvalue())
    assert "reset_result" not in payload
    # Orphans still appear in the scan output
    assert len(payload["orphans"]) == 1
    assert payload["orphans"][0]["port"] == 9401


def test_no_reset_no_sweep_human_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Plain ``auth doctor`` (human output) never calls ``reset_orphans`` (T024)."""
    lock_path = tmp_path / "auth" / "refresh.lock"
    _patch_doctor_state(monkeypatch, lock_path=lock_path, orphans=[])

    sweep_called = MagicMock(side_effect=AssertionError("reset_orphans called on read-only path"))
    monkeypatch.setattr(_auth_doctor, "reset_orphans", sweep_called)

    # Should complete without calling reset_orphans
    doctor_impl(json_output=False, reset=False, unstick_lock=False, stuck_threshold=60.0)

    sweep_called.assert_not_called()
