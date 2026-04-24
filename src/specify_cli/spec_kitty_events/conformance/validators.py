"""Dual-layer validation for spec-kitty-events contracts.

This module provides conformance validation combining:
1. Pydantic model validation (primary layer)
2. JSON Schema validation (optional secondary layer)

The validator gracefully degrades if jsonschema is unavailable, unless
strict=True is specified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Type, Union

from pydantic import ValidationError as PydanticValidationError
from ..cutover import assert_canonical_cutover_signal

from ..gates import GateFailedPayload, GatePassedPayload
from ..lifecycle import (
    MissionClosedPayload,
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionCreatedPayload,
    MissionStartedPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
)
from ..models import Event
from ..status import StatusTransitionPayload
from ..collaboration import (
    ParticipantInvitedPayload,
    ParticipantJoinedPayload,
    ParticipantLeftPayload,
    PresenceHeartbeatPayload,
    DriveIntentSetPayload,
    FocusChangedPayload,
    PromptStepExecutionStartedPayload,
    PromptStepExecutionCompletedPayload,
    ConcurrentDriverWarningPayload,
    PotentialStepCollisionDetectedPayload,
    WarningAcknowledgedPayload,
    CommentPostedPayload,
    DecisionCapturedPayload,
    SessionLinkedPayload,
)
from ..glossary import (
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    SemanticCheckEvaluatedPayload,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GlossarySenseUpdatedPayload,
    GenerationBlockedBySemanticConflictPayload,
    GlossaryStrictnessSetPayload,
)
from ..mission_next import (
    MissionRunStartedPayload,
    NextStepIssuedPayload,
    NextStepAutoCompletedPayload,
    DecisionInputRequestedPayload,
    DecisionInputAnsweredPayload,
    MissionRunCompletedPayload,
)
from ..analytics import (
    TokenUsageRecordedPayload,
    DiffSummaryRecordedPayload,
)
from ..dossier import (
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
)
from ..mission_audit import (
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
)
from ..decisionpoint import (
    DecisionPointOpenedPayload,
    DecisionPointDiscussingPayload,
    DecisionPointResolvedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointWidenedPayload,
)
from ..connector import (
    ConnectorProvisionedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorDegradedPayload,
    ConnectorRevokedPayload,
    ConnectorReconnectedPayload,
)
from ..sync import (
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncRetryScheduledPayload,
    SyncDeadLetteredPayload,
    SyncReplayCompletedPayload,
    ExternalReferenceLinkedPayload,
)
from ..profile_invocation import (
    ProfileInvocationStartedPayload,
)
from ..retrospective import (
    RetrospectiveCompletedPayload,
    RetrospectiveSkippedPayload,
)


@dataclass(frozen=True)
class ModelViolation:
    """A violation detected by Pydantic model validation."""

    field: str
    message: str
    violation_type: str
    input_value: object


@dataclass(frozen=True)
class SchemaViolation:
    """A violation detected by JSON Schema validation."""

    json_path: str
    message: str
    validator: str
    validator_value: object
    schema_path: Tuple[Union[str, int], ...]


@dataclass(frozen=True)
class ConformanceResult:
    """Result of dual-layer conformance validation."""

    valid: bool
    model_violations: Tuple[ModelViolation, ...]
    schema_violations: Tuple[SchemaViolation, ...]
    schema_check_skipped: bool
    event_type: str


# Event type to Pydantic model mapping
_EVENT_TYPE_TO_MODEL: Dict[str, Any] = {
    "Event": Event,
    "WPStatusChanged": StatusTransitionPayload,
    "GatePassed": GatePassedPayload,
    "GateFailed": GateFailedPayload,
    "MissionCreated": MissionCreatedPayload,
    "MissionClosed": MissionClosedPayload,
    "MissionStarted": MissionStartedPayload,
    "MissionCompleted": MissionCompletedPayload,
    "MissionCancelled": MissionCancelledPayload,
    "PhaseEntered": PhaseEnteredPayload,
    "ReviewRollback": ReviewRollbackPayload,
    # Collaboration event contracts
    "ParticipantInvited": ParticipantInvitedPayload,
    "ParticipantJoined": ParticipantJoinedPayload,
    "ParticipantLeft": ParticipantLeftPayload,
    "PresenceHeartbeat": PresenceHeartbeatPayload,
    "DriveIntentSet": DriveIntentSetPayload,
    "FocusChanged": FocusChangedPayload,
    "PromptStepExecutionStarted": PromptStepExecutionStartedPayload,
    "PromptStepExecutionCompleted": PromptStepExecutionCompletedPayload,
    "ConcurrentDriverWarning": ConcurrentDriverWarningPayload,
    "PotentialStepCollisionDetected": PotentialStepCollisionDetectedPayload,
    "WarningAcknowledged": WarningAcknowledgedPayload,
    "CommentPosted": CommentPostedPayload,
    "DecisionCaptured": DecisionCapturedPayload,
    "SessionLinked": SessionLinkedPayload,
    # Glossary semantic integrity contracts
    "GlossaryScopeActivated": GlossaryScopeActivatedPayload,
    "TermCandidateObserved": TermCandidateObservedPayload,
    "SemanticCheckEvaluated": SemanticCheckEvaluatedPayload,
    "GlossaryClarificationRequested": GlossaryClarificationRequestedPayload,
    "GlossaryClarificationResolved": GlossaryClarificationResolvedPayload,
    "GlossarySenseUpdated": GlossarySenseUpdatedPayload,
    "GenerationBlockedBySemanticConflict": GenerationBlockedBySemanticConflictPayload,
    "GlossaryStrictnessSet": GlossaryStrictnessSetPayload,
    # Mission-next runtime contracts
    "MissionRunStarted": MissionRunStartedPayload,
    "NextStepIssued": NextStepIssuedPayload,
    "NextStepAutoCompleted": NextStepAutoCompletedPayload,
    "DecisionInputRequested": DecisionInputRequestedPayload,
    "DecisionInputAnswered": DecisionInputAnsweredPayload,
    "MissionRunCompleted": MissionRunCompletedPayload,
    # Analytics contracts (3.3.0)
    "TokenUsageRecorded": TokenUsageRecordedPayload,
    "DiffSummaryRecorded": DiffSummaryRecordedPayload,
    # Dossier event contracts
    "MissionDossierArtifactIndexed": MissionDossierArtifactIndexedPayload,
    "MissionDossierArtifactMissing": MissionDossierArtifactMissingPayload,
    "MissionDossierSnapshotComputed": MissionDossierSnapshotComputedPayload,
    "MissionDossierParityDriftDetected": MissionDossierParityDriftDetectedPayload,
    # Mission audit lifecycle contracts (2.5.0)
    "MissionAuditRequested": MissionAuditRequestedPayload,
    "MissionAuditStarted": MissionAuditStartedPayload,
    "MissionAuditDecisionRequested": MissionAuditDecisionRequestedPayload,
    "MissionAuditCompleted": MissionAuditCompletedPayload,
    "MissionAuditFailed": MissionAuditFailedPayload,
    # DecisionPoint lifecycle contracts (2.6.0 / V1 4.0.0)
    "DecisionPointOpened": DecisionPointOpenedPayload,
    "DecisionPointWidened": DecisionPointWidenedPayload,
    "DecisionPointDiscussing": DecisionPointDiscussingPayload,
    "DecisionPointResolved": DecisionPointResolvedPayload,
    "DecisionPointOverridden": DecisionPointOverriddenPayload,
    # Connector lifecycle contracts (2.7.0)
    "ConnectorProvisioned": ConnectorProvisionedPayload,
    "ConnectorHealthChecked": ConnectorHealthCheckedPayload,
    "ConnectorDegraded": ConnectorDegradedPayload,
    "ConnectorRevoked": ConnectorRevokedPayload,
    "ConnectorReconnected": ConnectorReconnectedPayload,
    # Sync lifecycle contracts (2.7.0)
    "SyncIngestAccepted": SyncIngestAcceptedPayload,
    "SyncIngestRejected": SyncIngestRejectedPayload,
    "SyncRetryScheduled": SyncRetryScheduledPayload,
    "SyncDeadLettered": SyncDeadLetteredPayload,
    "SyncReplayCompleted": SyncReplayCompletedPayload,
    "ExternalReferenceLinked": ExternalReferenceLinkedPayload,
    # Profile invocation contracts (3.1.0)
    "ProfileInvocationStarted": ProfileInvocationStartedPayload,
    # Retrospective contracts (3.1.0)
    "RetrospectiveCompleted": RetrospectiveCompletedPayload,
    "RetrospectiveSkipped": RetrospectiveSkippedPayload,
}

# Event type to JSON Schema name mapping (used with load_schema())
_EVENT_TYPE_TO_SCHEMA: Dict[str, str] = {
    "Event": "event",
    "WPStatusChanged": "status_transition_payload",
    "GatePassed": "gate_passed_payload",
    "GateFailed": "gate_failed_payload",
    "MissionCreated": "mission_created_payload",
    "MissionClosed": "mission_closed_payload",
    "MissionStarted": "mission_started_payload",
    "MissionCompleted": "mission_completed_payload",
    "MissionCancelled": "mission_cancelled_payload",
    "PhaseEntered": "phase_entered_payload",
    "ReviewRollback": "review_rollback_payload",
    # Collaboration event contracts
    "ParticipantInvited": "participant_invited_payload",
    "ParticipantJoined": "participant_joined_payload",
    "ParticipantLeft": "participant_left_payload",
    "PresenceHeartbeat": "presence_heartbeat_payload",
    "DriveIntentSet": "drive_intent_set_payload",
    "FocusChanged": "focus_changed_payload",
    "PromptStepExecutionStarted": "prompt_step_execution_started_payload",
    "PromptStepExecutionCompleted": "prompt_step_execution_completed_payload",
    "ConcurrentDriverWarning": "concurrent_driver_warning_payload",
    "PotentialStepCollisionDetected": "potential_step_collision_detected_payload",
    "WarningAcknowledged": "warning_acknowledged_payload",
    "CommentPosted": "comment_posted_payload",
    "DecisionCaptured": "decision_captured_payload",
    "SessionLinked": "session_linked_payload",
    # Glossary semantic integrity contracts
    "GlossaryScopeActivated": "glossary_scope_activated_payload",
    "TermCandidateObserved": "term_candidate_observed_payload",
    "SemanticCheckEvaluated": "semantic_check_evaluated_payload",
    "GlossaryClarificationRequested": "glossary_clarification_requested_payload",
    "GlossaryClarificationResolved": "glossary_clarification_resolved_payload",
    "GlossarySenseUpdated": "glossary_sense_updated_payload",
    "GenerationBlockedBySemanticConflict": "generation_blocked_by_semantic_conflict_payload",
    "GlossaryStrictnessSet": "glossary_strictness_set_payload",
    # Mission-next runtime contracts
    "MissionRunStarted": "mission_run_started_payload",
    "NextStepIssued": "next_step_issued_payload",
    "NextStepAutoCompleted": "next_step_auto_completed_payload",
    "DecisionInputRequested": "decision_input_requested_payload",
    "DecisionInputAnswered": "decision_input_answered_payload",
    "MissionRunCompleted": "mission_run_completed_payload",
    # Analytics contracts (3.3.0)
    "TokenUsageRecorded": "token_usage_recorded_payload",
    "DiffSummaryRecorded": "diff_summary_recorded_payload",
    # Dossier event contracts
    "MissionDossierArtifactIndexed": "mission_dossier_artifact_indexed_payload",
    "MissionDossierArtifactMissing": "mission_dossier_artifact_missing_payload",
    "MissionDossierSnapshotComputed": "mission_dossier_snapshot_computed_payload",
    "MissionDossierParityDriftDetected": "mission_dossier_parity_drift_detected_payload",
    # Mission audit lifecycle contracts (2.5.0)
    "MissionAuditRequested": "mission_audit_requested_payload",
    "MissionAuditStarted": "mission_audit_started_payload",
    "MissionAuditDecisionRequested": "mission_audit_decision_requested_payload",
    "MissionAuditCompleted": "mission_audit_completed_payload",
    "MissionAuditFailed": "mission_audit_failed_payload",
    # DecisionPoint lifecycle contracts (2.6.0 / V1 4.0.0)
    "DecisionPointOpened": "decision_point_opened_payload",
    "DecisionPointWidened": "decision_point_widened_payload",
    "DecisionPointDiscussing": "decision_point_discussing_payload",
    "DecisionPointResolved": "decision_point_resolved_payload",
    "DecisionPointOverridden": "decision_point_overridden_payload",
    # Connector lifecycle contracts (2.7.0)
    "ConnectorProvisioned": "connector_provisioned_payload",
    "ConnectorHealthChecked": "connector_health_checked_payload",
    "ConnectorDegraded": "connector_degraded_payload",
    "ConnectorRevoked": "connector_revoked_payload",
    "ConnectorReconnected": "connector_reconnected_payload",
    # Sync lifecycle contracts (2.7.0)
    "SyncIngestAccepted": "sync_ingest_accepted_payload",
    "SyncIngestRejected": "sync_ingest_rejected_payload",
    "SyncRetryScheduled": "sync_retry_scheduled_payload",
    "SyncDeadLettered": "sync_dead_lettered_payload",
    "SyncReplayCompleted": "sync_replay_completed_payload",
    "ExternalReferenceLinked": "external_reference_linked_payload",
    # Profile invocation contracts (3.1.0)
    "ProfileInvocationStarted": "profile_invocation_started_payload",
    # Retrospective contracts (3.1.0)
    "RetrospectiveCompleted": "retrospective_completed_payload",
    "RetrospectiveSkipped": "retrospective_skipped_payload",
}


def _validate_with_model(
    payload: Dict[str, Any],
    model_class: Type[Any],
) -> Tuple[ModelViolation, ...]:
    """Validate payload using Pydantic model.

    Args:
        payload: The event payload to validate.
        model_class: The Pydantic model class to validate against.

    Returns:
        Tuple of ModelViolation instances (empty if valid).
    """
    try:
        model_class.model_validate(payload)
        return ()
    except PydanticValidationError as e:
        violations = []
        for error in e.errors():
            # Build field path from loc tuple
            field_path = ".".join(str(loc) for loc in error["loc"])
            violations.append(
                ModelViolation(
                    field=field_path,
                    message=error["msg"],
                    violation_type=error["type"],
                    input_value=error.get("input"),
                )
            )
        return tuple(violations)


def _validate_with_schema(
    payload: Dict[str, Any],
    schema_name: str,
    *,
    strict: bool,
) -> Tuple[Tuple[SchemaViolation, ...], bool]:
    """Validate payload using JSON Schema.

    Args:
        payload: The event payload to validate.
        schema_name: Name of the schema (passed to load_schema()).
        strict: If True, raise ImportError when jsonschema is unavailable.
                If False, skip validation and return empty violations.

    Returns:
        Tuple of (violations, skipped) where violations is a tuple of
        SchemaViolation instances and skipped indicates if validation
        was skipped due to missing jsonschema.

    Raises:
        ImportError: If strict=True and jsonschema is unavailable.
    """
    try:
        import jsonschema  # type: ignore[import-untyped]
        from jsonschema import Draft202012Validator
    except ImportError:
        if strict:
            raise ImportError(
                "jsonschema is required for strict conformance validation. "
                "Install with: pip install 'spec-kitty-events[conformance]'"
            ) from None
        # Graceful degradation
        return ((), True)

    # Load schema from package
    from ..schemas import load_schema

    schema = load_schema(schema_name)

    # Validate with jsonschema
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.json_path)

    if not errors:
        return ((), False)

    violations = []
    for error in errors:
        violations.append(
            SchemaViolation(
                json_path=error.json_path,
                message=error.message,
                validator=error.validator,
                validator_value=error.validator_value,
                schema_path=tuple(error.absolute_schema_path),
            )
        )

    return (tuple(violations), False)


def validate_event(
    payload: Dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Validate an event payload against the canonical contract.

    This function performs dual-layer validation:
    1. Pydantic model validation (always performed)
    2. JSON Schema validation (optional, requires jsonschema package)

    Args:
        payload: The event payload dictionary to validate.
        event_type: The event type string (e.g., "WPStatusChanged").
        strict: If True, require jsonschema and fail if unavailable.
                If False, skip schema validation if jsonschema is missing.

    Returns:
        ConformanceResult with validation status and any violations found.

    Raises:
        ValueError: If event_type is not recognized.
        ImportError: If strict=True and jsonschema is unavailable.
    """
    if event_type not in _EVENT_TYPE_TO_MODEL:
        raise ValueError(
            f"Unknown event type: {event_type!r}. "
            f"Known types: {sorted(_EVENT_TYPE_TO_MODEL)}"
        )

    model_class = _EVENT_TYPE_TO_MODEL[event_type]
    schema_name = _EVENT_TYPE_TO_SCHEMA.get(event_type)

    envelope = None
    model_payload = payload
    if (
        event_type != "Event"
        and isinstance(payload.get("payload"), dict)
        and payload.get("event_type") == event_type
    ):
        envelope = payload
        model_payload = payload["payload"]

    cutover_violations: Tuple[ModelViolation, ...] = ()
    if envelope is not None or event_type == "Event":
        candidate_envelope = envelope or payload
        try:
            assert_canonical_cutover_signal(candidate_envelope)
        except (TypeError, ValueError) as exc:
            cutover_violations = (
                ModelViolation(
                    field="schema_version",
                    message=str(exc),
                    violation_type="cutover_policy",
                    input_value=candidate_envelope,
                ),
            )

    # Layer 1: Pydantic validation
    model_violations = cutover_violations + _validate_with_model(model_payload, model_class)

    # Layer 2: JSON Schema validation (skip if no schema mapping exists)
    if schema_name is not None:
        schema_violations, schema_skipped = _validate_with_schema(
            model_payload, schema_name, strict=strict
        )
    else:
        schema_violations = ()
        schema_skipped = True

    # Determine overall validity
    valid = len(model_violations) == 0 and (
        len(schema_violations) == 0 or schema_skipped
    )

    return ConformanceResult(
        valid=valid,
        model_violations=model_violations,
        schema_violations=schema_violations,
        schema_check_skipped=schema_skipped,
        event_type=event_type,
    )
