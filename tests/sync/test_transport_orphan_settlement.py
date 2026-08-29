"""WP06 orphan terminalization proof slice."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from kernel.clock import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    mark_transport_started,
    prepare_delivery_attempt,
    plan_delivery_attempt_recovery,
    record_delivery_result,
    recover_delivery_attempts,
    settle_attempts_for_opt_out,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_consent_decisions "
            "(project_uuid, state, generation, action, actor, decided_at, decision_schema_version) "
            "VALUES (?, 'granted', 3, 'explicit_opt_in', 'tester', '2026-08-10T00:00:00Z', 1)",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (7, ?, 0, 'eligible', 3, 'opt_in')",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', 'server-generation-1', 'private-teamspace:teamspace-1')",
            (PROJECT_UUID,),
        )
    return store


def test_terminalized_orphan_cannot_later_be_promoted_to_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-orphan",
                write_kind="local_commit",
                native_identity="idempotency:orphan",
                payload_hash="sha256:orphan",
                payload_reference="local-commit:orphan",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, "attempt-orphan", now=datetime(2026, 8, 10, 0, 0, 0, tzinfo=UTC))

    settle_attempts_for_opt_out(store, reason="opt_out_deadline")

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="live or recoverable attempt"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id="late-success",
            attempt_id="attempt-orphan",
            outcome=DeliveryOutcome.DELIVERED,
        )

    with store.unit_of_work() as unit:
        [record] = recover_delivery_attempts(unit)

    assert record.state is DeliveryAttemptState.TERMINAL_UNKNOWN


def test_opt_out_settlement_cancels_prepared_and_terminalizes_started_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-before-send",
                write_kind="event",
                native_identity="event:event-1",
                payload_hash="sha256:event",
                payload_reference="event:event-1",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-after-send",
                write_kind="local_commit",
                native_identity="commit:abc",
                payload_hash="sha256:commit",
                payload_reference="local-commit:abc",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        unit.execute(
            "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ?",
            (
                DeliveryAttemptState.IN_FLIGHT.value,
                PROJECT_UUID,
                "attempt-after-send",
            ),
        )

    settlement = settle_attempts_for_opt_out(store, reason="explicit_opt_out")

    assert settlement.canceled_before_transport == 1
    assert settlement.terminalized_orphans == 1

    with store.unit_of_work() as unit:
        rows = {
            str(row[0]): str(row[1])
            for row in unit.execute(
                "SELECT attempt_id, state FROM delivery_attempts WHERE project_uuid = ?",
                (PROJECT_UUID,),
            )
        }
        terminal_result = unit.execute(
            "SELECT outcome, terminal_refusal_category, target_generation, admission_generation FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-after-send"),
        ).fetchone()

    assert rows == {
        "attempt-before-send": DeliveryAttemptState.CANCELED.value,
        "attempt-after-send": DeliveryAttemptState.TERMINAL_UNKNOWN.value,
    }
    assert terminal_result == (
        "terminal_unknown",
        "explicit_opt_out",
        4,
        "server-generation-1",
    )


def test_process_death_after_transport_start_terminalizes_and_blocks_late_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    script = textwrap.dedent(
        f"""
        import os

        from specify_cli.sync.project_store import ProjectSyncStore
        from specify_cli.sync.transport_attempts import DeliveryAttemptSpec, mark_transport_started, prepare_delivery_attempt
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        store = ProjectSyncStore({PROJECT_UUID!r})
        with acquire_project_transport_lease(store) as lease:
            with lease.unit_of_work() as (unit, context):
                prepare_delivery_attempt(
                    unit,
                    context,
                    DeliveryAttemptSpec(
                        attempt_id="attempt-killed-after-start",
                        write_kind="local_commit",
                        native_identity="idempotency:killed-after-start",
                        payload_hash="sha256:killed",
                        payload_reference="local-commit:killed",
                        deadline_at="2999-01-01T00:00:00Z",
                        reconciliation_policy="native_identity_query",
                    ),
                )
                mark_transport_started(unit, context, "attempt-killed-after-start")
            open({str(tmp_path / "started.barrier")!r}, "w").write("started")
            os._exit(99)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src"),
            "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
            "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        },
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 99

    assert (tmp_path / "started.barrier").read_text() == "started"

    settlement = settle_attempts_for_opt_out(store, reason="worker_died_after_start")
    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-killed-after-start")

    assert settlement.canceled_before_transport == 0
    assert settlement.terminalized_orphans == 1
    assert decision.state is DeliveryAttemptState.TERMINAL_UNKNOWN
    assert decision.native_identity == "idempotency:killed-after-start"
    assert decision.may_resend is False

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="live or recoverable attempt"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id="late-success-after-kill",
            attempt_id="attempt-killed-after-start",
            outcome=DeliveryOutcome.DELIVERED,
        )


