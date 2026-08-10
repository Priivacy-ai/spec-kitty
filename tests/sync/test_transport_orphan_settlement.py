"""WP06 orphan terminalization proof slice."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    prepare_delivery_attempt,
    record_delivery_result,
    recover_delivery_attempts,
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
            "INSERT INTO consent_epochs "
            "(epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) "
            "VALUES (7, ?, 0, 'eligible', 3, 'opt_in')",
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
