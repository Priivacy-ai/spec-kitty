"""WP06 durable delivery-attempt recovery contract."""

from __future__ import annotations

import json
from kernel.clock import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    RecoveryAction,
    mark_delivery_result_unknown,
    mark_transport_started,
    list_delivery_attempt_projections,
    plan_delivery_attempt_recovery,
    prepare_delivery_attempt,
    record_delivery_result,
    recover_delivery_attempts,
    restart_delivery_attempt,
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


def _insert_projection_attempt(
    unit: Any,
    *,
    attempt_id: str,
    payload_reference: object,
    state: str = "prepared",
    created_at: str = "2026-08-10T00:00:00Z",
) -> None:
    unit.execute(
        "INSERT INTO delivery_attempts "
        "(attempt_id, project_uuid, epoch_id, consent_generation, target_generation, "
        "admission_generation, binding_audience, payload_hash, payload_reference, "
        "state, deadline_at, reconciliation_policy, created_at) "
        "VALUES (?, ?, 7, 3, 4, 'server-generation-1', "
        "'private-teamspace:teamspace-1', 'sha256:payload', ?, ?, "
        "'2999-01-01T00:00:00Z', 'native_identity_retry', ?)",
        (attempt_id, PROJECT_UUID, payload_reference, state, created_at),
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


def test_public_attempt_projection_exposes_typed_identity_without_sql_tuples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _spec("attempt-projection"))

    with store.unit_of_work() as unit:
        [projection] = list_delivery_attempt_projections(unit)

    assert projection.attempt_id == "attempt-projection"
    assert projection.state is DeliveryAttemptState.PREPARED
    assert projection.write_kind == "local_commit"
    assert projection.event_id is None
    assert projection.target_id is None
    assert projection.created_at is not None


def test_public_attempt_projection_parses_dispatcher_correlation_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    dispatcher_reference = json.dumps(
        {
            "schema": "spec-kitty.dispatcher.v1",
            "event_id": "evt-typed",
            "target_id": "target-typed",
        },
        sort_keys=True,
    )
    dispatcher_metadata = {
        "write_kind": "dispatcher_http_event",
        "payload_reference": dispatcher_reference,
    }
    other_metadata = {
        "write_kind": "body_upload",
        "payload_reference": "body:one",
    }

    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, "
            "state, deadline_at, reconciliation_policy, created_at) "
            "VALUES ('dispatcher-typed', ?, 7, 3, 4, 'server-generation-1', "
            "'private-teamspace:teamspace-1', 'sha256:payload', ?, 'prepared', "
            "'2999-01-01T00:00:00Z', 'native_identity_retry', '2026-08-10T00:00:00Z')",
            (PROJECT_UUID, json.dumps(dispatcher_metadata, sort_keys=True)),
        )
        unit.execute(
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, "
            "state, deadline_at, reconciliation_policy, created_at) "
            "VALUES ('body-typed', ?, 7, 3, 4, 'server-generation-1', "
            "'private-teamspace:teamspace-1', 'sha256:body', ?, 'prepared', "
            "'2999-01-01T00:00:00Z', 'operator_review', '2026-08-10T00:00:01Z')",
            (PROJECT_UUID, json.dumps(other_metadata, sort_keys=True)),
        )
        projections = list_delivery_attempt_projections(unit)

    by_id = {projection.attempt_id: projection for projection in projections}
    assert by_id["dispatcher-typed"].event_id == "evt-typed"
    assert by_id["dispatcher-typed"].target_id == "target-typed"
    assert by_id["body-typed"].event_id is None
    assert by_id["body-typed"].target_id is None

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = 'dispatcher-typed'",
            (
                json.dumps({"write_kind": "dispatcher_http_event", "payload_reference": "{}"}),
                PROJECT_UUID,
            ),
        )
        with pytest.raises(ProjectStoreError, match="dispatcher delivery attempt"):
            list_delivery_attempt_projections(unit)


