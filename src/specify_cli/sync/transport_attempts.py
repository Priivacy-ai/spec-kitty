"""Durable delivery-attempt protocol for project-scoped hosted-sync writes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from specify_cli.sync.project_context import ProjectSyncContext, validate_project_sync_context_authority
from specify_cli.sync.project_store import ProjectStoreError, ProjectUnitOfWork


class DeliveryAttemptState(StrEnum):
    """Durable states with explicit uncertainty and irreversible orphan handling."""

    PREPARED = "prepared"
    IN_FLIGHT = "in_flight"
    UNKNOWN = "unknown"
    TERMINAL_UNKNOWN = "terminal_unknown"
    SUCCEEDED = "succeeded"
    REFUSED = "refused"
    CANCELED = "canceled"


class DeliveryOutcome(StrEnum):
    """Truthful terminal result classes recorded under the transport lease."""

    DELIVERED = "delivered"
    REFUSED = "refused"
    UNKNOWN = "unknown"
    TERMINAL_UNKNOWN = "terminal_unknown"


class RecoveryAction(StrEnum):
    """Adapter-neutral recovery action for one durable attempt."""

    QUERY_NATIVE_IDENTITY = "query_native_identity"
    RETRY_NATIVE_IDENTITY = "retry_native_identity"
    TERMINALIZED_NOOP = "terminalized_noop"
    OPERATOR_REVIEW = "operator_review"


@dataclass(frozen=True, slots=True)
class DeliveryAttemptSpec:
    """Adapter-neutral immutable identity for a possible remote disclosure."""

    attempt_id: str
    write_kind: str
    native_identity: str
    payload_hash: str
    payload_reference: str
    outbox_task_id: str | None = None
    deadline_at: str | None = None
    reconciliation_policy: str = "native_identity_required"


@dataclass(frozen=True, slots=True)
class DeliveryAttemptRecord:
    """Recovered durable attempt row."""

    attempt_id: str
    state: DeliveryAttemptState
    native_identity: str | None
    payload_hash: str | None
    reconciliation_policy: str | None


@dataclass(frozen=True, slots=True)
class OptOutSettlement:
    """Counts for one opt-out settlement pass over durable attempts."""

    canceled_before_transport: int
    terminalized_orphans: int


@dataclass(frozen=True, slots=True)
class DeliveryRecoveryDecision:
    """Recovery decision that never invents a fresh disclosure identity."""

    attempt_id: str
    state: DeliveryAttemptState
    action: RecoveryAction
    native_identity: str | None
    may_resend: bool
    diagnostic: str


def prepare_delivery_attempt(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    spec: DeliveryAttemptSpec,
) -> DeliveryAttemptRecord:
    """Persist an attempt before network I/O using the active project unit."""
    _validate_context_for_unit(unit, context, require_lease=False)
    if context.consent_generation is None or context.epoch_id is None:
        raise ProjectStoreError("delivery attempt requires a consenting project epoch")
    if context.target_audience is None or context.admission_generation is None or context.binding_audience is None:
        raise ProjectStoreError("delivery attempt requires an admitted target audience")
    _require_non_empty(
        attempt_id=spec.attempt_id,
        write_kind=spec.write_kind,
        native_identity=spec.native_identity,
        payload_hash=spec.payload_hash,
        reconciliation_policy=spec.reconciliation_policy,
    )
    metadata = _attempt_metadata(spec)
    # TODO(#3262/WP06 follow-up): the existing project-store schema has only the
    # payload_reference text slot for native attempt metadata. This keeps the
    # current WP adapter-neutral and durable without a migration, but a later
    # schema-hardening WP should normalize native_identity/write_kind into first
    # class columns before adapters depend on query-heavy recovery.
    unit.execute(
        "INSERT INTO delivery_attempts "
        "(attempt_id, project_uuid, epoch_id, outbox_task_id, consent_generation, "
        "target_generation, admission_generation, binding_audience, payload_hash, "
        "payload_reference, state, deadline_at, reconciliation_policy, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            spec.attempt_id,
            unit.project_uuid.storage_token,
            context.epoch_id,
            spec.outbox_task_id,
            context.consent_generation,
            context.target_audience.configuration_generation,
            context.admission_generation,
            context.binding_audience,
            spec.payload_hash,
            json.dumps(metadata, sort_keys=True),
            DeliveryAttemptState.PREPARED.value,
            spec.deadline_at,
            spec.reconciliation_policy,
            _now(),
        ),
    )
    return DeliveryAttemptRecord(
        attempt_id=spec.attempt_id,
        state=DeliveryAttemptState.PREPARED,
        native_identity=spec.native_identity,
        payload_hash=spec.payload_hash,
        reconciliation_policy=spec.reconciliation_policy,
    )


def mark_transport_started(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    attempt_id: str,
) -> None:
    """Move a prepared attempt to in-flight immediately before I/O."""
    _validate_context_for_unit(unit, context, require_lease=True)
    row = unit.execute(
        "SELECT 1 FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state = ?",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.PREPARED.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt was not prepared for transport start")
    unit.execute(
        "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ? AND state = ?",
        (
            DeliveryAttemptState.IN_FLIGHT.value,
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.PREPARED.value,
        ),
    )


def mark_delivery_result_unknown(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    attempt_id: str,
    reason: str,
) -> None:
    """Park response/result uncertainty without recording a false success.

    This represents the T030 ``response_received_before_result`` window: a
    worker observed enough to know the attempt is no longer safely unstarted,
    but crashed or lost authority before a genuine final result could be
    committed.  Recovery may inspect the same native identity later; opt-out may
    terminalize it first.
    """
    _validate_context_for_unit(unit, context, require_lease=True)
    _require_non_empty(attempt_id=attempt_id, reason=reason)
    row = unit.execute(
        "SELECT 1 FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("unknown result requires a started attempt")
    unit.execute(
        "UPDATE delivery_attempts SET state = ?, reconciliation_policy = ? WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?)",
        (
            DeliveryAttemptState.UNKNOWN.value,
            f"unknown:{reason}",
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    )


def record_delivery_result(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    result_id: str,
    attempt_id: str,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None = None,
) -> None:
    """Record a genuine transport result only while holding the project lease."""
    _validate_context_for_unit(unit, context, require_lease=True)
    if outcome is DeliveryOutcome.DELIVERED:
        terminal_state = DeliveryAttemptState.SUCCEEDED
    elif outcome is DeliveryOutcome.REFUSED:
        terminal_state = DeliveryAttemptState.REFUSED
    else:
        terminal_state = DeliveryAttemptState.UNKNOWN
    row = unit.execute(
        "SELECT epoch_id FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery result requires a live or recoverable attempt")
    unit.execute(
        "INSERT INTO delivery_results "
        "(result_id, project_uuid, epoch_id, attempt_id, target_generation, "
        "admission_generation, outcome, terminal_refusal_category, recorded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            result_id,
            unit.project_uuid.storage_token,
            int(row[0]),
            attempt_id,
            context.target_audience.configuration_generation if context.target_audience is not None else None,
            context.admission_generation,
            outcome.value,
            terminal_refusal_category,
            _now(),
        ),
    )
    unit.execute(
        "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ?",
        (terminal_state.value, unit.project_uuid.storage_token, attempt_id),
    )


def plan_delivery_attempt_recovery(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
) -> DeliveryRecoveryDecision:
    """Return the only safe adapter-neutral recovery action for an attempt.

    The decision deliberately carries the original native identity and a
    ``may_resend`` boolean instead of invoking transport adapters.  WP07/WP08
    can map this to their native protocols, but a terminalized orphan is always
    a no-op here: recovery may attach diagnostics later, never promote success
    and never mint/resend a fresh identity.
    """
    _require_non_empty(attempt_id=attempt_id)
    row = unit.execute(
        "SELECT state, payload_reference, reconciliation_policy FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt does not exist")
    state = DeliveryAttemptState(str(row[0]))
    metadata = _metadata_from_payload_reference(row[1])
    native_identity = metadata.get("native_identity")
    if state is DeliveryAttemptState.TERMINAL_UNKNOWN:
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.TERMINALIZED_NOOP,
            native_identity=native_identity,
            may_resend=False,
            diagnostic="attempt was terminalized during opt-out; preserve diagnostics only",
        )
    if state is DeliveryAttemptState.PREPARED:
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.RETRY_NATIVE_IDENTITY,
            native_identity=native_identity,
            may_resend=True,
            diagnostic="attempt was durable before transport; retry only with the original native identity",
        )
    if state in {DeliveryAttemptState.IN_FLIGHT, DeliveryAttemptState.UNKNOWN}:
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.QUERY_NATIVE_IDENTITY,
            native_identity=native_identity,
            may_resend=False,
            diagnostic="transport may have disclosed payload; query/reconcile original native identity only",
        )
    return DeliveryRecoveryDecision(
        attempt_id=attempt_id,
        state=state,
        action=RecoveryAction.OPERATOR_REVIEW,
        native_identity=native_identity,
        may_resend=False,
        diagnostic="terminal result already exists; automatic recovery is not allowed",
    )


def terminalize_orphaned_attempt(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
    reason: str,
) -> None:
    """Irreversibly settle an uncertain attempt when opt-out wins the race."""
    _require_non_empty(attempt_id=attempt_id, reason=reason)
    row = unit.execute(
        "SELECT epoch_id FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchone()
    if row is None:
        return
    unit.execute(
        "UPDATE delivery_attempts SET state = ?, reconciliation_policy = ? WHERE project_uuid = ? AND attempt_id = ?",
        (
            DeliveryAttemptState.TERMINAL_UNKNOWN.value,
            f"terminalized:{reason}",
            unit.project_uuid.storage_token,
            attempt_id,
        ),
    )
    unit.execute(
        "INSERT INTO delivery_results "
        "(result_id, project_uuid, epoch_id, attempt_id, outcome, terminal_refusal_category, recorded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            f"{attempt_id}:terminal-unknown",
            unit.project_uuid.storage_token,
            int(row[0]),
            attempt_id,
            DeliveryOutcome.TERMINAL_UNKNOWN.value,
            reason,
            _now(),
        ),
    )


def settle_attempts_for_opt_out(
    unit: ProjectUnitOfWork,
    *,
    reason: str,
) -> OptOutSettlement:
    """Cancel not-started attempts and terminalize started/uncertain orphans.

    This is the durable half of the WP06 opt-out ordering contract.  It does not
    claim remote revocation; it only prevents prepared attempts from starting and
    makes already-started/unknown attempts impossible to promote automatically
    after opt-out has returned.
    """
    _require_non_empty(reason=reason)
    prepared_rows = unit.execute(
        "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? AND state = ?",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
        ),
    ).fetchall()
    unit.execute(
        "UPDATE delivery_attempts SET state = ?, reconciliation_policy = ? WHERE project_uuid = ? AND state = ?",
        (
            DeliveryAttemptState.CANCELED.value,
            f"canceled:{reason}",
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
        ),
    )
    orphan_rows = unit.execute(
        "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? AND state IN (?, ?)",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchall()
    for row in orphan_rows:
        terminalize_orphaned_attempt(unit, attempt_id=str(row[0]), reason=reason)
    return OptOutSettlement(
        canceled_before_transport=len(prepared_rows),
        terminalized_orphans=len(orphan_rows),
    )


def recover_delivery_attempts(unit: ProjectUnitOfWork) -> list[DeliveryAttemptRecord]:
    """Return recoverable attempts without inventing a new native identity."""
    records: list[DeliveryAttemptRecord] = []
    for row in unit.execute(
        "SELECT attempt_id, state, payload_reference, payload_hash, reconciliation_policy FROM delivery_attempts WHERE project_uuid = ? AND state IN (?, ?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
            DeliveryAttemptState.TERMINAL_UNKNOWN.value,
        ),
    ):
        metadata = _metadata_from_payload_reference(row[2])
        records.append(
            DeliveryAttemptRecord(
                attempt_id=str(row[0]),
                state=DeliveryAttemptState(str(row[1])),
                native_identity=metadata.get("native_identity"),
                payload_hash=str(row[3]) if row[3] is not None else None,
                reconciliation_policy=str(row[4]) if row[4] is not None else None,
            )
        )
    return records


def _validate_context_for_unit(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    require_lease: bool,
) -> None:
    validate_project_sync_context_authority(context)
    if context.project_uuid != unit.project_uuid or context.store_identity != unit.store_identity:
        raise ProjectStoreError("delivery attempt context does not match the active project unit")
    if require_lease and not context.egress_eligible:
        raise ProjectStoreError("transport/result operation requires the project transport lease")


def _attempt_metadata(spec: DeliveryAttemptSpec) -> dict[str, str]:
    return {
        "payload_reference": spec.payload_reference,
        "write_kind": spec.write_kind,
        "native_identity": spec.native_identity,
    }


def _metadata_from_payload_reference(raw_value: object) -> dict[str, str]:
    if not isinstance(raw_value, str):
        return {}
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return {"payload_reference": raw_value}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _require_non_empty(**values: str) -> None:
    for name, value in values.items():
        if not value.strip():
            raise ValueError(f"{name} must be non-empty")


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "DeliveryAttemptRecord",
    "DeliveryRecoveryDecision",
    "DeliveryAttemptSpec",
    "DeliveryAttemptState",
    "DeliveryOutcome",
    "OptOutSettlement",
    "RecoveryAction",
    "mark_transport_started",
    "mark_delivery_result_unknown",
    "plan_delivery_attempt_recovery",
    "prepare_delivery_attempt",
    "record_delivery_result",
    "recover_delivery_attempts",
    "settle_attempts_for_opt_out",
    "terminalize_orphaned_attempt",
]