@pytest.mark.parametrize(
    ("phase", "expected_state"),
    [
        ("before_attempt_commit", None),
        ("after_attempt_commit_before_send", DeliveryAttemptState.CANCELED.value),
        ("transport_started", DeliveryAttemptState.TERMINAL_UNKNOWN.value),
        ("response_received_before_result", DeliveryAttemptState.TERMINAL_UNKNOWN.value),
        ("result_committed", DeliveryAttemptState.SUCCEEDED.value),
    ],
)
def test_t030_process_death_barriers_cover_named_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    expected_state: str | None,
) -> None:
    store = _store(tmp_path, monkeypatch)
    attempt_id = f"attempt-{phase}"
    barrier = tmp_path / f"{phase}.barrier"
    script = textwrap.dedent(
        f"""
        import os

        from specify_cli.sync.project_store import ProjectSyncStore
        from specify_cli.sync.transport_attempts import (
            DeliveryAttemptSpec,
            DeliveryOutcome,
            mark_delivery_result_unknown,
            mark_transport_started,
            prepare_delivery_attempt,
            record_delivery_result,
        )
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        phase = {phase!r}
        store = ProjectSyncStore({PROJECT_UUID!r})
        with acquire_project_transport_lease(store) as lease:
            if phase == "before_attempt_commit":
                with lease.unit_of_work() as (unit, context):
                    prepare_delivery_attempt(
                        unit,
                        context,
                        DeliveryAttemptSpec(
                            attempt_id={attempt_id!r},
                            write_kind="local_commit",
                            native_identity=f"idempotency:{{phase}}",
                            payload_hash=f"sha256:{{phase}}",
                            payload_reference=f"local-commit:{{phase}}",
                            deadline_at="2999-01-01T00:00:00Z",
                            reconciliation_policy="native_identity_query",
                        ),
                    )
                    open({str(barrier)!r}, "w").write(phase)
                    os._exit(91)
            else:
                with lease.unit_of_work() as (unit, context):
                    prepare_delivery_attempt(
                        unit,
                        context,
                        DeliveryAttemptSpec(
                            attempt_id={attempt_id!r},
                            write_kind="local_commit",
                            native_identity=f"idempotency:{{phase}}",
                            payload_hash=f"sha256:{{phase}}",
                            payload_reference=f"local-commit:{{phase}}",
                            deadline_at="2999-01-01T00:00:00Z",
                            reconciliation_policy="native_identity_query",
                        ),
                    )
                    if phase in {{"transport_started", "response_received_before_result", "result_committed"}}:
                        mark_transport_started(unit, context, {attempt_id!r})
                    if phase == "response_received_before_result":
                        mark_delivery_result_unknown(unit, context, attempt_id={attempt_id!r}, reason=phase)
                    if phase == "result_committed":
                        record_delivery_result(
                            unit,
                            context,
                            result_id=f"result-{{phase}}",
                            attempt_id={attempt_id!r},
                            outcome=DeliveryOutcome.DELIVERED,
                        )
            open({str(barrier)!r}, "w").write(phase)
            os._exit(91)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src"),
            "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
            "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        },
        text=True,
        capture_output=True,
        timeout=5,
    )

    assert result.returncode == 91, result.stderr
    assert barrier.read_text() == phase
    settle_attempts_for_opt_out(store, reason=f"settle_{phase}", lock_timeout_seconds=1)

    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, attempt_id),
        ).fetchone()

    if expected_state is None:
        assert row is None
    else:
        assert row == (expected_state,)


def test_response_unknown_death_immediate_opt_out_late_recovery_is_terminalized_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    barrier = tmp_path / "response-unknown.barrier"
    script = textwrap.dedent(
        f"""
        import os

        from specify_cli.sync.project_store import ProjectSyncStore
        from specify_cli.sync.transport_attempts import (
            DeliveryAttemptSpec,
            mark_delivery_result_unknown,
            mark_transport_started,
            prepare_delivery_attempt,
        )
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        store = ProjectSyncStore({PROJECT_UUID!r})
        with acquire_project_transport_lease(store) as lease:
            with lease.unit_of_work() as (unit, context):
                prepare_delivery_attempt(
                    unit,
                    context,
                    DeliveryAttemptSpec(
                        attempt_id="attempt-compound-response",
                        write_kind="local_commit",
                        native_identity="idempotency:compound-response",
                        payload_hash="sha256:compound-response",
                        payload_reference="local-commit:compound-response",
                        deadline_at="2999-01-01T00:00:00Z",
                        reconciliation_policy="native_identity_query",
                    ),
                )
                mark_transport_started(unit, context, "attempt-compound-response")
                mark_delivery_result_unknown(
                    unit,
                    context,
                    attempt_id="attempt-compound-response",
                    reason="response_received_before_result",
                )
            open({str(barrier)!r}, "w").write("unknown")
            os._exit(92)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src"),
            "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
            "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        },
        text=True,
        capture_output=True,
        timeout=5,
    )

    assert result.returncode == 92, result.stderr
    assert barrier.read_text() == "unknown"
    settlement = settle_attempts_for_opt_out(store, reason="immediate_opt_out")

    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-compound-response")

    assert settlement.terminalized_orphans == 1
    assert decision.state is DeliveryAttemptState.TERMINAL_UNKNOWN
    assert decision.native_identity == "idempotency:compound-response"
    assert decision.action.value == "terminalized_noop"
    assert decision.may_resend is False

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="live or recoverable attempt"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id="late-compound-success",
            attempt_id="attempt-compound-response",
            outcome=DeliveryOutcome.DELIVERED,
        )


