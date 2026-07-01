"""Unit tests for WP03: port-scan classification and structured ResetResult.

Covers T011–T015:
- T011: ``enumerate_identity_records`` builds a full ``DaemonIdentityRecord``
        with correct ``cleanup_class`` per in-range listener.
- T012: In-range + daemon-family hard guard prevents sweeps of out-of-range or
        ``never_touch`` records (NFR-001, C-002, C-004).
- T013: ``ResetResult`` carries exact per-entry fields including ``cleanup_path``
        (``http_shutdown`` | ``terminate`` | ``kill``).
- T014: Default sweep skips ``operator_required``; force flag attempts it.
- T015: Tests are subprocess-free and mock-light (fake health + fake PID doubles).

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.classification import (
    CandidateProbe,
    CleanupClass,
    DaemonIdentityRecord,
    ForegroundScope,
    HealthProbe,
    IdentitySource,
    SingletonRef,
    SkipReason,
    classify_candidate,
)
from specify_cli.sync.orphan_sweep import (
    FailedEntry,
    ResetResult,
    SkippedEntry,
    SweptEntry,
    _assert_safe_to_sweep,
    _build_health_probe,
    reset_orphans,
)

# Module-level marker so the CI gate-coverage selector picks these pure unit
# tests up (every test file must declare a module-level ``pytestmark``).
pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Shared constants and builder helpers
# ---------------------------------------------------------------------------

_SCOPE = "/Users/alice/.spec-kitty"
_OTHER_SCOPE = "/Users/bob/.spec-kitty"
_SINGLETON_PID = 9000
_SINGLETON_PORT = 9400
_ORPHAN_PID = 9001
_ORPHAN_PORT = 9401


def _foreground(
    scope_id: str = _SCOPE,
    singleton_pid: int | None = _SINGLETON_PID,
    singleton_port: int | None = _SINGLETON_PORT,
) -> ForegroundScope:
    return ForegroundScope(
        scope_id=scope_id,
        executable_scope="/usr/bin/python3",
        singleton=SingletonRef(pid=singleton_pid, port=singleton_port),
    )


def _health_probe(
    *,
    responded: bool = True,
    owner_pid: int | None = _ORPHAN_PID,
    owner_port: int | None = _ORPHAN_PORT,
    package_version: str | None = "3.2.2",
    protocol_version: int | None = 1,
    daemon_family: str | None = "sync",
) -> HealthProbe:
    return HealthProbe(
        responded=responded,
        status="ok" if responded else None,
        protocol_version=protocol_version,
        package_version=package_version,
        daemon_family=daemon_family,
        owner_pid=owner_pid,
        owner_port=owner_port,
        queue_db_path="/Users/alice/.spec-kitty/queues/queue-test.db",
        auth_scope="https://api.example.com|alice@example.com|t-private",
        server_url="https://api.example.com",
    )


def _probe(
    *,
    port: int = _ORPHAN_PORT,
    listener_pid: int | None = _ORPHAN_PID,
    health: HealthProbe | None = None,
    singleton_scope_id: str | None = _SCOPE,
    spawn_shape_ok: bool = True,
    executable_summary: str | None = "/usr/bin/python3",
    owner_present: bool = False,
) -> CandidateProbe:
    return CandidateProbe(
        port=port,
        listener_pid=listener_pid,
        health=health,
        singleton_scope_id=singleton_scope_id,
        spawn_shape_ok=spawn_shape_ok,
        executable_summary=executable_summary,
        owner_present=owner_present,
    )


def _safe_auto_record(port: int = _ORPHAN_PORT, pid: int = _ORPHAN_PID) -> DaemonIdentityRecord:
    """Build a ``safe_auto`` classified record for use in sweep tests."""
    health = _health_probe(owner_pid=pid, owner_port=port)
    p = _probe(port=port, listener_pid=pid, health=health)
    return classify_candidate(p, _foreground())


def _operator_required_record(port: int = _ORPHAN_PORT, pid: int = _ORPHAN_PID) -> DaemonIdentityRecord:
    """Build an ``operator_required`` classified record (wedged / unresponsive)."""
    p = _probe(port=port, listener_pid=pid, health=None)
    return classify_candidate(p, _foreground())


def _never_touch_record(port: int = 9999) -> DaemonIdentityRecord:
    """Build a ``never_touch`` record (out-of-range port)."""
    p = _probe(
        port=port,
        listener_pid=None,
        health=None,
        singleton_scope_id=None,
        spawn_shape_ok=False,
        executable_summary=None,
    )
    return classify_candidate(p, _foreground())


# ---------------------------------------------------------------------------
# T011 — Record built with correct cleanup_class
# ---------------------------------------------------------------------------


class TestT011RecordClassification:
    """T011: ``classify_candidate`` produces the correct ``cleanup_class`` for
    each scenario exercised through the WP03 scan path."""

    def test_safe_auto_record(self) -> None:
        """Same scope + responsive health + spawn shape → safe_auto."""
        record = _safe_auto_record()
        assert record.cleanup_class == CleanupClass.SAFE_AUTO
        assert record.skip_reason is None
        assert record.daemon_family == "sync"
        assert record.port == _ORPHAN_PORT
        assert record.pid == _ORPHAN_PID

    def test_operator_required_unresponsive(self) -> None:
        """Wedged listener (health=None) → operator_required / unresponsive (D-01)."""
        record = _operator_required_record()
        assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
        assert record.skip_reason == SkipReason.unresponsive

    def test_operator_required_missing_pid(self) -> None:
        """Missing PID → operator_required / missing_pid."""
        health = _health_probe(owner_pid=None, owner_port=_ORPHAN_PORT)
        p = _probe(port=_ORPHAN_PORT, listener_pid=None, health=health)
        record = classify_candidate(p, _foreground())
        assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
        assert record.skip_reason == SkipReason.missing_pid

    def test_operator_required_pre_marker(self) -> None:
        """No daemon-root marker → operator_required / pre_marker."""
        health = _health_probe()
        p = _probe(port=_ORPHAN_PORT, health=health, singleton_scope_id=None)
        record = classify_candidate(p, _foreground())
        assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
        assert record.skip_reason == SkipReason.pre_marker

    def test_operator_required_cross_root(self) -> None:
        """Marker belongs to different scope → operator_required / cross_root."""
        health = _health_probe()
        p = _probe(port=_ORPHAN_PORT, health=health, singleton_scope_id=_OTHER_SCOPE)
        record = classify_candidate(p, _foreground())
        assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
        assert record.skip_reason == SkipReason.cross_root

    def test_never_touch_out_of_range(self) -> None:
        """Out-of-range port → never_touch / out_of_range."""
        record = _never_touch_record(port=9999)
        assert record.cleanup_class == CleanupClass.NEVER_TOUCH
        assert record.skip_reason == SkipReason.out_of_range

    def test_never_touch_below_range(self) -> None:
        """Port below 9400 → never_touch / out_of_range."""
        record = _never_touch_record(port=9399)
        assert record.cleanup_class == CleanupClass.NEVER_TOUCH
        assert record.skip_reason == SkipReason.out_of_range

    def test_safe_auto_stale_version_allowed(self) -> None:
        """Version mismatch is evidence, not a gate — still safe_auto (FR-008)."""
        health = _health_probe(package_version="2.0.0")
        p = _probe(port=_ORPHAN_PORT, health=health)
        record = classify_candidate(p, _foreground())
        assert record.cleanup_class == CleanupClass.SAFE_AUTO
        assert record.skip_reason is None

    def test_identity_source_populated(self) -> None:
        """safe_auto records report health_self_report as identity source."""
        record = _safe_auto_record()
        assert record.identity_source == IdentitySource.health_self_report

    def test_daemon_family_sync(self) -> None:
        """All records in range carry daemon_family='sync'."""
        record = _safe_auto_record()
        assert record.daemon_family == "sync"


# ---------------------------------------------------------------------------
# T011 — _build_health_probe helper
# ---------------------------------------------------------------------------


class TestBuildHealthProbe:
    """Test the ``_build_health_probe`` helper that converts raw payloads."""

    def test_none_payload_responds_false(self) -> None:
        """``None`` payload → ``responded=False`` (wedged listener)."""
        probe = _build_health_probe(None, port=9401, pid=None)
        assert probe.responded is False
        assert probe.protocol_version is None
        assert probe.package_version is None

    def test_valid_payload_parsed(self) -> None:
        """Valid health payload → fully populated ``HealthProbe``."""
        payload: dict[str, Any] = {
            "status": "ok",
            "protocol_version": 1,
            "package_version": "3.2.2",
            "daemon_family": "sync",
            "owner": {"pid": 9001, "port": 9401},
        }
        probe = _build_health_probe(payload, port=9401, pid=9001)
        assert probe.responded is True
        assert probe.protocol_version == 1
        assert probe.package_version == "3.2.2"
        assert probe.daemon_family == "sync"
        assert probe.owner_pid == 9001
        assert probe.owner_port == 9401

    def test_missing_owner_block_preserves_unknown_pid_port(self) -> None:
        """Missing daemon-local owner identity stays unknown; callers do not fabricate it."""
        payload: dict[str, Any] = {
            "protocol_version": 1,
            "package_version": "3.2.2",
        }
        probe = _build_health_probe(payload, port=9401, pid=5001)
        assert probe.owner_pid is None
        assert probe.owner_port is None


# ---------------------------------------------------------------------------
# T012 — In-range / family guard (NFR-001, C-002, C-004)
# ---------------------------------------------------------------------------


class TestT012InRangeGuard:
    """T012: ``_assert_safe_to_sweep`` raises RuntimeError for unsafe records."""

    def test_safe_auto_in_range_passes(self) -> None:
        """``safe_auto`` in-range record passes the guard without raising."""
        record = _safe_auto_record(port=9401)
        # Should not raise.
        _assert_safe_to_sweep(record)

    def test_operator_required_in_range_passes(self) -> None:
        """``operator_required`` in-range record passes guard (checked before sweep)."""
        record = _operator_required_record(port=9401)
        _assert_safe_to_sweep(record)

    def test_out_of_range_port_raises(self) -> None:
        """Out-of-range port → ``RuntimeError`` (NFR-001)."""
        # Build a fake record with an out-of-range port by constructing directly.
        record = DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9999,
            protocol_version=1,
            package_version="3.2.2",
            singleton_scope_id=_SCOPE,
            daemon_root=_SCOPE,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=True,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.SAFE_AUTO,
            skip_reason=None,
        )
        with pytest.raises(RuntimeError, match="out-of-range port"):
            _assert_safe_to_sweep(record)

    def test_non_sync_family_raises(self) -> None:
        """Non-sync daemon_family → ``RuntimeError`` (C-002)."""
        record = DaemonIdentityRecord(
            daemon_family="dashboard",
            pid=9001,
            port=9401,
            protocol_version=1,
            package_version="3.2.2",
            singleton_scope_id=_SCOPE,
            daemon_root=_SCOPE,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=True,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.SAFE_AUTO,
            skip_reason=None,
        )
        with pytest.raises(RuntimeError, match="non-sync daemon_family"):
            _assert_safe_to_sweep(record)

    def test_never_touch_record_raises(self) -> None:
        """``never_touch`` cleanup_class → ``RuntimeError`` (C-004)."""
        record = _never_touch_record(port=9999)
        # Port is also out of range here — either guard fires; RuntimeError required.
        with pytest.raises(RuntimeError):
            _assert_safe_to_sweep(record)

    def test_never_touch_in_range_raises(self) -> None:
        """``never_touch`` in-range port → ``RuntimeError`` (C-004 still applies)."""
        # Construct a never_touch record with an in-range port directly.
        record = DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9401,
            protocol_version=None,
            package_version=None,
            singleton_scope_id=None,
            daemon_root=None,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.none,
            executable_summary=None,
            spawn_shape_ok=False,
            self_report_matches_listener=False,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.NEVER_TOUCH,
            skip_reason=SkipReason.not_spec_kitty,
        )
        with pytest.raises(RuntimeError, match="never_touch"):
            _assert_safe_to_sweep(record)


# ---------------------------------------------------------------------------
# T013 — ResetResult shape and cleanup_path
# ---------------------------------------------------------------------------


class TestT013ResetResultShape:
    """T013: ``reset_orphans`` populates ``swept``/``skipped``/``failed`` with
    per-entry fields including ``cleanup_path``."""

    def _mock_sweep_http_success(self) -> MagicMock:
        """Patch ``_sweep_one_with_path`` to simulate HTTP shutdown success."""
        mock = MagicMock(return_value=(True, "http_shutdown", None))
        return mock

    def test_swept_entry_fields_on_http_success(self) -> None:
        """Successful HTTP shutdown → ``SweptEntry`` with ``cleanup_path='http_shutdown'``."""
        record = _safe_auto_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "http_shutdown", None),
        ):
            result = reset_orphans([record])

        assert len(result.swept) == 1
        entry = result.swept[0]
        assert isinstance(entry, SweptEntry)
        assert entry.port == _ORPHAN_PORT
        assert entry.pid == _ORPHAN_PID
        assert entry.cleanup_path == "http_shutdown"
        assert entry.package_version == "3.2.2"
        assert entry.protocol_version == 1
        assert entry.reason  # non-empty reason string

    def test_swept_entry_cleanup_path_terminate(self) -> None:
        """Terminate escalation → ``cleanup_path='terminate'``."""
        record = _safe_auto_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "terminate", None),
        ):
            result = reset_orphans([record])

        assert result.swept[0].cleanup_path == "terminate"

    def test_swept_entry_cleanup_path_kill(self) -> None:
        """Kill escalation → ``cleanup_path='kill'``."""
        record = _safe_auto_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "kill", None),
        ):
            result = reset_orphans([record])

        assert result.swept[0].cleanup_path == "kill"

    def test_failed_entry_on_sweep_failure(self) -> None:
        """Failed sweep → ``FailedEntry`` with ``failure_reason``."""
        record = _safe_auto_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(False, "kill", "port_still_listening_after_kill"),
        ):
            result = reset_orphans([record])

        assert len(result.failed) == 1
        entry = result.failed[0]
        assert isinstance(entry, FailedEntry)
        assert entry.port == _ORPHAN_PORT
        assert entry.pid == _ORPHAN_PID
        assert "kill" in entry.failure_reason or "listening" in entry.failure_reason

    def test_empty_input_produces_empty_result(self) -> None:
        """Empty input list → all arrays empty."""
        result = reset_orphans([])
        assert result.swept == []
        assert result.skipped == []
        assert result.failed == []

    def test_reset_result_is_frozen(self) -> None:
        """``ResetResult`` fields are immutable (frozen dataclass)."""
        result = ResetResult()
        with pytest.raises((AttributeError, TypeError)):
            result.swept = []  # type: ignore[misc]  # frozen dataclass: deliberate mutation asserts FrozenInstanceError at runtime

    def test_skipped_entry_fields(self) -> None:
        """Skipped ``operator_required`` entry carries ``cleanup_class`` and ``skip_reason``."""
        record = _operator_required_record()
        result = reset_orphans([record], include_operator_required=False)

        assert len(result.skipped) == 1
        entry = result.skipped[0]
        assert isinstance(entry, SkippedEntry)
        assert entry.port == _ORPHAN_PORT
        assert entry.pid == _ORPHAN_PID
        assert entry.cleanup_class == "operator_required"
        assert entry.skip_reason == "unresponsive"


# ---------------------------------------------------------------------------
# T014 — Force-aware sweep (D-02)
# ---------------------------------------------------------------------------


class TestT014ForceAwareSweep:
    """T014: Default skips ``operator_required``; force flag attempts it."""

    def test_default_skips_operator_required(self) -> None:
        """Without force, ``operator_required`` records land in ``skipped``."""
        record = _operator_required_record()
        result = reset_orphans([record], include_operator_required=False)

        assert result.swept == []
        assert result.failed == []
        assert len(result.skipped) == 1
        assert result.skipped[0].cleanup_class == "operator_required"

    def test_force_attempts_operator_required_success(self) -> None:
        """With force and successful sweep, ``operator_required`` moves to ``swept``."""
        record = _operator_required_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "http_shutdown", None),
        ):
            result = reset_orphans([record], include_operator_required=True)

        assert result.skipped == []
        assert len(result.swept) == 1
        assert result.swept[0].port == _ORPHAN_PORT

    def test_force_attempts_operator_required_failure(self) -> None:
        """With force and failed sweep, ``operator_required`` moves to ``failed``."""
        record = _operator_required_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(False, "kill", "port_still_listening_after_kill"),
        ):
            result = reset_orphans([record], include_operator_required=True)

        assert result.skipped == []
        assert len(result.failed) == 1
        assert result.failed[0].port == _ORPHAN_PORT

    def test_safe_auto_always_swept_regardless_of_force_flag(self) -> None:
        """``safe_auto`` records are swept whether force is True or False."""
        record = _safe_auto_record()
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "http_shutdown", None),
        ):
            for include_force in (False, True):
                result = reset_orphans([record], include_operator_required=include_force)
                assert len(result.swept) == 1, f"Expected swept with force={include_force}"

    def test_mixed_records_default(self) -> None:
        """Mix of safe_auto + operator_required: safe swept, operator skipped."""
        safe = _safe_auto_record(port=9401)
        op_req = _operator_required_record(port=9402)
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "http_shutdown", None),
        ):
            result = reset_orphans([safe, op_req], include_operator_required=False)

        assert len(result.swept) == 1
        assert result.swept[0].port == 9401
        assert len(result.skipped) == 1
        assert result.skipped[0].port == 9402
        assert result.failed == []

    def test_mixed_records_force(self) -> None:
        """Mix of safe_auto + operator_required with force: both swept."""
        safe = _safe_auto_record(port=9401)
        op_req = _operator_required_record(port=9402)
        with patch(
            "specify_cli.sync.orphan_sweep._sweep_one_with_path",
            return_value=(True, "terminate", None),
        ):
            result = reset_orphans([safe, op_req], include_operator_required=True)

        assert len(result.swept) == 2
        ports = {e.port for e in result.swept}
        assert ports == {9401, 9402}
        assert result.skipped == []

    def test_never_touch_records_not_swept(self) -> None:
        """``never_touch`` records passed to ``reset_orphans`` are silently skipped."""
        record = DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9401,
            protocol_version=None,
            package_version=None,
            singleton_scope_id=None,
            daemon_root=None,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.none,
            executable_summary=None,
            spawn_shape_ok=False,
            self_report_matches_listener=False,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.NEVER_TOUCH,
            skip_reason=SkipReason.not_spec_kitty,
        )
        # Must not raise; never_touch is silently dropped.
        result = reset_orphans([record])
        assert result.swept == []
        assert result.skipped == []
        assert result.failed == []


# ---------------------------------------------------------------------------
# T015 — Guard integration: out-of-range / never_touch never reach sweep call
# ---------------------------------------------------------------------------


class TestT015GuardIntegration:
    """T015: Guard prevents any _sweep_daemon_process call for unsafe records."""

    def test_guard_blocks_out_of_range_before_signal(self) -> None:
        """Out-of-range record never reaches the signal step (RuntimeError)."""
        bad_record = DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9999,
            protocol_version=1,
            package_version="3.2.2",
            singleton_scope_id=_SCOPE,
            daemon_root=_SCOPE,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=True,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.SAFE_AUTO,
            skip_reason=None,
        )
        # Directly calling _assert_safe_to_sweep should raise before any I/O.
        with pytest.raises(RuntimeError, match="out-of-range port"):
            _assert_safe_to_sweep(bad_record)

    def test_guard_blocks_wrong_family_before_signal(self) -> None:
        """Non-sync family record never reaches the signal step (RuntimeError)."""
        bad_record = DaemonIdentityRecord(
            daemon_family="dashboard",
            pid=9001,
            port=9401,
            protocol_version=1,
            package_version="3.2.2",
            singleton_scope_id=_SCOPE,
            daemon_root=_SCOPE,
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=True,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=CleanupClass.SAFE_AUTO,
            skip_reason=None,
        )
        with pytest.raises(RuntimeError, match="non-sync daemon_family"):
            _assert_safe_to_sweep(bad_record)

    def test_reset_orphans_calls_classify_candidate_for_safe_auto(self) -> None:
        """``reset_orphans`` calls the sweep path only for safe_auto records."""
        safe = _safe_auto_record()
        sweep_calls: list[int] = []

        def fake_sweep(rec: DaemonIdentityRecord) -> tuple[bool, str, None]:
            sweep_calls.append(rec.port)
            return (True, "http_shutdown", None)

        with patch("specify_cli.sync.orphan_sweep._sweep_one_with_path", side_effect=fake_sweep):
            result = reset_orphans([safe])

        assert sweep_calls == [_ORPHAN_PORT]
        assert len(result.swept) == 1
