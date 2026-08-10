"""WP06 durable delivery-attempt recovery contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    RecoveryAction,
    mark_delivery_result_unknown,
    mark_transport_started,
    plan_delivery_attempt_recovery,
    prepare_delivery_attempt,
    recover_delivery_attempts,
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


def _spec(attempt_id: str = "attempt-1") -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=attempt_id,
        write_kind="local_commit",
        native_identity="idempotency:commit-abc",
        payload_hash="sha256:payload",
        payload_reference="local-commit:commit-abc",
        deadline_at="2026-08-10T00:01:00Z",
    )


def test_attempt_is_durable_before_transport_and_recovers_native_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepared = prepare_delivery_attempt(unit, context, _spec())

    assert prepared.state is DeliveryAttemptState.PREPARED

    reopened = ProjectSyncStore(PROJECT_UUID)
    with reopened.unit_of_work() as unit:
        [record] = recover_delivery_attempts(unit)

    assert record.attempt_id == "attempt-1"
    assert record.state is DeliveryAttemptState.PREPARED
    assert record.native_identity == "idempotency:commit-abc"
    assert record.payload_hash == "sha256:payload"
    assert record.reconciliation_policy == "native_identity_required"


def test_recovery_decision_uses_original_identity_after_transport_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _spec("attempt-started"))
        mark_transport_started(unit, context, "attempt-started")

    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-started")

    assert decision.state is DeliveryAttemptState.IN_FLIGHT
    assert decision.action is RecoveryAction.QUERY_NATIVE_IDENTITY
    assert decision.native_identity == "idempotency:commit-abc"
    assert decision.may_resend is False


def test_response_received_before_result_is_unknown_and_never_blind_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _spec("attempt-unknown"))
        mark_transport_started(unit, context, "attempt-unknown")
        mark_delivery_result_unknown(unit, context, attempt_id="attempt-unknown", reason="response_before_commit")

    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-unknown")

    assert decision.state is DeliveryAttemptState.UNKNOWN
    assert decision.action is RecoveryAction.QUERY_NATIVE_IDENTITY
    assert decision.native_identity == "idempotency:commit-abc"
    assert decision.may_resend is False