@pytest.mark.parametrize(
    ("metadata", "message"),
    (
        (None, "metadata is missing"),
        ("{not-json", "metadata is not JSON"),
        (json.dumps(["array-root"]), "metadata must be a JSON object"),
        (json.dumps(7), "metadata must be a JSON object"),
        (json.dumps({}), "requires write_kind or complete legacy event_id/target_id"),
        (json.dumps({"payload_reference": "body:one"}), "requires write_kind or complete legacy event_id/target_id"),
        (json.dumps({"write_kind": 7}), "write_kind must be a non-empty string"),
        (json.dumps({"write_kind": ""}), "write_kind must be a non-empty string"),
        (json.dumps({"event_id": "evt-legacy"}), "target_id must be a non-empty string"),
        (json.dumps({"target_id": "target-legacy"}), "event_id must be a non-empty string"),
        (json.dumps({"event_id": 7, "target_id": "target-legacy"}), "event_id must be a non-empty string"),
        (json.dumps({"event_id": "evt-legacy", "target_id": {"bad": "target"}}), "target_id must be a non-empty string"),
    ),
)
def test_public_attempt_projection_fails_closed_on_corrupt_outer_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: str,
    message: str,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with store.unit_of_work() as unit:
        _insert_projection_attempt(
            unit,
            attempt_id="attempt-corrupt-projection",
            payload_reference=metadata,
        )
        with pytest.raises(ProjectStoreError, match=message):
            list_delivery_attempt_projections(unit)


@pytest.mark.parametrize(
    "metadata",
    (
        json.dumps(
            {
                "payload_reference": json.dumps(
                    {
                        "schema": "spec-kitty.dispatcher.v1",
                        "event_id": "evt-dispatcher",
                        "target_id": "target-dispatcher",
                    }
                )
            },
            sort_keys=True,
        ),
        json.dumps(
            {
                "write_kind": "body_upload",
                "payload_reference": "body:wrong-kind",
            },
            sort_keys=True,
        ),
    ),
)
def test_public_attempt_projection_requires_dispatcher_kind_for_dispatcher_attempt_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: str,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with store.unit_of_work() as unit:
        _insert_projection_attempt(
            unit,
            attempt_id="dispatcher-http:attempt-corrupt-kind",
            payload_reference=metadata,
        )
        with pytest.raises(ProjectStoreError, match="dispatcher_http_event write_kind"):
            list_delivery_attempt_projections(unit)


def test_public_attempt_projection_keeps_valid_controls_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    dispatcher_reference = json.dumps(
        {
            "schema": "spec-kitty.dispatcher.v1",
            "event_id": "evt-dispatcher",
            "target_id": "target-dispatcher",
        },
        sort_keys=True,
    )

    with store.unit_of_work() as unit:
        _insert_projection_attempt(
            unit,
            attempt_id="attempt-dispatcher",
            payload_reference=json.dumps(
                {
                    "write_kind": "dispatcher_http_event",
                    "payload_reference": dispatcher_reference,
                },
                sort_keys=True,
            ),
            created_at="2026-08-10T00:00:00Z",
        )
        _insert_projection_attempt(
            unit,
            attempt_id="attempt-body",
            payload_reference=json.dumps(
                {
                    "write_kind": "body_upload",
                    "payload_reference": "body:valid",
                },
                sort_keys=True,
            ),
            created_at="2026-08-10T00:00:01Z",
        )
        _insert_projection_attempt(
            unit,
            attempt_id="attempt-legacy",
            payload_reference=json.dumps(
                {
                    "event_id": "evt-legacy",
                    "target_id": "target-legacy",
                },
                sort_keys=True,
            ),
            created_at="2026-08-10T00:00:02Z",
        )
        projections = list_delivery_attempt_projections(unit)

    by_id = {projection.attempt_id: projection for projection in projections}
    assert by_id["attempt-dispatcher"].write_kind == "dispatcher_http_event"
    assert by_id["attempt-dispatcher"].event_id == "evt-dispatcher"
    assert by_id["attempt-dispatcher"].target_id == "target-dispatcher"
    assert by_id["attempt-body"].write_kind == "body_upload"
    assert by_id["attempt-body"].event_id is None
    assert by_id["attempt-body"].target_id is None
    assert by_id["attempt-legacy"].write_kind is None
    assert by_id["attempt-legacy"].event_id == "evt-legacy"
    assert by_id["attempt-legacy"].target_id == "target-legacy"
    assert by_id["attempt-legacy"].legacy_metadata == {
        "event_id": "evt-legacy",
        "target_id": "target-legacy",
    }


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