def test_opt_out_never_returns_residual_live_inflight_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-live",
                write_kind="local_commit",
                native_identity="idempotency:live",
                payload_hash="sha256:live",
                payload_reference="local-commit:live",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, "attempt-live")

    settlement = settle_attempts_for_opt_out(store, reason="explicit_opt_out")

    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-live"),
        ).fetchone()

    assert settlement.terminalized_orphans == 1
    assert settlement.waiting_live_attempts == 0
    assert row == (DeliveryAttemptState.TERMINAL_UNKNOWN.value,)


@pytest.mark.parametrize("deny_mode", ["consent_refused", "kill_switch_off"])
def test_opt_out_settlement_runs_when_egress_authority_is_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    deny_mode: str,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id=f"attempt-{deny_mode}",
                write_kind="local_commit",
                native_identity=f"idempotency:{deny_mode}",
                payload_hash=f"sha256:{deny_mode}",
                payload_reference=f"local-commit:{deny_mode}",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, f"attempt-{deny_mode}")

    if deny_mode == "consent_refused":
        with store.unit_of_work() as unit:
            unit.execute(
                "UPDATE project_consent_decisions SET state = 'refused', generation = 4, action = 'explicit_opt_out' WHERE project_uuid = ?",
                (PROJECT_UUID,),
            )
    else:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")

    settlement = settle_attempts_for_opt_out(store, reason=deny_mode)

    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, f"attempt-{deny_mode}"),
        ).fetchone()

    assert settlement.terminalized_orphans == 1
    assert row == (DeliveryAttemptState.TERMINAL_UNKNOWN.value,)


