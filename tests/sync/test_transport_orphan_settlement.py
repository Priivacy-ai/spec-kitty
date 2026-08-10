"""WP06 orphan terminalization proof slice."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    prepare_delivery_attempt,
    plan_delivery_attempt_recovery,
    record_delivery_result,
    recover_delivery_attempts,
    settle_attempts_for_opt_out,
    terminalize_orphaned_attempt,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
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
            ),
        )

    with store.unit_of_work() as unit:
        terminalize_orphaned_attempt(unit, attempt_id="attempt-orphan", reason="opt_out_deadline")

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

    with store.unit_of_work() as unit:
        settlement = settle_attempts_for_opt_out(unit, reason="explicit_opt_out")

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
            "SELECT outcome, terminal_refusal_category FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-after-send"),
        ).fetchone()

    assert rows == {
        "attempt-before-send": DeliveryAttemptState.CANCELED.value,
        "attempt-after-send": DeliveryAttemptState.TERMINAL_UNKNOWN.value,
    }
    assert terminal_result == ("terminal_unknown", "explicit_opt_out")


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
        with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
            prepare_delivery_attempt(
                unit,
                context,
                DeliveryAttemptSpec(
                    attempt_id="attempt-killed-after-start",
                    write_kind="local_commit",
                    native_identity="idempotency:killed-after-start",
                    payload_hash="sha256:killed",
                    payload_reference="local-commit:killed",
                ),
            )
            mark_transport_started(unit, context, "attempt-killed-after-start")
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
        },
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 99

    with store.unit_of_work() as unit:
        settlement = settle_attempts_for_opt_out(unit, reason="worker_died_after_start")
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