def test_pending_remote_requires_query_and_no_resend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _spec("attempt-pending"))
        mark_transport_started(unit, context, "attempt-pending")
        record_delivery_result(
            unit,
            context,
            result_id="attempt-pending:result",
            attempt_id="attempt-pending",
            outcome=DeliveryOutcome.PENDING,
        )

    with store.unit_of_work() as unit:
        record = recover_delivery_attempts(unit)[0]
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-pending")

    assert record.state is DeliveryAttemptState.PENDING_REMOTE
    assert decision.action is RecoveryAction.QUERY_NATIVE_IDENTITY
    assert decision.native_identity == "idempotency:commit-abc"
    assert decision.may_resend is False


def test_pending_remote_without_query_policy_parks_for_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-dispatcher-pending",
                write_kind="dispatcher_http_event",
                native_identity="dispatcher-http:target:evt-pending",
                payload_hash="sha256:payload",
                payload_reference="dispatcher:evt-pending",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        mark_transport_started(unit, context, "attempt-dispatcher-pending")
        record_delivery_result(
            unit,
            context,
            result_id="attempt-dispatcher-pending:result",
            attempt_id="attempt-dispatcher-pending",
            outcome=DeliveryOutcome.PENDING,
        )

    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-dispatcher-pending")

    assert decision.state is DeliveryAttemptState.PENDING_REMOTE
    assert decision.action is RecoveryAction.OPERATOR_REVIEW
    assert decision.may_resend is False


def test_retryable_no_effect_restarts_same_attempt_under_live_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-no-effect",
                write_kind="local_commit",
                native_identity="idempotency:no-effect",
                payload_hash="sha256:payload",
                payload_reference="local-commit:no-effect",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        mark_transport_started(unit, context, "attempt-no-effect")
        record_delivery_result(
            unit,
            context,
            result_id="attempt-no-effect:result",
            attempt_id="attempt-no-effect",
            outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
        )

    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-no-effect")

    assert decision.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT
    assert decision.action is RecoveryAction.RETRY_NATIVE_IDENTITY
    assert decision.native_identity == "idempotency:no-effect"
    assert decision.may_resend is True

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        restart_delivery_attempt(unit, context, "attempt-no-effect")

    with store.unit_of_work() as unit:
        [record] = recover_delivery_attempts(unit)

    assert record.attempt_id == "attempt-no-effect"
    assert record.state is DeliveryAttemptState.IN_FLIGHT


def test_retryable_no_effect_cannot_record_success_without_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-direct-promotion",
                write_kind="local_commit",
                native_identity="idempotency:direct-promotion",
                payload_hash="sha256:payload",
                payload_reference="local-commit:direct-promotion",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_retry",
            ),
        )
        mark_transport_started(unit, context, "attempt-direct-promotion")
        record_delivery_result(
            unit,
            context,
            result_id="attempt-direct-promotion:result",
            attempt_id="attempt-direct-promotion",
            outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
        )
        with pytest.raises(ProjectStoreError, match="live or recoverable attempt"):
            record_delivery_result(
                unit,
                context,
                result_id="attempt-direct-promotion:result",
                attempt_id="attempt-direct-promotion",
                outcome=DeliveryOutcome.DELIVERED,
            )

    with store.unit_of_work() as unit:
        [record] = recover_delivery_attempts(unit)

    assert record.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT


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
        ("attempt-array-native", "in_flight", ("native_identity", []), "native_identity_query"),
        ("attempt-object-write-kind", "in_flight", ("write_kind", {"kind": "local_commit"}), "native_identity_query"),
        ("attempt-object-payload", "unknown", ("payload_reference", {"ref": "local-commit"}), "native_identity_query"),
        ("attempt-number-generation", "prepared", ("target_generation", 4), "native_identity_retry"),
        ("attempt-array-audience", "unknown", ("binding_audience", ["private-teamspace"]), "native_identity_query"),
        ("attempt-bool-deadline", "in_flight", ("deadline_at", False), "native_identity_query"),
        ("attempt-number-policy", "in_flight", ("reconciliation_policy", 1), "native_identity_query"),
    ],
)
def test_corrupt_recovery_metadata_fails_closed_to_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attempt_id: str,
    state_transition: str,
    payload_reference: str | tuple[str, object] | None,
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
        elif isinstance(payload_reference, tuple):
            row = unit.execute(
                "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
                (PROJECT_UUID, attempt_id),
            ).fetchone()
            assert row is not None
            metadata = json.loads(str(row[0]))
            field, malformed_value = payload_reference
            metadata[field] = malformed_value
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
    if attempt_id == "attempt-array-native":
        assert decision.native_identity is None


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
