"""WP06 durable delivery-attempt recovery contract."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
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


def _spec(attempt_id: str = "attempt-1") -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=attempt_id,
        write_kind="local_commit",
        native_identity="idempotency:commit-abc",
        payload_hash="sha256:payload",
        payload_reference="local-commit:commit-abc",
        deadline_at="2999-01-01T00:00:00Z",
        reconciliation_policy="native_identity_query",
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
    assert record.reconciliation_policy == "native_identity_query"


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


def test_prepared_recovery_only_resends_when_policy_allows_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-retry",
                write_kind="local_commit",
                native_identity="idempotency:retry",
                payload_hash="sha256:payload",
                payload_reference="local-commit:retry",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-review",
                write_kind="local_commit",
                native_identity="idempotency:review",
                payload_hash="sha256:payload",
                payload_reference="local-commit:review",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="operator_review",
            ),
        )

    with store.unit_of_work() as unit:
        retry = plan_delivery_attempt_recovery(unit, attempt_id="attempt-retry")
        review = plan_delivery_attempt_recovery(unit, attempt_id="attempt-review")

    assert retry.action is RecoveryAction.RETRY_NATIVE_IDENTITY
    assert retry.may_resend is True
    assert review.action is RecoveryAction.OPERATOR_REVIEW
    assert review.may_resend is False


def test_transport_start_deadline_boundary_is_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-deadline-before",
                write_kind="local_commit",
                native_identity="idempotency:deadline-before",
                payload_hash="sha256:payload",
                payload_reference="local-commit:deadline-before",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(
            unit,
            context,
            "attempt-deadline-before",
            now=datetime(2026, 8, 10, 0, 0, 59, tzinfo=UTC),
        )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-deadline-at",
                write_kind="local_commit",
                native_identity="idempotency:deadline-at",
                payload_hash="sha256:payload",
                payload_reference="local-commit:deadline-at",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        with pytest.raises(ProjectStoreError, match="deadline expired"):
            mark_transport_started(
                unit,
                context,
                "attempt-deadline-at",
                now=datetime(2026, 8, 10, 0, 1, 0, tzinfo=UTC),
            )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-deadline-after",
                write_kind="local_commit",
                native_identity="idempotency:deadline-after",
                payload_hash="sha256:payload",
                payload_reference="local-commit:deadline-after",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        with pytest.raises(ProjectStoreError, match="deadline expired"):
            mark_transport_started(
                unit,
                context,
                "attempt-deadline-after",
                now=datetime(2026, 8, 10, 0, 1, 1, tzinfo=UTC),
            )


def test_expired_deadline_blocks_automatic_retry_and_query_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-expired-prepared",
                write_kind="local_commit",
                native_identity="idempotency:expired-prepared",
                payload_hash="sha256:payload",
                payload_reference="local-commit:expired-prepared",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-expired-query",
                write_kind="local_commit",
                native_identity="idempotency:expired-query",
                payload_hash="sha256:payload",
                payload_reference="local-commit:expired-query",
                deadline_at="2026-08-10T00:01:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(
            unit,
            context,
            "attempt-expired-query",
            now=datetime(2026, 8, 10, 0, 0, 59, tzinfo=UTC),
        )

    with store.unit_of_work() as unit:
        prepared = plan_delivery_attempt_recovery(
            unit,
            attempt_id="attempt-expired-prepared",
            now=datetime(2026, 8, 10, 0, 1, 0, tzinfo=UTC),
        )
        query = plan_delivery_attempt_recovery(
            unit,
            attempt_id="attempt-expired-query",
            now=datetime(2026, 8, 10, 0, 1, 1, tzinfo=UTC),
        )

    assert prepared.action is RecoveryAction.OPERATOR_REVIEW
    assert prepared.may_resend is False
    assert query.action is RecoveryAction.OPERATOR_REVIEW
    assert query.may_resend is False


@pytest.mark.parametrize(
    ("attempt_id", "state_transition", "payload_reference", "policy"),
    [
        ("attempt-malformed", "prepared", "{not-json", "native_identity_retry"),
        ("attempt-empty", "prepared", "{}", "native_identity_retry"),
        (
            "attempt-missing-identity",
            "in_flight",
            json.dumps({"write_kind": "local_commit", "payload_reference": "local-commit:missing"}),
            "native_identity_query",
        ),
        ("attempt-invalid-policy", "unknown", "__keep__", "does_not_exist"),
        ("attempt-conflicting-authority", "in_flight", "conflict", "native_identity_query"),
    ],
)
def test_corrupt_recovery_metadata_fails_closed_to_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attempt_id: str,
    state_transition: str,
    payload_reference: str | None,
    policy: str,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id=attempt_id,
                write_kind="local_commit",
                native_identity=f"idempotency:{attempt_id}",
                payload_hash="sha256:payload",
                payload_reference=f"local-commit:{attempt_id}",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query" if state_transition != "prepared" else "native_identity_retry",
            ),
        )
        if state_transition in {"in_flight", "unknown"}:
            mark_transport_started(unit, context, attempt_id)
        if state_transition == "unknown":
            mark_delivery_result_unknown(unit, context, attempt_id=attempt_id, reason="corruption_probe")

    with store.unit_of_work() as unit:
        if payload_reference == "conflict":
            row = unit.execute(
                "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
                (PROJECT_UUID, attempt_id),
            ).fetchone()
            assert row is not None
            metadata = json.loads(str(row[0]))
            metadata["target_generation"] = "999"
            payload_reference = json.dumps(metadata, sort_keys=True)
        if payload_reference == "__keep__":
            unit.execute(
                "UPDATE delivery_attempts SET reconciliation_policy = ? WHERE project_uuid = ? AND attempt_id = ?",
                (policy, PROJECT_UUID, attempt_id),
            )
        else:
            unit.execute(
                "UPDATE delivery_attempts SET payload_reference = ?, reconciliation_policy = ? WHERE project_uuid = ? AND attempt_id = ?",
                (payload_reference, policy, PROJECT_UUID, attempt_id),
            )
        decision = plan_delivery_attempt_recovery(unit, attempt_id=attempt_id)

    assert decision.action is RecoveryAction.OPERATOR_REVIEW
    assert decision.may_resend is False
    assert "operator" in decision.diagnostic


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
