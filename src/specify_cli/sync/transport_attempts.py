"""Durable delivery-attempt protocol for project-scoped hosted-sync writes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from kernel.clock import UTC, datetime, now_utc, now_utc_iso, timedelta
from enum import StrEnum
from typing import Any, cast
from uuid import UUID, uuid4

from specify_cli.sync.project_context import ProjectSyncContext, validate_project_sync_context_authority
from specify_cli.sync.project_store import ProjectStoreError, ProjectStoreLockedError, ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.transport_lease import (
    TransportLeaseContext,
    acquire_project_transport_lease,
    transport_lease_context_is_live,
    transport_lease_identity_is_live_for_project,
)


class DeliveryAttemptState(StrEnum):
    """Durable states with explicit uncertainty and irreversible orphan handling."""

    PREPARED = "prepared"
    IN_FLIGHT = "in_flight"
    PENDING_REMOTE = "pending_remote"
    RETRYABLE_NO_EFFECT = "retryable_no_effect"
    UNKNOWN = "unknown"
    TERMINAL_UNKNOWN = "terminal_unknown"
    SUCCEEDED = "succeeded"
    REFUSED = "refused"
    CANCELED = "canceled"


class DeliveryOutcome(StrEnum):
    """Truthful terminal result classes recorded under the transport lease.

    ``PREFLIGHT_ACCEPTED`` exists so a non-mutating endpoint can reach a
    terminal ledger state without claiming delivery. Preflight guarantees the
    server *would* accept the batch; it guarantees nothing about the server
    holding it. Recording that as ``DELIVERED`` made an in-progress preflight
    phase indistinguishable from completed delivery (#3722).
    """

    DELIVERED = "delivered"
    PREFLIGHT_ACCEPTED = "preflight_accepted"
    DUPLICATE = "duplicate"
    PENDING = "pending"
    RETRYABLE_NO_EFFECT = "retryable_no_effect"
    REFUSED = "refused"
    UNKNOWN = "unknown"
    TERMINAL_UNKNOWN = "terminal_unknown"


class RecoveryAction(StrEnum):
    """Adapter-neutral recovery action for one durable attempt."""

    QUERY_NATIVE_IDENTITY = "query_native_identity"
    RETRY_NATIVE_IDENTITY = "retry_native_identity"
    TERMINALIZED_NOOP = "terminalized_noop"
    OPERATOR_REVIEW = "operator_review"


class ReconciliationPolicy(StrEnum):
    """Native adapter strategy the durable protocol may perform automatically."""

    NATIVE_IDENTITY_QUERY = "native_identity_query"
    NATIVE_IDENTITY_RETRY = "native_identity_retry"
    NATIVE_IDENTITY_RETRY_THEN_QUERY = "native_identity_retry_then_query"
    OPERATOR_REVIEW = "operator_review"


class LogicalOperationRepeatability(StrEnum):
    """Whether terminal history completes or precedes a logical invocation."""

    REPEATABLE_READ = "repeatable_read"
    IDEMPOTENT_WRITE = "idempotent_write"


class LogicalOperationDisposition(StrEnum):
    """Typed action selected atomically for one logical hosted operation."""

    NEW_PREPARED = "new_prepared"
    PREPARED_RETRY = "prepared_retry"
    RETRYABLE_RESTART = "retryable_restart"
    QUERY_NATIVE = "query_native"
    OPERATOR_REVIEW = "operator_review"
    TERMINAL_PRIOR = "terminal_prior"


class DeliveryTerminalResultStatus(StrEnum):
    """Typed presence/state classification for exact terminal history."""

    ABSENT = "absent"
    NONTERMINAL = "nonterminal"
    TERMINAL = "terminal"


_REQUIRED_METADATA_FIELDS = (
    "payload_reference",
    "write_kind",
    "native_identity",
    "project_uuid",
    "store_database_path",
    "store_schema_version",
    "store_layout_version",
    "epoch_id",
    "consent_generation",
    "target_identity",
    "account_identity",
    "private_teamspace_id",
    "target_generation",
    "admission_generation",
    "binding_audience",
    "deadline_at",
    "reconciliation_policy",
)

_LOGICAL_OPERATION_PREFIX = "logical-operation:"
_LOGICAL_OPERATION_SCHEMA = "spec-kitty.logical-operation.v1"
_LOGICAL_OPERATION_MAX_LIFETIME = timedelta(hours=1)
_LOGICAL_OPERATION_TERMINAL_STATES = frozenset(
    {
        DeliveryAttemptState.SUCCEEDED,
        DeliveryAttemptState.REFUSED,
        DeliveryAttemptState.CANCELED,
        DeliveryAttemptState.TERMINAL_UNKNOWN,
    }
)


@dataclass(frozen=True, slots=True)
class DeliveryAttemptSpec:
    """Adapter-neutral immutable identity for a possible remote disclosure."""

    attempt_id: str
    write_kind: str
    native_identity: str
    payload_hash: str
    payload_reference: str
    outbox_task_id: str | None = None
    deadline_at: str = ""
    reconciliation_policy: str = ReconciliationPolicy.OPERATOR_REVIEW.value
    logical_operation_semantic_key: str | None = None
    logical_operation_repeatability: str | None = None
    logical_operation_collaborative_teamspace_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryAttemptRecord:
    """Recovered durable attempt row."""

    attempt_id: str
    state: DeliveryAttemptState
    native_identity: str | None
    payload_hash: str | None
    reconciliation_policy: str | None


@dataclass(frozen=True, slots=True)
class DeliveryAttemptProjection:
    """Typed read projection for consumers that do not own attempt SQL."""

    attempt_id: str
    state: DeliveryAttemptState | None
    write_kind: str | None
    event_id: str | None
    target_id: str | None
    legacy_metadata: dict[str, Any] | None
    created_at: str | None


@dataclass(frozen=True, slots=True)
class OptOutSettlement:
    """Counts for one opt-out settlement pass over durable attempts."""

    canceled_before_transport: int
    terminalized_orphans: int
    waiting_live_attempts: int = 0


@dataclass(frozen=True, slots=True)
class DeliveryRecoveryDecision:
    """Recovery decision that never invents a fresh disclosure identity."""

    attempt_id: str
    state: DeliveryAttemptState
    action: RecoveryAction
    native_identity: str | None
    may_resend: bool
    diagnostic: str


@dataclass(frozen=True, slots=True)
class LogicalOperationRequest:
    """Immutable semantic identity and policy for one hosted invocation."""

    write_kind: str
    semantic_key: str
    payload_hash: str
    payload_reference: str
    repeatability: LogicalOperationRepeatability
    reconciliation_policy: str
    deadline_at: str
    recover_with_persisted_deadline: bool = False
    requested_native_identity: str | None = None
    collaborative_teamspace_id: str | None = None


@dataclass(frozen=True, slots=True)
class LogicalOperationDecision:
    """Durable allocator result; it authorizes no I/O by itself."""

    disposition: LogicalOperationDisposition
    attempt_id: str
    native_identity: str | None
    state: DeliveryAttemptState | None
    outcome: DeliveryOutcome | None
    terminal_refusal_category: str | None
    repeatability: LogicalOperationRepeatability
    may_resend: bool
    may_query: bool
    requires_operator_review: bool
    remote_operation_id: str | None
    deadline_at: str | None
    diagnostic: str
    terminal_response_reference: str | None = None
    terminal_refusal_reference: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryTerminalResultProjection:
    """Validated terminal history without exposing delivery-store rows."""

    status: DeliveryTerminalResultStatus
    attempt_id: str
    state: DeliveryAttemptState | None
    outcome: DeliveryOutcome | None
    terminal_refusal_category: str | None


@dataclass(frozen=True, slots=True)
class _LogicalOperationCandidate:
    attempt_id: str
    state: DeliveryAttemptState
    payload_hash: str | None
    deadline_at: str | None
    reconciliation_policy: str | None
    metadata: dict[str, Any]
    epoch_id: int | None
    consent_generation: int | None
    target_generation: int | None
    admission_generation: str | None
    binding_audience: str | None


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
        deadline_at=spec.deadline_at,
        reconciliation_policy=spec.reconciliation_policy,
    )
    _validate_logical_operation_namespace(unit=unit, spec=spec)
    _parse_deadline(spec.deadline_at)
    policy = _parse_reconciliation_policy(spec.reconciliation_policy)
    metadata = _attempt_metadata(spec, context=context, unit=unit, reconciliation_policy=policy)
    _assert_native_identity_available_for_prepare(unit=unit, context=context, spec=spec, metadata=metadata)
    # TODO(#3262/WP06 follow-up): the existing project-store schema has only the
    # payload_reference text slot for native attempt metadata. This keeps the
    # current WP adapter-neutral and durable without a migration, but a later
    # schema-hardening WP should normalize native_identity/write_kind into first
    # class columns before adapters depend on query-heavy recovery. Until then,
    # the denormalized scan below fails closed on corrupt existing metadata
    # rather than risking a replayed/colliding native identity.
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
            policy.value,
            _now(),
        ),
    )
    return DeliveryAttemptRecord(
        attempt_id=spec.attempt_id,
        state=DeliveryAttemptState.PREPARED,
        native_identity=spec.native_identity,
        payload_hash=spec.payload_hash,
        reconciliation_policy=policy.value,
    )


def get_delivery_attempt_record(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
) -> DeliveryAttemptRecord | None:
    """Return an existing durable attempt by ID without parsing error strings.

    WP07 senders use this as the typed idempotency seam before calling
    :func:`prepare_delivery_attempt`: absence means a new attempt may be prepared;
    presence means the caller must recover or resume that exact attempt identity.
    """
    _require_non_empty(attempt_id=attempt_id)
    row = unit.execute(
        "SELECT state, payload_reference, payload_hash, reconciliation_policy FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        return None
    metadata = _metadata_from_payload_reference(row[1])
    native_identity = metadata.get("native_identity")
    return DeliveryAttemptRecord(
        attempt_id=attempt_id,
        state=DeliveryAttemptState(str(row[0])),
        native_identity=native_identity,
        payload_hash=str(row[2]) if row[2] is not None else None,
        reconciliation_policy=str(row[3]) if row[3] is not None else None,
    )


def get_delivery_terminal_result_projection(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    spec: DeliveryAttemptSpec,
) -> DeliveryTerminalResultProjection:
    """Return validated exact terminal history under the active transport lease.

    Absence and nonterminal history are explicit typed results. Existing history
    is never accepted by attempt ID alone: its complete authority tuple,
    transport identity, write kind, payload hash, and payload reference must
    match the caller's immutable specification before any result is projected.
    """
    _validate_context_for_unit(unit, context, require_lease=True)
    _require_non_empty(
        attempt_id=spec.attempt_id,
        write_kind=spec.write_kind,
        native_identity=spec.native_identity,
        payload_hash=spec.payload_hash,
        payload_reference=spec.payload_reference,
    )
    row = unit.execute(
        "SELECT epoch_id, consent_generation, target_generation, admission_generation, binding_audience, "
        "payload_reference, state, payload_hash FROM delivery_attempts "
        "WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, spec.attempt_id),
    ).fetchone()
    if row is None:
        return DeliveryTerminalResultProjection(
            status=DeliveryTerminalResultStatus.ABSENT,
            attempt_id=spec.attempt_id,
            state=None,
            outcome=None,
            terminal_refusal_category=None,
        )
    try:
        _assert_attempt_authority_matches_context(row=row, unit=unit, context=context)
    except (TypeError, ValueError, IndexError) as exc:
        raise ProjectStoreError("delivery terminal projection attempt authority is corrupt") from exc
    target = context.target_audience
    if target is None:
        raise ProjectStoreError("delivery terminal projection requires an admitted target audience")
    metadata = _metadata_from_payload_reference(row[5])
    diagnostic = _metadata_required_identity_diagnostic(
        metadata,
        payload_hash=str(row[7]) if row[7] is not None else None,
    )
    if diagnostic is not None:
        raise ProjectStoreError(diagnostic)
    expected = {
        "write_kind": spec.write_kind,
        "native_identity": spec.native_identity,
        "payload_reference": spec.payload_reference,
    }
    for key, expected_value in expected.items():
        if metadata.get(key) != expected_value:
            raise ProjectStoreError(f"delivery terminal projection {key} does not match exact attempt history")
    if str(row[7]) != spec.payload_hash:
        raise ProjectStoreError("delivery terminal projection payload hash does not match exact attempt history")
    try:
        state = DeliveryAttemptState(str(row[6]))
    except ValueError as exc:
        raise ProjectStoreError("delivery terminal projection attempt state is invalid") from exc
    terminal_results = _validated_terminal_projection_results(
        unit,
        attempt_id=spec.attempt_id,
        epoch_id=context.epoch_id,
        target_generation=target.configuration_generation,
        admission_generation=context.admission_generation,
    )
    if state not in _LOGICAL_OPERATION_TERMINAL_STATES:
        if terminal_results:
            raise ProjectStoreError("nonterminal delivery attempt has contradictory terminal result history")
        return DeliveryTerminalResultProjection(
            status=DeliveryTerminalResultStatus.NONTERMINAL,
            attempt_id=spec.attempt_id,
            state=state,
            outcome=None,
            terminal_refusal_category=None,
        )
    if len(terminal_results) != 1:
        raise ProjectStoreError("terminal delivery attempt requires exactly one durable terminal result")
    outcome, category = terminal_results[0]
    expected_state = {
        DeliveryOutcome.DELIVERED: DeliveryAttemptState.SUCCEEDED,
        DeliveryOutcome.DUPLICATE: DeliveryAttemptState.SUCCEEDED,
        # Terminal, so a re-run replays the accepted verdict instead of
        # crashing on a perpetually nonterminal attempt -- the constraint the
        # DELIVERED shortcut was protecting -- without asserting delivery.
        DeliveryOutcome.PREFLIGHT_ACCEPTED: DeliveryAttemptState.SUCCEEDED,
        DeliveryOutcome.REFUSED: DeliveryAttemptState.REFUSED,
        DeliveryOutcome.TERMINAL_UNKNOWN: DeliveryAttemptState.TERMINAL_UNKNOWN,
    }[outcome]
    if state is not expected_state:
        raise ProjectStoreError("terminal delivery result outcome does not match attempt state")
    return DeliveryTerminalResultProjection(
        status=DeliveryTerminalResultStatus.TERMINAL,
        attempt_id=spec.attempt_id,
        state=state,
        outcome=outcome,
        terminal_refusal_category=category,
    )


def _validated_terminal_projection_results(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
    epoch_id: int | None,
    target_generation: int,
    admission_generation: str | None,
) -> list[tuple[DeliveryOutcome, str | None]]:
    result_rows = unit.execute(
        "SELECT epoch_id, target_generation, admission_generation, outcome, terminal_refusal_category "
        "FROM delivery_results WHERE project_uuid = ? AND attempt_id = ? ORDER BY recorded_at, result_id",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchall()
    terminal_results: list[tuple[DeliveryOutcome, str | None]] = []
    for result_row in result_rows:
        try:
            outcome = DeliveryOutcome(str(result_row[3]))
            result_epoch_id = int(cast("str | int | float | bytes", result_row[0]))
            result_target_generation = int(cast("str | int | float | bytes", result_row[1]))
        except (TypeError, ValueError, IndexError) as exc:
            raise ProjectStoreError("delivery terminal projection result row is corrupt") from exc
        category = str(result_row[4]) if result_row[4] is not None else None
        _validate_result_category(outcome=outcome, terminal_refusal_category=category)
        if result_epoch_id != epoch_id or result_target_generation != target_generation or str(result_row[2]) != admission_generation:
            raise ProjectStoreError("delivery terminal result authority no longer matches the live transport lease")
        if outcome in {
            DeliveryOutcome.DELIVERED,
            DeliveryOutcome.DUPLICATE,
            DeliveryOutcome.REFUSED,
            DeliveryOutcome.TERMINAL_UNKNOWN,
        }:
            terminal_results.append((outcome, category))
    return terminal_results


def list_delivery_attempt_projections(unit: ProjectUnitOfWork) -> list[DeliveryAttemptProjection]:
    """Return typed delivery-attempt rows without exposing table tuple shape."""
    rows = unit.execute(
        "SELECT attempt_id, state, payload_reference, created_at FROM delivery_attempts WHERE project_uuid = ? ORDER BY created_at, attempt_id",
        (unit.project_uuid.storage_token,),
    ).fetchall()
    return [_delivery_attempt_projection_from_row(row) for row in rows]


def _delivery_attempt_projection_from_row(row: Any) -> DeliveryAttemptProjection:
    attempt_id = str(row[0])
    state_value = str(row[1])
    metadata = _read_projection_metadata(row[2])
    write_kind = _optional_projection_string(metadata, "write_kind")
    if attempt_id.startswith("dispatcher-http:") and write_kind != "dispatcher_http_event":
        raise ProjectStoreError("dispatcher delivery attempt metadata is missing dispatcher_http_event write_kind")
    if attempt_id.startswith("event:") and write_kind != "event":
        raise ProjectStoreError("Event delivery attempt metadata is missing event write_kind")
    try:
        state: DeliveryAttemptState | None = DeliveryAttemptState(state_value)
    except ValueError as exc:
        if write_kind in {"dispatcher_http_event", "event"}:
            raise ProjectStoreError("dispatcher delivery attempt has an invalid state") from exc
        state = None
    event_id: str | None = None
    target_id: str | None = None
    legacy_metadata: dict[str, Any] | None = None
    if write_kind in {"dispatcher_http_event", "event"}:
        event_id, target_id = _dispatcher_correlation_from_metadata(metadata)
    elif "event_id" in metadata or "target_id" in metadata:
        event_id = _required_projection_string(metadata, "event_id", "legacy delivery attempt metadata")
        target_id = _required_projection_string(metadata, "target_id", "legacy delivery attempt metadata")
        legacy_metadata = metadata
    elif write_kind is None:
        raise ProjectStoreError("delivery attempt metadata requires write_kind or complete legacy event_id/target_id correlation")
    return DeliveryAttemptProjection(
        attempt_id=attempt_id,
        state=state,
        write_kind=write_kind,
        event_id=event_id,
        target_id=target_id,
        legacy_metadata=legacy_metadata,
        created_at=str(row[3]) if row[3] is not None else None,
    )


def _read_projection_metadata(raw_value: object) -> dict[str, Any]:
    if raw_value is None:
        raise ProjectStoreError("delivery attempt metadata is missing")
    try:
        value = json.loads(str(raw_value))
    except json.JSONDecodeError as exc:
        raise ProjectStoreError("delivery attempt metadata is not JSON") from exc
    if not isinstance(value, dict):
        raise ProjectStoreError("delivery attempt metadata must be a JSON object")
    return value


def _optional_projection_string(metadata: dict[str, Any], key: str) -> str | None:
    if key not in metadata:
        return None
    value = metadata[key]
    if not isinstance(value, str) or not value.strip():
        raise ProjectStoreError(f"delivery attempt metadata field {key} must be a non-empty string")
    return value


def _required_projection_string(metadata: dict[str, Any], key: str, context: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectStoreError(f"{context} field {key} must be a non-empty string")
    return value


def _dispatcher_correlation_from_metadata(metadata: dict[str, Any]) -> tuple[str, str]:
    raw_reference = metadata.get("payload_reference")
    if not isinstance(raw_reference, str):
        raise ProjectStoreError("dispatcher delivery attempt metadata is missing structured payload_reference")
    try:
        reference: Any = json.loads(raw_reference)
    except json.JSONDecodeError as exc:
        raise ProjectStoreError("dispatcher delivery attempt payload_reference is not JSON") from exc
    if not isinstance(reference, dict) or reference.get("schema") != "spec-kitty.dispatcher.v1":
        raise ProjectStoreError("dispatcher delivery attempt payload_reference has an unsupported schema")
    event_id = reference.get("event_id")
    target_id = reference.get("target_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ProjectStoreError("dispatcher delivery attempt payload_reference missing event_id")
    if not isinstance(target_id, str) or not target_id.strip():
        raise ProjectStoreError("dispatcher delivery attempt payload_reference missing target_id")
    return event_id, target_id


def mark_transport_started(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    attempt_id: str,
    *,
    now: datetime | None = None,
) -> None:
    """Move a prepared attempt to in-flight immediately before I/O."""
    _validate_context_for_unit(unit, context, require_lease=True)
    row = unit.execute(
        "SELECT epoch_id, consent_generation, target_generation, admission_generation, binding_audience, payload_reference, deadline_at "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state = ?",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.PREPARED.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt was not prepared for transport start")
    _assert_attempt_authority_matches_context(row=row, unit=unit, context=context)
    deadline = _parse_deadline(str(row[6]) if row[6] is not None else "")
    if deadline <= (now or now_utc()):
        raise ProjectStoreError("delivery attempt deadline expired before transport start")
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
        "SELECT epoch_id, consent_generation, target_generation, admission_generation, binding_audience, payload_reference "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("unknown result requires a started attempt")
    _assert_attempt_authority_matches_context(row=row, unit=unit, context=context)
    unit.execute(
        "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?)",
        (
            DeliveryAttemptState.UNKNOWN.value,
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
    _record_delivery_result(
        unit,
        context,
        result_id=result_id,
        attempt_id=attempt_id,
        outcome=outcome,
        terminal_refusal_category=terminal_refusal_category,
        allow_queried_recovery=False,
    )


def _record_delivery_result(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    result_id: str,
    attempt_id: str,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None,
    allow_queried_recovery: bool,
) -> None:
    _validate_context_for_unit(unit, context, require_lease=True)
    _validate_result_category(outcome=outcome, terminal_refusal_category=terminal_refusal_category)
    if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE}:
        terminal_state = DeliveryAttemptState.SUCCEEDED
    elif outcome is DeliveryOutcome.REFUSED:
        terminal_state = DeliveryAttemptState.REFUSED
    elif outcome is DeliveryOutcome.TERMINAL_UNKNOWN:
        terminal_state = DeliveryAttemptState.TERMINAL_UNKNOWN
    elif outcome is DeliveryOutcome.PENDING:
        terminal_state = DeliveryAttemptState.PENDING_REMOTE
    elif outcome is DeliveryOutcome.RETRYABLE_NO_EFFECT:
        terminal_state = DeliveryAttemptState.RETRYABLE_NO_EFFECT
    else:
        terminal_state = DeliveryAttemptState.UNKNOWN
    row = unit.execute(
        "SELECT epoch_id, consent_generation, target_generation, admission_generation, binding_audience, payload_reference, state "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.UNKNOWN.value,
            DeliveryAttemptState.PENDING_REMOTE.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery result requires a live or recoverable attempt")
    _assert_attempt_authority_matches_context(row=row, unit=unit, context=context)
    persisted_state = DeliveryAttemptState(str(row[6]))
    direct_recovery_noop = outcome is DeliveryOutcome.UNKNOWN or (persisted_state is DeliveryAttemptState.PENDING_REMOTE and outcome is DeliveryOutcome.PENDING)
    if not allow_queried_recovery and persisted_state in {DeliveryAttemptState.PENDING_REMOTE, DeliveryAttemptState.UNKNOWN} and not direct_recovery_noop:
        raise ProjectStoreError("recoverable delivery result promotion requires the remote operation query execution seam")
    recorded_at = _now()
    existing_result = unit.execute(
        "SELECT attempt_id, epoch_id, target_generation, admission_generation, outcome, terminal_refusal_category "
        "FROM delivery_results WHERE project_uuid = ? AND result_id = ?",
        (unit.project_uuid.storage_token, result_id),
    ).fetchone()
    if existing_result is None:
        unit.execute(
            "INSERT INTO delivery_results "
            "(result_id, project_uuid, epoch_id, attempt_id, target_generation, "
            "admission_generation, outcome, terminal_refusal_category, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result_id,
                unit.project_uuid.storage_token,
                int(cast("str | int | float | bytes", row[0])),
                attempt_id,
                int(row[2]) if row[2] is not None else None,
                str(row[3]) if row[3] is not None else None,
                outcome.value,
                terminal_refusal_category,
                recorded_at,
            ),
        )
    else:
        _assert_result_upsert_allowed(
            existing_result=existing_result,
            row=row,
            attempt_id=attempt_id,
            outcome=outcome,
            terminal_refusal_category=terminal_refusal_category,
        )
        unit.execute(
            "UPDATE delivery_results SET outcome = ?, terminal_refusal_category = ?, recorded_at = ? WHERE project_uuid = ? AND result_id = ?",
            (
                outcome.value,
                terminal_refusal_category,
                recorded_at,
                unit.project_uuid.storage_token,
                result_id,
            ),
        )
    unit.execute(
        "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ?",
        (terminal_state.value, unit.project_uuid.storage_token, attempt_id),
    )


def restart_delivery_attempt(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    attempt_id: str,
    *,
    now: datetime | None = None,
) -> None:
    """Restart a proved-no-effect attempt with the same native identity row.

    This is the only automatic resend seam for attempts that reached a receiver
    but were classified as having no remote effect. It never mints a fresh row or
    native identity; callers must send the original attempt after this returns.
    """
    _validate_context_for_unit(unit, context, require_lease=True)
    row = unit.execute(
        "SELECT epoch_id, consent_generation, target_generation, admission_generation, binding_audience, payload_reference, deadline_at, reconciliation_policy "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state = ?",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.RETRYABLE_NO_EFFECT.value,
        ),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt is not retryable without effect")
    _assert_attempt_authority_matches_context(row=row, unit=unit, context=context)
    if _parse_reconciliation_policy(str(row[7]) if row[7] is not None else "") not in {
        ReconciliationPolicy.NATIVE_IDENTITY_RETRY,
        ReconciliationPolicy.NATIVE_IDENTITY_RETRY_THEN_QUERY,
    }:
        raise ProjectStoreError("delivery attempt retry is not authorized by reconciliation policy")
    deadline = _parse_deadline(str(row[6]) if row[6] is not None else "")
    if deadline <= (now or now_utc()):
        raise ProjectStoreError("delivery attempt deadline expired before transport restart")
    unit.execute(
        "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ? AND state = ?",
        (
            DeliveryAttemptState.IN_FLIGHT.value,
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.RETRYABLE_NO_EFFECT.value,
        ),
    )


def plan_delivery_attempt_recovery(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
    now: datetime | None = None,
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
        "SELECT state, payload_reference, reconciliation_policy, deadline_at, payload_hash, "
        "epoch_id, consent_generation, target_generation, admission_generation, binding_audience "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt does not exist")
    state = DeliveryAttemptState(str(row[0]))
    metadata = _metadata_from_payload_reference(row[1])
    native_identity = metadata.get("native_identity")
    policy = _parse_reconciliation_policy(str(row[2]) if row[2] is not None else "")
    deadline = _parse_deadline(str(row[3]) if row[3] is not None else "")
    metadata_diagnostic = _recovery_metadata_diagnostic(row=row, metadata=metadata)
    if metadata_diagnostic is not None:
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.OPERATOR_REVIEW,
            native_identity=native_identity if native_identity and native_identity.strip() else None,
            may_resend=False,
            diagnostic=metadata_diagnostic,
        )
    if state in {
        DeliveryAttemptState.PREPARED,
        DeliveryAttemptState.IN_FLIGHT,
        DeliveryAttemptState.PENDING_REMOTE,
        DeliveryAttemptState.RETRYABLE_NO_EFFECT,
        DeliveryAttemptState.UNKNOWN,
    } and deadline <= (now or now_utc()):
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.OPERATOR_REVIEW,
            native_identity=native_identity,
            may_resend=False,
            diagnostic="attempt deadline expired; automatic retry/query is not allowed",
        )
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
        if policy not in {
            ReconciliationPolicy.NATIVE_IDENTITY_RETRY,
            ReconciliationPolicy.NATIVE_IDENTITY_RETRY_THEN_QUERY,
        }:
            return DeliveryRecoveryDecision(
                attempt_id=attempt_id,
                state=state,
                action=RecoveryAction.OPERATOR_REVIEW,
                native_identity=native_identity,
                may_resend=False,
                diagnostic="attempt is prepared but native retry is not authorized by reconciliation policy",
            )
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.RETRY_NATIVE_IDENTITY,
            native_identity=native_identity,
            may_resend=True,
            diagnostic="attempt was durable before transport; retry only with the original native identity",
        )
    if state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
        if policy not in {
            ReconciliationPolicy.NATIVE_IDENTITY_RETRY,
            ReconciliationPolicy.NATIVE_IDENTITY_RETRY_THEN_QUERY,
        }:
            return DeliveryRecoveryDecision(
                attempt_id=attempt_id,
                state=state,
                action=RecoveryAction.OPERATOR_REVIEW,
                native_identity=native_identity,
                may_resend=False,
                diagnostic="attempt is proved no-effect but native retry is not authorized by reconciliation policy",
            )
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.RETRY_NATIVE_IDENTITY,
            native_identity=native_identity,
            may_resend=True,
            diagnostic="attempt has no remote effect; retry only by restarting the original native identity",
        )
    if state in {DeliveryAttemptState.IN_FLIGHT, DeliveryAttemptState.PENDING_REMOTE, DeliveryAttemptState.UNKNOWN}:
        if policy not in {
            ReconciliationPolicy.NATIVE_IDENTITY_QUERY,
            ReconciliationPolicy.NATIVE_IDENTITY_RETRY_THEN_QUERY,
        }:
            return DeliveryRecoveryDecision(
                attempt_id=attempt_id,
                state=state,
                action=RecoveryAction.OPERATOR_REVIEW,
                native_identity=native_identity,
                may_resend=False,
                diagnostic="attempt may have a remote effect; policy requires operator review",
            )
        return DeliveryRecoveryDecision(
            attempt_id=attempt_id,
            state=state,
            action=RecoveryAction.QUERY_NATIVE_IDENTITY,
            native_identity=native_identity,
            may_resend=False,
            diagnostic="transport may have a remote effect; query/reconcile original native identity only",
        )
    return DeliveryRecoveryDecision(
        attempt_id=attempt_id,
        state=state,
        action=RecoveryAction.OPERATOR_REVIEW,
        native_identity=native_identity,
        may_resend=False,
        diagnostic="terminal result already exists; automatic recovery is not allowed",
    )


def allocate_logical_delivery_operation(
    store: ProjectSyncStore,
    request: LogicalOperationRequest,
    *,
    lock_timeout_seconds: float = 5.0,
    now: datetime | None = None,
) -> LogicalOperationDecision:
    """Atomically recover or persist one logical hosted operation before I/O.

    The project transport lease serializes competing allocators. The returned
    decision carries durable identity and recovery truth but does not start the
    attempt or authorize a network call; callers must leave this transaction and
    use the normal WP06 start/restart/query surfaces.
    """
    current_time = (now or now_utc()).astimezone(UTC)
    policy = _validate_logical_operation_request(request)
    with (
        acquire_project_transport_lease(
            store,
            lock_timeout_seconds=lock_timeout_seconds,
            lease_identity="logical-operation-allocation",
        ) as lease,
        lease.unit_of_work() as (unit, context),
    ):
        _validate_context_for_unit(unit, context, require_lease=True)
        matches: list[_LogicalOperationCandidate] = []
        for row in _logical_operation_rows(unit):
            attempt_id = str(row[0])
            if not _logical_attempt_id_may_match_request(
                project_uuid=unit.project_uuid.storage_token,
                request=request,
                attempt_id=attempt_id,
            ):
                continue
            try:
                candidate = _logical_operation_candidate(unit, row)
            except (ProjectStoreError, ValueError) as exc:
                return _logical_operator_review(
                    request,
                    attempt_id=attempt_id,
                    native_identity=None,
                    state=None,
                    deadline_at=None,
                    diagnostic=f"logical operation metadata requires operator review: {exc}",
                )
            if (
                candidate.metadata["logical_operation_semantic_key"] != request.semantic_key
                or candidate.metadata["write_kind"] != request.write_kind
                or candidate.metadata["logical_operation_repeatability"] != request.repeatability.value
            ):
                continue
            authority_diagnostic = _logical_operation_authority_diagnostic(
                candidate=candidate,
                unit=unit,
                context=context,
            )
            if authority_diagnostic is not None:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic=authority_diagnostic,
                )
            if candidate.payload_hash != request.payload_hash:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation payload hash drift requires operator review",
                )
            if candidate.metadata["payload_reference"] != request.payload_reference:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation payload reference drift requires operator review",
                )
            if candidate.reconciliation_policy != request.reconciliation_policy:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation reconciliation policy drift requires operator review",
                )
            if candidate.metadata.get("collaborative_teamspace_id") != request.collaborative_teamspace_id:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation Collaborative Teamspace authority drift requires operator review",
                )
            expected_native_identity = request.requested_native_identity or candidate.attempt_id
            if candidate.metadata.get("native_identity") != expected_native_identity:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation native identity drift requires operator review",
                )
            deadline_may_be_recovered = request.recover_with_persisted_deadline and candidate.state not in _LOGICAL_OPERATION_TERMINAL_STATES
            terminal_prior_never_resends = candidate.state in _LOGICAL_OPERATION_TERMINAL_STATES
            if candidate.deadline_at != request.deadline_at and not deadline_may_be_recovered and not terminal_prior_never_resends:
                return _logical_operator_review_for_candidate(
                    unit,
                    request,
                    candidate,
                    diagnostic="logical operation deadline drift requires operator review",
                )
            matches.append(candidate)

        nonterminal = [candidate for candidate in matches if candidate.state not in _LOGICAL_OPERATION_TERMINAL_STATES]
        if len(nonterminal) > 1:
            return _logical_operator_review_for_candidate(
                unit,
                request,
                nonterminal[0],
                diagnostic="multiple nonterminal logical operations require operator review",
            )
        if nonterminal:
            return _logical_recovery_decision(
                unit,
                request,
                nonterminal[0],
                now=current_time,
            )
        if request.repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE and matches:
            return _logical_terminal_prior_decision(unit, request, matches[0])

        _validate_new_logical_operation_deadline(request.deadline_at, now=current_time)
        attempt_id, native_identity = _new_logical_operation_identity(
            project_uuid=unit.project_uuid.storage_token,
            request=request,
        )
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id=attempt_id,
                write_kind=request.write_kind,
                native_identity=native_identity,
                payload_hash=request.payload_hash,
                payload_reference=request.payload_reference,
                deadline_at=request.deadline_at,
                reconciliation_policy=policy.value,
                logical_operation_semantic_key=request.semantic_key,
                logical_operation_repeatability=request.repeatability.value,
                logical_operation_collaborative_teamspace_id=request.collaborative_teamspace_id,
            ),
        )
        return LogicalOperationDecision(
            disposition=LogicalOperationDisposition.NEW_PREPARED,
            attempt_id=attempt_id,
            native_identity=native_identity,
            state=DeliveryAttemptState.PREPARED,
            outcome=None,
            terminal_refusal_category=None,
            repeatability=request.repeatability,
            may_resend=True,
            may_query=False,
            requires_operator_review=False,
            remote_operation_id=None,
            deadline_at=request.deadline_at,
            diagnostic="logical operation was durably prepared before transport",
        )


def attach_remote_operation_id(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    attempt_id: str,
    remote_operation_id: str,
) -> None:
    """Durably attach a server operation ID before recording pending state."""
    _validate_context_for_unit(unit, context, require_lease=True)
    _require_non_empty(attempt_id=attempt_id, remote_operation_id=remote_operation_id)
    row = unit.execute(
        "SELECT attempt_id, state, payload_hash, payload_reference, deadline_at, reconciliation_policy, "
        "epoch_id, consent_generation, target_generation, admission_generation, binding_audience "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("remote operation correlation requires a durable attempt")
    candidate = _logical_operation_candidate(unit, row)
    if candidate.state not in {
        DeliveryAttemptState.IN_FLIGHT,
        DeliveryAttemptState.PENDING_REMOTE,
        DeliveryAttemptState.UNKNOWN,
    }:
        raise ProjectStoreError("remote operation correlation requires a started or pending attempt")
    diagnostic = _logical_operation_authority_diagnostic(candidate=candidate, unit=unit, context=context)
    if diagnostic is not None:
        raise ProjectStoreError(diagnostic)
    existing = candidate.metadata.get("remote_operation_id")
    if existing is not None and existing != remote_operation_id:
        raise ProjectStoreError("delivery attempt already has a different remote operation id")
    candidate.metadata["remote_operation_id"] = remote_operation_id
    unit.execute(
        "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
        (json.dumps(candidate.metadata, sort_keys=True), unit.project_uuid.storage_token, attempt_id),
    )


def read_remote_operation_id(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
) -> str | None:
    """Read the durable remote-operation correlation for one logical attempt."""
    _require_non_empty(attempt_id=attempt_id)
    row = unit.execute(
        "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("delivery attempt does not exist")
    metadata = _logical_operation_metadata(attempt_id, row[0])
    return _optional_non_empty_metadata_string(metadata, "remote_operation_id")


def record_logical_operation_result(
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    *,
    result_id: str,
    attempt_id: str,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None = None,
    response_reference: str | None = None,
    refusal_reference: str | None = None,
) -> None:
    """Persist one logical-operation result and its exact public terminal value.

    Successful or duplicate idempotent writes need their original response on a
    later zero-I/O invocation.  The response reference is stored atomically with
    the result under the same active transport lease; callers receive only the
    typed projection carried by :class:`LogicalOperationDecision`.
    """
    _validate_context_for_unit(unit, context, require_lease=True)
    candidate = _logical_operation_candidate_by_id(unit, attempt_id=attempt_id)
    diagnostic = _logical_operation_authority_diagnostic(
        candidate=candidate,
        unit=unit,
        context=context,
    )
    if diagnostic is not None:
        raise ProjectStoreError(diagnostic)
    _persist_logical_terminal_reference(
        unit,
        candidate,
        outcome=outcome,
        terminal_refusal_category=terminal_refusal_category,
        response_reference=response_reference,
        refusal_reference=refusal_reference,
    )
    _record_delivery_result(
        unit,
        context,
        result_id=result_id,
        attempt_id=attempt_id,
        outcome=outcome,
        terminal_refusal_category=terminal_refusal_category,
        allow_queried_recovery=False,
    )


def _persist_logical_terminal_reference(
    unit: ProjectUnitOfWork,
    candidate: _LogicalOperationCandidate,
    *,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None,
    response_reference: str | None,
    refusal_reference: str | None,
) -> None:
    """Validate and persist the exact sanitized terminal public value."""
    _validate_logical_terminal_reference(
        outcome=outcome,
        terminal_refusal_category=terminal_refusal_category,
        response_reference=response_reference,
        refusal_reference=refusal_reference,
    )
    existing = candidate.metadata.get("terminal_response_reference")
    if existing is not None and existing != response_reference:
        raise ProjectStoreError("logical operation response reference changed")
    if response_reference is not None:
        candidate.metadata["terminal_response_reference"] = response_reference
    existing_refusal = candidate.metadata.get("terminal_refusal_reference")
    if existing_refusal is not None and existing_refusal != refusal_reference:
        raise ProjectStoreError("logical operation refusal reference changed")
    if refusal_reference is not None:
        candidate.metadata["terminal_refusal_reference"] = refusal_reference
    if response_reference is not None or refusal_reference is not None:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
            (
                json.dumps(candidate.metadata, sort_keys=True),
                unit.project_uuid.storage_token,
                candidate.attempt_id,
            ),
        )


def _validate_logical_terminal_reference(
    *,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None,
    response_reference: str | None,
    refusal_reference: str | None,
) -> None:
    if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE}:
        if not isinstance(response_reference, str) or not response_reference:
            raise ProjectStoreError("successful logical operation requires an exact response reference")
        if refusal_reference is not None:
            raise ProjectStoreError("successful logical operation cannot persist a refusal reference")
    elif outcome is DeliveryOutcome.REFUSED:
        if terminal_refusal_category == "project_not_admitted":
            if not isinstance(refusal_reference, str) or not refusal_reference:
                raise ProjectStoreError("project_not_admitted requires an exact refusal reference")
        elif refusal_reference is not None:
            raise ProjectStoreError("only project_not_admitted may persist a refusal reference")
        if response_reference is not None:
            raise ProjectStoreError("refused logical operation cannot persist a success response reference")
    elif response_reference is not None:
        raise ProjectStoreError("non-success logical operation cannot persist a success response reference")
    elif refusal_reference is not None:
        raise ProjectStoreError("non-refusal logical operation cannot persist a refusal reference")


def execute_remote_operation_query(
    store: ProjectSyncStore,
    *,
    attempt_id: str,
    result_id: str,
    query: Callable[[str], object],
    classify: Callable[[object], tuple[DeliveryOutcome, str | None]],
    response_reference: Callable[[object], str | None] | None = None,
    refusal_reference: Callable[[object], str | None] | None = None,
    lock_timeout_seconds: float = 5.0,
) -> object:
    """Query one attached operation without a UoW across I/O and persist truth."""
    _require_non_empty(attempt_id=attempt_id, result_id=result_id)
    with acquire_project_transport_lease(
        store,
        lock_timeout_seconds=lock_timeout_seconds,
        lease_identity="remote-operation-query",
    ) as lease:
        return execute_remote_operation_query_under_lease(
            lease,
            attempt_id=attempt_id,
            result_id=result_id,
            query=query,
            classify=classify,
            response_reference=response_reference,
            refusal_reference=refusal_reference,
        )


def execute_remote_operation_query_under_lease(
    lease: TransportLeaseContext,
    *,
    attempt_id: str,
    result_id: str,
    query: Callable[[str], object],
    classify: Callable[[object], tuple[DeliveryOutcome, str | None]],
    response_reference: Callable[[object], str | None] | None = None,
    refusal_reference: Callable[[object], str | None] | None = None,
) -> object:
    """Query and persist one operation while reusing a caller-held lease.

    Each SQLite unit closes before the callback, while the cross-process lease
    remains held continuously from the caller's transport start through query
    result persistence.
    """
    _require_non_empty(attempt_id=attempt_id, result_id=result_id)
    if not transport_lease_context_is_live(lease):
        raise ProjectStoreError("remote operation query requires a live project transport lease")
    with lease.unit_of_work() as (unit, context):
        candidate = _logical_operation_candidate_by_id(unit, attempt_id=attempt_id)
        _require_query_recovery_decision(unit, candidate)
        diagnostic = _logical_operation_authority_diagnostic(
            candidate=candidate,
            unit=unit,
            context=context,
        )
        if diagnostic is not None:
            raise ProjectStoreError(diagnostic)
        remote_operation_id = _logical_remote_operation_id(candidate)
        if remote_operation_id is None:
            raise ProjectStoreError("remote operation query requires durable correlation")

    value = query(remote_operation_id)
    outcome, refusal_category = classify(value)
    if not isinstance(outcome, DeliveryOutcome):
        raise TypeError("remote operation query classifier must return a DeliveryOutcome")
    projected_response = response_reference(value) if response_reference is not None else None
    projected_refusal = refusal_reference(value) if refusal_reference is not None else None

    with lease.unit_of_work() as (unit, context):
        candidate = _logical_operation_candidate_by_id(unit, attempt_id=attempt_id)
        _require_query_recovery_decision(unit, candidate)
        diagnostic = _logical_operation_authority_diagnostic(
            candidate=candidate,
            unit=unit,
            context=context,
        )
        if diagnostic is not None:
            raise ProjectStoreError(diagnostic)
        if _logical_remote_operation_id(candidate) != remote_operation_id:
            raise ProjectStoreError("remote operation correlation changed during query")
        if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE} and response_reference is not None:
            if not isinstance(projected_response, str) or not projected_response:
                raise ProjectStoreError("successful remote query requires an exact response reference")
            existing = candidate.metadata.get("terminal_response_reference")
            if existing is not None and existing != projected_response:
                raise ProjectStoreError("remote operation response reference changed")
            candidate.metadata["terminal_response_reference"] = projected_response
            unit.execute(
                "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
                (
                    json.dumps(candidate.metadata, sort_keys=True),
                    unit.project_uuid.storage_token,
                    attempt_id,
                ),
            )
        elif outcome not in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE} and projected_response is not None:
            raise ProjectStoreError("non-success remote query cannot persist a success response reference")
        if outcome is DeliveryOutcome.REFUSED and refusal_category == "project_not_admitted":
            if not isinstance(projected_refusal, str) or not projected_refusal:
                raise ProjectStoreError("project_not_admitted query requires an exact refusal reference")
            existing_refusal = candidate.metadata.get("terminal_refusal_reference")
            if existing_refusal is not None and existing_refusal != projected_refusal:
                raise ProjectStoreError("remote operation refusal reference changed")
            candidate.metadata["terminal_refusal_reference"] = projected_refusal
            unit.execute(
                "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
                (
                    json.dumps(candidate.metadata, sort_keys=True),
                    unit.project_uuid.storage_token,
                    attempt_id,
                ),
            )
        elif projected_refusal is not None:
            raise ProjectStoreError("only project_not_admitted query may persist a refusal reference")
        _record_delivery_result(
            unit,
            context,
            result_id=result_id,
            attempt_id=attempt_id,
            outcome=outcome,
            terminal_refusal_category=refusal_category,
            allow_queried_recovery=True,
        )
    return value


def _logical_operation_rows(unit: ProjectUnitOfWork) -> list[Any]:
    return list(
        unit.execute(
            "SELECT attempt_id, state, payload_hash, payload_reference, deadline_at, reconciliation_policy, "
            "epoch_id, consent_generation, target_generation, admission_generation, binding_audience "
            "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id LIKE ? "
            "ORDER BY created_at DESC, attempt_id DESC",
            (unit.project_uuid.storage_token, f"{_LOGICAL_OPERATION_PREFIX}%"),
        ).fetchall()
    )


def _logical_operation_candidate_by_id(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
) -> _LogicalOperationCandidate:
    row = unit.execute(
        "SELECT attempt_id, state, payload_hash, payload_reference, deadline_at, reconciliation_policy, "
        "epoch_id, consent_generation, target_generation, admission_generation, binding_audience "
        "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        raise ProjectStoreError("logical operation does not exist")
    return _logical_operation_candidate(unit, row)


def _require_query_recovery_decision(
    unit: ProjectUnitOfWork,
    candidate: _LogicalOperationCandidate,
) -> None:
    try:
        deadline = _parse_deadline(candidate.deadline_at or "")
    except ValueError as exc:
        raise ProjectStoreError("remote operation query deadline is corrupt") from exc
    if deadline > now_utc() + _LOGICAL_OPERATION_MAX_LIFETIME:
        raise ProjectStoreError("remote operation query deadline is not bounded")
    recovery = plan_delivery_attempt_recovery(unit, attempt_id=candidate.attempt_id)
    if recovery.action is not RecoveryAction.QUERY_NATIVE_IDENTITY:
        raise ProjectStoreError(f"remote operation query is not authorized: {recovery.diagnostic}")
    if recovery.native_identity != _required_non_empty_metadata_string(candidate.metadata, "native_identity"):
        raise ProjectStoreError("remote operation query recovery identity does not match the durable attempt")


def _logical_operation_candidate(
    unit: ProjectUnitOfWork,
    row: Any,
) -> _LogicalOperationCandidate:
    attempt_id = str(row[0])
    metadata = _logical_operation_metadata(attempt_id, row[3])
    state = DeliveryAttemptState(str(row[1]))
    repeatability = LogicalOperationRepeatability(_required_non_empty_metadata_string(metadata, "logical_operation_repeatability"))
    write_kind = _required_non_empty_metadata_string(metadata, "write_kind")
    semantic_key = _required_non_empty_metadata_string(metadata, "logical_operation_semantic_key")
    _required_non_empty_metadata_string(metadata, "native_identity")
    expected_attempt_id = _expected_logical_operation_attempt_id(
        project_uuid=unit.project_uuid.storage_token,
        write_kind=write_kind,
        semantic_key=semantic_key,
        repeatability=repeatability,
        attempt_id=attempt_id,
    )
    if expected_attempt_id != attempt_id:
        raise ProjectStoreError("logical operation semantic identity does not match durable attempt identity")
    _required_non_empty_metadata_string(metadata, "payload_reference")
    return _LogicalOperationCandidate(
        attempt_id=attempt_id,
        state=state,
        payload_hash=str(row[2]) if row[2] is not None else None,
        deadline_at=str(row[4]) if row[4] is not None else None,
        reconciliation_policy=str(row[5]) if row[5] is not None else None,
        metadata=metadata,
        epoch_id=int(row[6]) if row[6] is not None else None,
        consent_generation=int(row[7]) if row[7] is not None else None,
        target_generation=int(row[8]) if row[8] is not None else None,
        admission_generation=str(row[9]) if row[9] is not None else None,
        binding_audience=str(row[10]) if row[10] is not None else None,
    )


def _logical_operation_metadata(attempt_id: str, raw_value: object) -> dict[str, Any]:
    if not attempt_id.startswith(_LOGICAL_OPERATION_PREFIX):
        raise ProjectStoreError("attempt is not a logical operation")
    metadata = _read_projection_metadata(raw_value)
    if metadata.get("logical_operation_schema") != _LOGICAL_OPERATION_SCHEMA:
        raise ProjectStoreError("logical operation metadata has an unsupported schema")
    return metadata


def _required_non_empty_metadata_string(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectStoreError(f"logical operation metadata field {key} must be a non-empty string")
    return value


def _optional_non_empty_metadata_string(metadata: dict[str, Any], key: str) -> str | None:
    if key not in metadata:
        return None
    return _required_non_empty_metadata_string(metadata, key)


def _validate_logical_operation_request(
    request: LogicalOperationRequest,
) -> ReconciliationPolicy:
    if not isinstance(request.repeatability, LogicalOperationRepeatability):
        raise TypeError("repeatability must be a LogicalOperationRepeatability")
    if not isinstance(request.recover_with_persisted_deadline, bool):
        raise TypeError("recover_with_persisted_deadline must be a bool")
    if request.requested_native_identity is not None and (not isinstance(request.requested_native_identity, str) or not request.requested_native_identity.strip()):
        raise TypeError("requested_native_identity must be a non-empty string or None")
    if request.collaborative_teamspace_id is not None and (
        not isinstance(request.collaborative_teamspace_id, str) or not request.collaborative_teamspace_id.strip()
    ):
        raise TypeError("collaborative_teamspace_id must be a non-empty string or None")
    _require_non_empty(
        write_kind=request.write_kind,
        semantic_key=request.semantic_key,
        payload_hash=request.payload_hash,
        payload_reference=request.payload_reference,
        reconciliation_policy=request.reconciliation_policy,
        deadline_at=request.deadline_at,
    )
    try:
        policy = ReconciliationPolicy(request.reconciliation_policy)
    except ValueError as exc:
        raise ValueError("reconciliation_policy must name a supported policy") from exc
    _parse_deadline(request.deadline_at)
    return policy


def _validate_new_logical_operation_deadline(deadline_at: str, *, now: datetime) -> None:
    deadline = _parse_deadline(deadline_at)
    if deadline <= now or deadline > now + _LOGICAL_OPERATION_MAX_LIFETIME:
        raise ValueError("logical operation deadline must be future and bounded to one hour")


def _logical_operation_digest(
    *,
    project_uuid: str,
    write_kind: str,
    semantic_key: str,
    repeatability: LogicalOperationRepeatability,
) -> str:
    raw = "\x1f".join((project_uuid, write_kind, semantic_key, repeatability.value))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()  # noqa: TID251 - native idempotency identity, not charter content


def _new_logical_operation_identity(
    *,
    project_uuid: str,
    request: LogicalOperationRequest,
) -> tuple[str, str]:
    digest = _logical_operation_digest(
        project_uuid=project_uuid,
        write_kind=request.write_kind,
        semantic_key=request.semantic_key,
        repeatability=request.repeatability,
    )
    if request.repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE:
        attempt_id = f"{_LOGICAL_OPERATION_PREFIX}write:{digest}"
    else:
        attempt_id = f"{_LOGICAL_OPERATION_PREFIX}read:{digest}:{uuid4()}"
    return attempt_id, request.requested_native_identity or attempt_id


def _logical_attempt_id_may_match_request(
    *,
    project_uuid: str,
    request: LogicalOperationRequest,
    attempt_id: str,
) -> bool:
    digest = _logical_operation_digest(
        project_uuid=project_uuid,
        write_kind=request.write_kind,
        semantic_key=request.semantic_key,
        repeatability=request.repeatability,
    )
    if request.repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE:
        return attempt_id == f"{_LOGICAL_OPERATION_PREFIX}write:{digest}"
    return attempt_id.startswith(f"{_LOGICAL_OPERATION_PREFIX}read:{digest}:")


def _expected_logical_operation_attempt_id(
    *,
    project_uuid: str,
    write_kind: str,
    semantic_key: str,
    repeatability: LogicalOperationRepeatability,
    attempt_id: str,
) -> str:
    digest = _logical_operation_digest(
        project_uuid=project_uuid,
        write_kind=write_kind,
        semantic_key=semantic_key,
        repeatability=repeatability,
    )
    if repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE:
        return f"{_LOGICAL_OPERATION_PREFIX}write:{digest}"
    prefix = f"{_LOGICAL_OPERATION_PREFIX}read:{digest}:"
    if not attempt_id.startswith(prefix):
        return ""
    identifier = attempt_id.removeprefix(prefix)
    try:
        parsed = UUID(identifier)
    except (ValueError, AttributeError):
        return ""
    if parsed.version != 4:
        return ""
    return attempt_id


def _logical_operation_authority_diagnostic(
    *,
    candidate: _LogicalOperationCandidate,
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
) -> str | None:
    target = context.target_audience
    if target is None:
        return "logical operation live authority has no admitted target; operator review required"
    expected = {
        "project_uuid": unit.project_uuid.storage_token,
        "store_database_path": str(context.store_identity.database_path),
        "store_schema_version": str(context.store_identity.schema_version),
        "store_layout_version": str(context.store_identity.layout_version),
        "epoch_id": str(context.epoch_id),
        "consent_generation": str(context.consent_generation),
        "target_identity": target.target_identity,
        "account_identity": target.account_identity,
        "private_teamspace_id": target.private_teamspace_id,
        "target_generation": str(target.configuration_generation),
        "admission_generation": str(context.admission_generation),
        "binding_audience": str(context.binding_audience),
    }
    persisted_columns = {
        "epoch_id": str(candidate.epoch_id),
        "consent_generation": str(candidate.consent_generation),
        "target_generation": str(candidate.target_generation),
        "admission_generation": str(candidate.admission_generation),
        "binding_audience": str(candidate.binding_audience),
    }
    for key, expected_value in expected.items():
        if candidate.metadata.get(key) != expected_value:
            return f"logical operation authority drift for {key}; operator review required"
    for key, persisted_value in persisted_columns.items():
        if persisted_value != expected[key]:
            return f"logical operation persisted authority drift for {key}; operator review required"
    return None


def _logical_result(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
) -> tuple[DeliveryOutcome | None, str | None]:
    row = unit.execute(
        "SELECT outcome, terminal_refusal_category FROM delivery_results "
        "WHERE project_uuid = ? AND attempt_id = ? ORDER BY recorded_at DESC, result_id DESC LIMIT 1",
        (unit.project_uuid.storage_token, attempt_id),
    ).fetchone()
    if row is None:
        return None, None
    try:
        outcome = DeliveryOutcome(str(row[0]))
    except ValueError as exc:
        raise ProjectStoreError("logical operation result has an unsupported outcome") from exc
    category = str(row[1]) if row[1] is not None else None
    if category is not None and not category.strip():
        raise ProjectStoreError("logical operation result has an empty refusal category")
    return outcome, category


def _logical_remote_operation_id(candidate: _LogicalOperationCandidate) -> str | None:
    return _optional_non_empty_metadata_string(candidate.metadata, "remote_operation_id")


def _logical_recovery_decision(
    unit: ProjectUnitOfWork,
    request: LogicalOperationRequest,
    candidate: _LogicalOperationCandidate,
    *,
    now: datetime,
) -> LogicalOperationDecision:
    try:
        deadline = _parse_deadline(candidate.deadline_at or "")
    except ValueError as exc:
        return _logical_operator_review_for_candidate(
            unit,
            request,
            candidate,
            diagnostic=f"logical operation deadline is corrupt: {exc}",
        )
    if deadline > now + _LOGICAL_OPERATION_MAX_LIFETIME:
        return _logical_operator_review_for_candidate(
            unit,
            request,
            candidate,
            diagnostic="logical operation persisted deadline is not bounded",
        )
    recovery = plan_delivery_attempt_recovery(unit, attempt_id=candidate.attempt_id, now=now)
    outcome, category = _logical_result(unit, attempt_id=candidate.attempt_id)
    disposition = LogicalOperationDisposition.OPERATOR_REVIEW
    may_resend = False
    may_query = False
    requires_review = True
    if candidate.state is DeliveryAttemptState.PREPARED and recovery.action is RecoveryAction.RETRY_NATIVE_IDENTITY and recovery.may_resend:
        disposition = LogicalOperationDisposition.PREPARED_RETRY
        may_resend = True
        requires_review = False
    elif candidate.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT and recovery.action is RecoveryAction.RETRY_NATIVE_IDENTITY and recovery.may_resend:
        disposition = LogicalOperationDisposition.RETRYABLE_RESTART
        may_resend = True
        requires_review = False
    elif recovery.action is RecoveryAction.QUERY_NATIVE_IDENTITY:
        disposition = LogicalOperationDisposition.QUERY_NATIVE
        may_query = True
        requires_review = False
    return LogicalOperationDecision(
        disposition=disposition,
        attempt_id=candidate.attempt_id,
        native_identity=recovery.native_identity,
        state=candidate.state,
        outcome=outcome,
        terminal_refusal_category=category,
        repeatability=request.repeatability,
        may_resend=may_resend,
        may_query=may_query,
        requires_operator_review=requires_review,
        remote_operation_id=_logical_remote_operation_id(candidate),
        deadline_at=candidate.deadline_at,
        diagnostic=recovery.diagnostic,
    )


def _logical_terminal_prior_decision(
    unit: ProjectUnitOfWork,
    request: LogicalOperationRequest,
    candidate: _LogicalOperationCandidate,
) -> LogicalOperationDecision:
    try:
        outcome, category = _logical_result(unit, attempt_id=candidate.attempt_id)
        remote_operation_id = _logical_remote_operation_id(candidate)
    except ProjectStoreError as exc:
        return _logical_operator_review(
            request,
            attempt_id=candidate.attempt_id,
            native_identity=candidate.metadata.get("native_identity") if isinstance(candidate.metadata.get("native_identity"), str) else None,
            state=candidate.state,
            deadline_at=candidate.deadline_at,
            diagnostic=str(exc),
        )
    if candidate.state in {DeliveryAttemptState.SUCCEEDED, DeliveryAttemptState.REFUSED, DeliveryAttemptState.TERMINAL_UNKNOWN} and outcome is None:
        return _logical_operator_review_for_candidate(
            unit,
            request,
            candidate,
            diagnostic="terminal logical operation is missing its durable result",
        )
    return LogicalOperationDecision(
        disposition=LogicalOperationDisposition.TERMINAL_PRIOR,
        attempt_id=candidate.attempt_id,
        native_identity=_required_non_empty_metadata_string(candidate.metadata, "native_identity"),
        state=candidate.state,
        outcome=outcome,
        terminal_refusal_category=category,
        repeatability=request.repeatability,
        may_resend=False,
        may_query=False,
        requires_operator_review=False,
        remote_operation_id=remote_operation_id,
        deadline_at=candidate.deadline_at,
        diagnostic="idempotent logical operation already has terminal durable history",
        terminal_response_reference=_optional_non_empty_metadata_string(
            candidate.metadata,
            "terminal_response_reference",
        ),
        terminal_refusal_reference=_optional_non_empty_metadata_string(
            candidate.metadata,
            "terminal_refusal_reference",
        ),
    )


def _logical_operator_review_for_candidate(
    unit: ProjectUnitOfWork,
    request: LogicalOperationRequest,
    candidate: _LogicalOperationCandidate,
    *,
    diagnostic: str,
) -> LogicalOperationDecision:
    try:
        outcome, category = _logical_result(unit, attempt_id=candidate.attempt_id)
        remote_operation_id = _logical_remote_operation_id(candidate)
    except ProjectStoreError:
        outcome, category, remote_operation_id = None, None, None
    native = candidate.metadata.get("native_identity")
    return LogicalOperationDecision(
        disposition=LogicalOperationDisposition.OPERATOR_REVIEW,
        attempt_id=candidate.attempt_id,
        native_identity=native if isinstance(native, str) and native.strip() else None,
        state=candidate.state,
        outcome=outcome,
        terminal_refusal_category=category,
        repeatability=request.repeatability,
        may_resend=False,
        may_query=False,
        requires_operator_review=True,
        remote_operation_id=remote_operation_id,
        deadline_at=candidate.deadline_at,
        diagnostic=diagnostic,
    )


def _logical_operator_review(
    request: LogicalOperationRequest,
    *,
    attempt_id: str,
    native_identity: str | None,
    state: DeliveryAttemptState | None,
    deadline_at: str | None,
    diagnostic: str,
) -> LogicalOperationDecision:
    return LogicalOperationDecision(
        disposition=LogicalOperationDisposition.OPERATOR_REVIEW,
        attempt_id=attempt_id,
        native_identity=native_identity,
        state=state,
        outcome=None,
        terminal_refusal_category=None,
        repeatability=request.repeatability,
        may_resend=False,
        may_query=False,
        requires_operator_review=True,
        remote_operation_id=None,
        deadline_at=deadline_at,
        diagnostic=diagnostic,
    )


def _terminalize_orphaned_attempt(
    unit: ProjectUnitOfWork,
    *,
    attempt_id: str,
    reason: str,
) -> None:
    """Irreversibly settle an uncertain attempt when opt-out wins the race."""
    _require_non_empty(attempt_id=attempt_id, reason=reason)
    row = unit.execute(
        "SELECT epoch_id, target_generation, admission_generation FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ? AND state IN (?, ?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            attempt_id,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.PENDING_REMOTE.value,
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
        "(result_id, project_uuid, epoch_id, attempt_id, target_generation, "
        "admission_generation, outcome, terminal_refusal_category, recorded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            f"{attempt_id}:terminal-unknown",
            unit.project_uuid.storage_token,
            int(cast("str | int | float | bytes", row[0])),
            attempt_id,
            int(row[1]) if row[1] is not None else None,
            str(row[2]) if row[2] is not None else None,
            DeliveryOutcome.TERMINAL_UNKNOWN.value,
            reason,
            _now(),
        ),
    )


def settle_attempts_for_opt_out(
    store: ProjectSyncStore,
    *,
    reason: str,
    lock_timeout_seconds: float = 5.0,
) -> OptOutSettlement:
    """Cancel not-started attempts and terminalize started/uncertain orphans.

    Settlement owns the bounded cross-process lease wait. If a live worker holds
    the project transport lease, this call waits for that worker to commit its
    genuine result and release. Once this call acquires the lease, any residual
    started/unknown row is an orphan and is fenced as ``terminal_unknown`` before
    opt-out returns. If the holder remains live past the caller's bounded wait,
    every still-live started/unknown row is atomically fenced under the opt-out
    settlement deadline without the transport lease; later result recording
    still fails because terminal rows are not recoverable result targets.
    """
    _require_non_empty(reason=reason)
    if lock_timeout_seconds < 0:
        raise ValueError("lock_timeout_seconds cannot be negative")
    try:
        with acquire_project_transport_lease(
            store,
            lock_timeout_seconds=lock_timeout_seconds,
        ) as lease:
            return settle_attempts_for_opt_out_under_lease(lease, reason=reason)
    except ProjectStoreLockedError:
        with store.unit_of_work() as unit:
            return _settle_open_unit(unit, reason=reason)


def settle_attempts_for_opt_out_under_lease(
    lease: TransportLeaseContext,
    *,
    reason: str,
) -> OptOutSettlement:
    """Settle attempts while the caller continuously owns the project lease.

    Revocation uses this seam after persisting refusal under the same lease.  It
    deliberately does not rebuild an egress-eligible context: refusal has already
    made new disclosure ineligible, while the still-live lease proves that no new
    transport start can cross the decision/settlement boundary.
    """
    _require_non_empty(reason=reason)
    if not transport_lease_context_is_live(lease):
        raise ProjectStoreError("opt-out settlement requires a live project transport lease")
    with lease.store.unit_of_work() as unit:
        return _settle_open_unit(unit, reason=reason)


def _settle_open_unit(
    unit: ProjectUnitOfWork,
    *,
    reason: str,
) -> OptOutSettlement:
    cancelable_rows = unit.execute(
        "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? AND state IN (?, ?)",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.RETRYABLE_NO_EFFECT.value,
        ),
    ).fetchall()
    unit.execute(
        "UPDATE delivery_attempts SET state = ?, reconciliation_policy = ? WHERE project_uuid = ? AND state IN (?, ?)",
        (
            DeliveryAttemptState.CANCELED.value,
            f"canceled:{reason}",
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.RETRYABLE_NO_EFFECT.value,
        ),
    )
    orphan_rows = unit.execute(
        "SELECT attempt_id, deadline_at FROM delivery_attempts WHERE project_uuid = ? AND state IN (?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.PENDING_REMOTE.value,
            DeliveryAttemptState.UNKNOWN.value,
        ),
    ).fetchall()
    terminalized = 0
    for row in orphan_rows:
        _parse_deadline(str(row[1]) if row[1] is not None else "")
        refreshed = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (unit.project_uuid.storage_token, str(row[0])),
        ).fetchone()
        if refreshed is None:
            continue
        refreshed_state = DeliveryAttemptState(str(refreshed[0]))
        if refreshed_state not in {DeliveryAttemptState.IN_FLIGHT, DeliveryAttemptState.PENDING_REMOTE, DeliveryAttemptState.UNKNOWN}:
            continue
        _terminalize_orphaned_attempt(unit, attempt_id=str(row[0]), reason=reason)
        terminalized += 1
    return OptOutSettlement(
        canceled_before_transport=len(cancelable_rows),
        terminalized_orphans=terminalized,
        waiting_live_attempts=0,
    )


def recover_delivery_attempts(unit: ProjectUnitOfWork) -> list[DeliveryAttemptRecord]:
    """Return recoverable attempts without inventing a new native identity."""
    records: list[DeliveryAttemptRecord] = []
    for row in unit.execute(
        "SELECT attempt_id, state, payload_reference, payload_hash, reconciliation_policy "
        "FROM delivery_attempts WHERE project_uuid = ? AND state IN (?, ?, ?, ?, ?, ?)",
        (
            unit.project_uuid.storage_token,
            DeliveryAttemptState.PREPARED.value,
            DeliveryAttemptState.IN_FLIGHT.value,
            DeliveryAttemptState.PENDING_REMOTE.value,
            DeliveryAttemptState.RETRYABLE_NO_EFFECT.value,
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
    if require_lease and not transport_lease_identity_is_live_for_project(
        context.transport_lease_identity,
        unit.project_uuid,
    ):
        raise ProjectStoreError("transport/result operation requires a live project transport lease")


def _attempt_metadata(
    spec: DeliveryAttemptSpec,
    *,
    context: ProjectSyncContext,
    unit: ProjectUnitOfWork,
    reconciliation_policy: ReconciliationPolicy,
) -> dict[str, str]:
    target = context.target_audience
    if target is None:
        raise ProjectStoreError("delivery attempt requires an admitted target audience")
    metadata = {
        "payload_reference": spec.payload_reference,
        "write_kind": spec.write_kind,
        "native_identity": spec.native_identity,
        "project_uuid": unit.project_uuid.storage_token,
        "store_database_path": str(context.store_identity.database_path),
        "store_schema_version": str(context.store_identity.schema_version),
        "store_layout_version": str(context.store_identity.layout_version),
        "epoch_id": str(context.epoch_id),
        "consent_generation": str(context.consent_generation),
        "target_identity": target.target_identity,
        "account_identity": target.account_identity,
        "private_teamspace_id": target.private_teamspace_id,
        "target_generation": str(target.configuration_generation),
        "admission_generation": str(context.admission_generation),
        "binding_audience": str(context.binding_audience),
        "deadline_at": spec.deadline_at,
        "reconciliation_policy": reconciliation_policy.value,
    }
    if spec.logical_operation_semantic_key is not None:
        metadata["logical_operation_schema"] = _LOGICAL_OPERATION_SCHEMA
        metadata["logical_operation_semantic_key"] = spec.logical_operation_semantic_key
    if spec.logical_operation_repeatability is not None:
        metadata["logical_operation_repeatability"] = spec.logical_operation_repeatability
    if spec.logical_operation_collaborative_teamspace_id is not None:
        metadata["collaborative_teamspace_id"] = spec.logical_operation_collaborative_teamspace_id
    return metadata


def _validate_logical_operation_namespace(
    *,
    unit: ProjectUnitOfWork,
    spec: DeliveryAttemptSpec,
) -> None:
    reserved_identity = spec.attempt_id.startswith(_LOGICAL_OPERATION_PREFIX)
    has_semantic_key = spec.logical_operation_semantic_key is not None
    has_repeatability = spec.logical_operation_repeatability is not None
    if has_semantic_key != has_repeatability:
        raise ProjectStoreError("logical operation metadata requires both semantic key and repeatability")
    if not reserved_identity:
        if has_semantic_key:
            raise ProjectStoreError("logical operation metadata requires a reserved logical-operation identity")
        return
    if not has_semantic_key:
        raise ProjectStoreError("reserved logical-operation identity requires logical operation metadata")
    if spec.logical_operation_collaborative_teamspace_id is not None and not spec.logical_operation_collaborative_teamspace_id.strip():
        raise ProjectStoreError("logical operation Collaborative Teamspace id must be non-empty")
    semantic_key = spec.logical_operation_semantic_key
    repeatability_value = spec.logical_operation_repeatability
    if semantic_key is None or not semantic_key.strip():
        raise ProjectStoreError("logical operation semantic key must be a non-empty string")
    try:
        repeatability = LogicalOperationRepeatability(str(repeatability_value))
    except ValueError as exc:
        raise ProjectStoreError("logical operation repeatability is invalid") from exc
    expected_attempt_id = _expected_logical_operation_attempt_id(
        project_uuid=unit.project_uuid.storage_token,
        write_kind=spec.write_kind,
        semantic_key=semantic_key,
        repeatability=repeatability,
        attempt_id=spec.attempt_id,
    )
    if expected_attempt_id != spec.attempt_id:
        raise ProjectStoreError("logical operation identity is not derived from its semantic metadata")


def _assert_native_identity_available_for_prepare(
    *,
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
    spec: DeliveryAttemptSpec,
    metadata: dict[str, str],
) -> None:
    """Reserve the target-authority ``(write_kind, native_identity)`` scope.

    SaaS-native correlation keys such as Event ``event_id`` are scoped by the
    admitted target authority on the wire.  The same Event may therefore be
    delivered to a distinct target, while a second attempt under the same exact
    target tuple must recover the original attempt.  Attempt ID and payload
    reference retain the logical/project/target uniqueness without inventing a
    native identity SaaS cannot return.
    """
    for row in unit.execute(
        "SELECT attempt_id, state, payload_hash, payload_reference FROM delivery_attempts WHERE project_uuid = ?",
        (unit.project_uuid.storage_token,),
    ):
        existing_attempt_id = str(row[0])
        existing_metadata = _metadata_from_payload_reference(row[3])
        diagnostic = _metadata_required_identity_diagnostic(existing_metadata, payload_hash=str(row[2]) if row[2] is not None else None)
        if diagnostic is not None:
            raise ProjectStoreError("existing delivery attempt metadata requires operator repair before native identity admission")
        if existing_attempt_id == spec.attempt_id:
            _assert_metadata_tuple_matches(
                metadata=existing_metadata,
                payload_hash=str(row[2]) if row[2] is not None else None,
                context=context,
                unit=unit,
            )
            if existing_metadata["write_kind"] != spec.write_kind:
                raise ProjectStoreError("delivery attempt already exists with a different write kind")
            if existing_metadata["native_identity"] != spec.native_identity:
                raise ProjectStoreError("delivery attempt already exists with a different native identity")
            if str(row[2]) != spec.payload_hash:
                raise ProjectStoreError("delivery attempt already exists with a different payload hash")
            if existing_metadata.get("payload_reference") != metadata["payload_reference"]:
                raise ProjectStoreError("delivery attempt already exists with a different payload reference")
            raise ProjectStoreError("delivery attempt already exists; recover the original attempt")
        native_scope_fields = (
            "target_identity",
            "account_identity",
            "private_teamspace_id",
            "target_generation",
            "admission_generation",
            "binding_audience",
        )
        same_native_scope = all(existing_metadata[field] == metadata[field] for field in native_scope_fields)
        if existing_metadata["write_kind"] == spec.write_kind and existing_metadata["native_identity"] == spec.native_identity and same_native_scope:
            raise ProjectStoreError("native transport identity already belongs to another delivery attempt")


def _metadata_required_identity_diagnostic(
    metadata: dict[str, str],
    *,
    payload_hash: str | None,
) -> str | None:
    for key in _REQUIRED_METADATA_FIELDS:
        value = metadata.get(key)
        if value is None or not value.strip():
            return f"delivery attempt metadata is missing required {key}; operator repair required"
    if payload_hash is None or not payload_hash.strip():
        return "delivery attempt metadata is missing required payload_hash; operator repair required"
    return None


def _recovery_metadata_diagnostic(
    *,
    row: object,
    metadata: dict[str, str],
) -> str | None:
    diagnostic = _metadata_required_identity_diagnostic(
        metadata,
        payload_hash=str(row[4]) if row[4] is not None else None,  # type: ignore[index]
    )
    if diagnostic is not None:
        return diagnostic
    expected = {
        "epoch_id": str(row[5]),  # type: ignore[index]
        "consent_generation": str(row[6]),  # type: ignore[index]
        "target_generation": str(row[7]),  # type: ignore[index]
        "admission_generation": str(row[8]),  # type: ignore[index]
        "binding_audience": str(row[9]),  # type: ignore[index]
    }
    for key, expected_value in expected.items():
        if metadata.get(key) != expected_value:
            return "delivery attempt metadata authority tuple is inconsistent; operator repair required"
    return None


def _assert_metadata_tuple_matches(
    *,
    metadata: dict[str, str],
    payload_hash: str | None,
    context: ProjectSyncContext,
    unit: ProjectUnitOfWork,
) -> None:
    target = context.target_audience
    if target is None:
        raise ProjectStoreError("delivery attempt requires an admitted target audience")
    expected = {
        "project_uuid": unit.project_uuid.storage_token,
        "store_database_path": str(context.store_identity.database_path),
        "store_schema_version": str(context.store_identity.schema_version),
        "store_layout_version": str(context.store_identity.layout_version),
        "epoch_id": str(context.epoch_id),
        "consent_generation": str(context.consent_generation),
        "target_identity": target.target_identity,
        "account_identity": target.account_identity,
        "private_teamspace_id": target.private_teamspace_id,
        "target_generation": str(target.configuration_generation),
        "admission_generation": str(context.admission_generation),
        "binding_audience": str(context.binding_audience),
        "payload_hash": payload_hash or "",
    }
    for key, expected_value in expected.items():
        if key == "payload_hash":
            if not expected_value.strip():
                raise ProjectStoreError("native transport identity already belongs to an invalid payload")
            continue
        if metadata.get(key) != expected_value:
            raise ProjectStoreError("native transport identity already belongs to a different authority")


def _metadata_from_payload_reference(raw_value: object) -> dict[str, str]:
    if not isinstance(raw_value, str):
        return {}
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    metadata: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            continue
        metadata[key] = item
    return metadata


def _validate_result_category(
    *,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None,
) -> None:
    has_category = terminal_refusal_category is not None and bool(terminal_refusal_category.strip())
    if outcome is DeliveryOutcome.REFUSED and not has_category:
        raise ProjectStoreError("refused delivery result requires a terminal refusal category")
    if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE} and terminal_refusal_category is not None:
        raise ProjectStoreError("successful delivery result cannot include a terminal refusal category")


def _assert_result_upsert_allowed(
    *,
    existing_result: object,
    row: object,
    attempt_id: str,
    outcome: DeliveryOutcome,
    terminal_refusal_category: str | None,
) -> None:
    """Allow only idempotent stable-result writes or nonterminal convergence."""
    if str(existing_result[0]) != attempt_id:  # type: ignore[index]
        raise ProjectStoreError("delivery result id already belongs to another attempt")
    expected = {
        "epoch_id": str(row[0]),  # type: ignore[index]
        "target_generation": str(row[2]),  # type: ignore[index]
        "admission_generation": str(row[3]),  # type: ignore[index]
    }
    actual = {
        "epoch_id": str(existing_result[1]),  # type: ignore[index]
        "target_generation": str(existing_result[2]),  # type: ignore[index]
        "admission_generation": str(existing_result[3]),  # type: ignore[index]
    }
    if actual != expected:
        raise ProjectStoreError("delivery result id already belongs to another authority tuple")
    existing_outcome = DeliveryOutcome(str(existing_result[4]))  # type: ignore[index]
    existing_category = str(existing_result[5]) if existing_result[5] is not None else None  # type: ignore[index]
    if existing_outcome is outcome and existing_category == terminal_refusal_category:
        return
    terminal = {
        DeliveryOutcome.DELIVERED,
        DeliveryOutcome.DUPLICATE,
        DeliveryOutcome.REFUSED,
        DeliveryOutcome.TERMINAL_UNKNOWN,
    }
    recoverable = {
        DeliveryOutcome.PENDING,
        DeliveryOutcome.RETRYABLE_NO_EFFECT,
        DeliveryOutcome.UNKNOWN,
    }
    if existing_outcome in recoverable and outcome in (recoverable | terminal):
        return
    raise ProjectStoreError("delivery result id already records a conflicting outcome")


def _require_non_empty(**values: str) -> None:
    for name, value in values.items():
        if not value.strip():
            raise ValueError(f"{name} must be non-empty")


def _assert_attempt_authority_matches_context(
    *,
    row: object,
    unit: ProjectUnitOfWork,
    context: ProjectSyncContext,
) -> None:
    target = context.target_audience
    if target is None:
        raise ProjectStoreError("delivery attempt requires an admitted target audience")
    epoch_id = int(row[0])  # type: ignore[index]
    consent_generation = int(row[1])  # type: ignore[index]
    target_generation = int(row[2])  # type: ignore[index]
    admission_generation = str(row[3])  # type: ignore[index]
    binding_audience = str(row[4])  # type: ignore[index]
    metadata = _metadata_from_payload_reference(row[5])  # type: ignore[index]
    expected = {
        "project_uuid": unit.project_uuid.storage_token,
        "store_database_path": str(context.store_identity.database_path),
        "store_schema_version": str(context.store_identity.schema_version),
        "store_layout_version": str(context.store_identity.layout_version),
        "epoch_id": str(context.epoch_id),
        "consent_generation": str(context.consent_generation),
        "target_identity": target.target_identity,
        "account_identity": target.account_identity,
        "private_teamspace_id": target.private_teamspace_id,
        "target_generation": str(target.configuration_generation),
        "admission_generation": str(context.admission_generation),
        "binding_audience": str(context.binding_audience),
    }
    persisted = {
        "epoch_id": str(epoch_id),
        "consent_generation": str(consent_generation),
        "target_generation": str(target_generation),
        "admission_generation": admission_generation,
        "binding_audience": binding_audience,
    }
    expected.update(persisted)
    for key, expected_value in expected.items():
        if metadata.get(key) != expected_value:
            raise ProjectStoreError("delivery attempt authority no longer matches the live transport lease")
    if (
        epoch_id != context.epoch_id
        or consent_generation != context.consent_generation
        or target_generation != target.configuration_generation
        or admission_generation != context.admission_generation
        or binding_audience != context.binding_audience
    ):
        raise ProjectStoreError("delivery attempt authority no longer matches the live transport lease")


def _parse_deadline(value: str) -> datetime:
    if not value.strip():
        raise ValueError("deadline_at must be non-empty")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    deadline = datetime.fromisoformat(normalized)
    if deadline.tzinfo is None:
        raise ValueError("deadline_at must include timezone")
    return deadline.astimezone(UTC)


def _parse_reconciliation_policy(value: str) -> ReconciliationPolicy:
    try:
        return ReconciliationPolicy(value.strip())
    except ValueError:
        return ReconciliationPolicy.OPERATOR_REVIEW


def _now() -> str:
    return now_utc_iso()


__all__ = [
    "DeliveryAttemptProjection",
    "DeliveryAttemptSpec",
    "DeliveryAttemptState",
    "DeliveryOutcome",
    "DeliveryTerminalResultProjection",
    "DeliveryTerminalResultStatus",
    "LogicalOperationDecision",
    "LogicalOperationDisposition",
    "LogicalOperationRepeatability",
    "LogicalOperationRequest",
    "RecoveryAction",
    "allocate_logical_delivery_operation",
    "attach_remote_operation_id",
    "execute_remote_operation_query_under_lease",
    "mark_transport_started",
    "mark_delivery_result_unknown",
    "get_delivery_attempt_record",
    "get_delivery_terminal_result_projection",
    "list_delivery_attempt_projections",
    "plan_delivery_attempt_recovery",
    "prepare_delivery_attempt",
    "record_delivery_result",
    "record_logical_operation_result",
    "restart_delivery_attempt",
    "settle_attempts_for_opt_out",
    "settle_attempts_for_opt_out_under_lease",
]