def test_opt_out_waits_for_live_holder_genuine_result_before_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    started = tmp_path / "holder-started"
    release = tmp_path / "holder-release"
    script = textwrap.dedent(
        f"""
        import time

        from specify_cli.sync.project_store import ProjectSyncStore
        from specify_cli.sync.transport_attempts import (
            DeliveryAttemptSpec,
            DeliveryOutcome,
            mark_transport_started,
            prepare_delivery_attempt,
            record_delivery_result,
        )
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        store = ProjectSyncStore({PROJECT_UUID!r})
        with acquire_project_transport_lease(store) as lease:
            with lease.unit_of_work() as (unit, context):
                prepare_delivery_attempt(
                    unit,
                    context,
                    DeliveryAttemptSpec(
                        attempt_id="attempt-live-result",
                        write_kind="local_commit",
                        native_identity="idempotency:live-result",
                        payload_hash="sha256:live-result",
                        payload_reference="local-commit:live-result",
                        deadline_at="2999-01-01T00:00:00Z",
                        reconciliation_policy="native_identity_query",
                    ),
                )
                mark_transport_started(unit, context, "attempt-live-result")
            open({str(started)!r}, "w").write("started")
            while not {str(release)!r}:
                time.sleep(0.01)
            while not __import__("pathlib").Path({str(release)!r}).exists():
                time.sleep(0.01)
            with lease.unit_of_work() as (unit, context):
                record_delivery_result(
                    unit,
                    context,
                    result_id="result-live-holder",
                    attempt_id="attempt-live-result",
                    outcome=DeliveryOutcome.DELIVERED,
                )
        """
    )

    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src"),
            "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
            "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    while not started.exists():
        pass
    release.write_text("release")
    settlement = settle_attempts_for_opt_out(store, reason="explicit_opt_out", lock_timeout_seconds=3)
    stdout, stderr = child.communicate(timeout=5)

    assert child.returncode == 0, stdout + stderr
    assert settlement.terminalized_orphans == 0
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-live-result"),
        ).fetchone()
    assert row == (DeliveryAttemptState.SUCCEEDED.value,)


def test_hung_live_holder_opt_out_timeout_fences_even_future_attempt_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    started = tmp_path / "hung-started"
    release = tmp_path / "hung-release"
    child_status = tmp_path / "hung-status"
    script = textwrap.dedent(
        f"""
        import time

        from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
        from specify_cli.sync.transport_attempts import (
            DeliveryAttemptSpec,
            DeliveryOutcome,
            mark_transport_started,
            prepare_delivery_attempt,
            record_delivery_result,
        )
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        store = ProjectSyncStore({PROJECT_UUID!r})
        with acquire_project_transport_lease(store) as lease:
            with lease.unit_of_work() as (unit, context):
                prepare_delivery_attempt(
                    unit,
                    context,
                    DeliveryAttemptSpec(
                        attempt_id="attempt-hung",
                        write_kind="local_commit",
                        native_identity="idempotency:hung",
                        payload_hash="sha256:hung",
                        payload_reference="local-commit:hung",
                        deadline_at="2999-01-01T00:00:00Z",
                        reconciliation_policy="native_identity_query",
                    ),
                )
                mark_transport_started(unit, context, "attempt-hung")
            open({str(started)!r}, "w").write("started")
            while not __import__("pathlib").Path({str(release)!r}).exists():
                time.sleep(0.01)
            try:
                with lease.unit_of_work() as (unit, context):
                    record_delivery_result(
                        unit,
                        context,
                        result_id="late-hung-result",
                        attempt_id="attempt-hung",
                        outcome=DeliveryOutcome.DELIVERED,
                    )
            except ProjectStoreError:
                open({str(child_status)!r}, "w").write("late-result-rejected")
        """
    )

    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src"),
            "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
            "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    while not started.exists():
        pass

    settlement = settle_attempts_for_opt_out(store, reason="hung_deadline", lock_timeout_seconds=0.05)
    release.write_text("release")
    stdout, stderr = child.communicate(timeout=5)

    assert child.returncode == 0, stdout + stderr
    assert settlement.terminalized_orphans == 1
    assert child_status.read_text() == "late-result-rejected"
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-hung"),
        ).fetchone()
    assert row == (DeliveryAttemptState.TERMINAL_UNKNOWN.value,)
