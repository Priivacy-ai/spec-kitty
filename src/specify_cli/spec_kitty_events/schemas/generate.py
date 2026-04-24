"""Build-time JSON Schema generation script for spec-kitty-events models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

from pydantic import TypeAdapter
from pydantic import BaseModel

# Import all models to generate schemas for
from ..models import Event
from ..status import (
    Lane,
    SyncLaneV1,
    SyncLaneV2,
    StatusTransitionPayload,
)
from ..lifecycle import (
    MissionCreatedPayload,
    MissionClosedPayload,
    MissionStartedPayload,
    MissionCompletedPayload,
    MissionCancelledPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
)
from ..cutover import CutoverArtifact
from ..gates import (
    GatePassedPayload,
    GateFailedPayload,
)
from ..collaboration import (
    ParticipantIdentity,
    ParticipantExternalRefs,
    AuthPrincipalBinding,
    FocusTarget,
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
    SemanticConflictEntry,
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    GlossarySenseUpdatedPayload,
    GlossaryStrictnessSetPayload,
    SemanticCheckEvaluatedPayload,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GenerationBlockedBySemanticConflictPayload,
)
from ..mission_next import (
    RuntimeActorIdentity,
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
    ArtifactIdentity,
    ContentHashRef,
    ProvenanceRef,
    LocalNamespaceTuple,
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
from ..decision_moment import (
    SummaryBlock,
    TeamspaceRef,
    DefaultChannelRef,
    ThreadRef,
    ClosureMessageRef,
)
from ..decisionpoint import (
    DecisionPointWidenedPayload,
    DecisionPointOverriddenPayload,
    _OPENED_ADAPTER,
    _DISCUSSING_ADAPTER,
    _RESOLVED_ADAPTER,
)
from ..connector import (
    ConnectorProvisionedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorDegradedPayload,
    ConnectorRevokedPayload,
    ConnectorReconnectedPayload,
    UserConnectedPayload,
    UserDisconnectedPayload,
    UserConnectionStatus,
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


# Schema directory (same directory as this script)
SCHEMA_DIR = Path(__file__).parent

# Registry of models to generate schemas for
PYDANTIC_MODELS: List[tuple[str, Type[BaseModel]]] = [
    ("event", Event),
    ("status_transition_payload", StatusTransitionPayload),
    ("gate_passed_payload", GatePassedPayload),
    ("gate_failed_payload", GateFailedPayload),
    ("mission_started_payload", MissionStartedPayload),
    ("mission_created_payload", MissionCreatedPayload),
    ("mission_closed_payload", MissionClosedPayload),
    ("mission_completed_payload", MissionCompletedPayload),
    ("mission_cancelled_payload", MissionCancelledPayload),
    ("phase_entered_payload", PhaseEnteredPayload),
    ("review_rollback_payload", ReviewRollbackPayload),
    # Collaboration identity models (V1: ParticipantIdentity gains external_refs)
    ("participant_identity", ParticipantIdentity),
    ("participant_external_refs", ParticipantExternalRefs),
    ("auth_principal_binding", AuthPrincipalBinding),
    ("focus_target", FocusTarget),
    # Collaboration payload models
    ("participant_invited_payload", ParticipantInvitedPayload),
    ("participant_joined_payload", ParticipantJoinedPayload),
    ("participant_left_payload", ParticipantLeftPayload),
    ("presence_heartbeat_payload", PresenceHeartbeatPayload),
    ("drive_intent_set_payload", DriveIntentSetPayload),
    ("focus_changed_payload", FocusChangedPayload),
    ("prompt_step_execution_started_payload", PromptStepExecutionStartedPayload),
    ("prompt_step_execution_completed_payload", PromptStepExecutionCompletedPayload),
    ("concurrent_driver_warning_payload", ConcurrentDriverWarningPayload),
    ("potential_step_collision_detected_payload", PotentialStepCollisionDetectedPayload),
    ("warning_acknowledged_payload", WarningAcknowledgedPayload),
    ("comment_posted_payload", CommentPostedPayload),
    ("decision_captured_payload", DecisionCapturedPayload),
    ("session_linked_payload", SessionLinkedPayload),
    # Glossary semantic integrity models
    ("semantic_conflict_entry", SemanticConflictEntry),
    ("glossary_scope_activated_payload", GlossaryScopeActivatedPayload),
    ("term_candidate_observed_payload", TermCandidateObservedPayload),
    ("glossary_sense_updated_payload", GlossarySenseUpdatedPayload),
    ("glossary_strictness_set_payload", GlossaryStrictnessSetPayload),
    ("semantic_check_evaluated_payload", SemanticCheckEvaluatedPayload),
    ("glossary_clarification_requested_payload", GlossaryClarificationRequestedPayload),
    ("glossary_clarification_resolved_payload", GlossaryClarificationResolvedPayload),
    ("generation_blocked_by_semantic_conflict_payload", GenerationBlockedBySemanticConflictPayload),
    # Mission-next runtime models
    ("runtime_actor_identity", RuntimeActorIdentity),
    ("mission_run_started_payload", MissionRunStartedPayload),
    ("next_step_issued_payload", NextStepIssuedPayload),
    ("next_step_auto_completed_payload", NextStepAutoCompletedPayload),
    ("decision_input_requested_payload", DecisionInputRequestedPayload),
    ("decision_input_answered_payload", DecisionInputAnsweredPayload),
    ("mission_run_completed_payload", MissionRunCompletedPayload),
    # Analytics models (3.3.0)
    ("token_usage_recorded_payload", TokenUsageRecordedPayload),
    ("diff_summary_recorded_payload", DiffSummaryRecordedPayload),
    # Dossier event contract models
    ("artifact_identity", ArtifactIdentity),
    ("content_hash_ref", ContentHashRef),
    ("provenance_ref", ProvenanceRef),
    ("local_namespace_tuple", LocalNamespaceTuple),
    ("mission_dossier_artifact_indexed_payload", MissionDossierArtifactIndexedPayload),
    ("mission_dossier_artifact_missing_payload", MissionDossierArtifactMissingPayload),
    ("mission_dossier_snapshot_computed_payload", MissionDossierSnapshotComputedPayload),
    ("mission_dossier_parity_drift_detected_payload", MissionDossierParityDriftDetectedPayload),
    # Mission audit lifecycle contracts (2.5.0)
    ("mission_audit_requested_payload", MissionAuditRequestedPayload),
    ("mission_audit_started_payload", MissionAuditStartedPayload),
    ("mission_audit_decision_requested_payload", MissionAuditDecisionRequestedPayload),
    ("mission_audit_completed_payload", MissionAuditCompletedPayload),
    ("mission_audit_failed_payload", MissionAuditFailedPayload),
    ("cutover_artifact", CutoverArtifact),
    # DecisionPoint shared models (V1 / 4.0.0)
    ("summary_block", SummaryBlock),
    ("teamspace_ref", TeamspaceRef),
    ("default_channel_ref", DefaultChannelRef),
    ("thread_ref", ThreadRef),
    ("closure_message_ref", ClosureMessageRef),
    # DecisionPoint lifecycle contracts (V1 / 4.0.0)
    # NOTE: Opened, Discussing, Resolved are discriminated unions — generated via
    # UNION_ADAPTERS below using TypeAdapter.json_schema(); they are NOT listed here.
    ("decision_point_widened_payload", DecisionPointWidenedPayload),
    ("decision_point_overridden_payload", DecisionPointOverriddenPayload),
    # Connector lifecycle contracts (2.7.0) — extended in 2.8.0
    ("connector_provisioned_payload", ConnectorProvisionedPayload),
    ("connector_health_checked_payload", ConnectorHealthCheckedPayload),
    ("connector_degraded_payload", ConnectorDegradedPayload),
    ("connector_revoked_payload", ConnectorRevokedPayload),
    ("connector_reconnected_payload", ConnectorReconnectedPayload),
    ("user_connected_payload", UserConnectedPayload),
    ("user_disconnected_payload", UserDisconnectedPayload),
    ("user_connection_status", UserConnectionStatus),
    # Sync lifecycle contracts (2.7.0)
    ("sync_ingest_accepted_payload", SyncIngestAcceptedPayload),
    ("sync_ingest_rejected_payload", SyncIngestRejectedPayload),
    ("sync_retry_scheduled_payload", SyncRetryScheduledPayload),
    ("sync_dead_lettered_payload", SyncDeadLetteredPayload),
    ("sync_replay_completed_payload", SyncReplayCompletedPayload),
    ("external_reference_linked_payload", ExternalReferenceLinkedPayload),
    # Profile invocation contracts (3.1.0)
    ("profile_invocation_started_payload", ProfileInvocationStartedPayload),
    # Retrospective contracts (3.1.0)
    ("retrospective_completed_payload", RetrospectiveCompletedPayload),
    ("retrospective_skipped_payload", RetrospectiveSkippedPayload),
]

# Enums (use TypeAdapter)
ENUM_TYPES: List[tuple[str, type]] = [
    ("lane", Lane),
    ("sync_lane_v1", SyncLaneV1),
    ("sync_lane_v2", SyncLaneV2),
]

# Discriminated-union payloads (V1): use TypeAdapter.json_schema() to emit oneOf
# Each entry: (schema_name, TypeAdapter_instance)
UNION_ADAPTERS: List[tuple[str, TypeAdapter[Any]]] = [
    ("decision_point_opened_payload", _OPENED_ADAPTER),
    ("decision_point_discussing_payload", _DISCUSSING_ADAPTER),
    ("decision_point_resolved_payload", _RESOLVED_ADAPTER),
]


def generate_schema(name: str, model: Type[BaseModel]) -> Dict[str, Any]:
    """Generate JSON Schema for a Pydantic model.

    Args:
        name: Schema name for $id field
        model: Pydantic model class

    Returns:
        JSON Schema dict with $schema and $id fields
    """
    schema = model.model_json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"spec-kitty-events/{name}"
    return schema


def generate_union_schema(name: str, adapter: TypeAdapter[Any]) -> Dict[str, Any]:
    """Generate JSON Schema for a discriminated-union type via TypeAdapter.

    Args:
        name: Schema name for $id field
        adapter: Pre-built TypeAdapter for the union type

    Returns:
        JSON Schema dict with $schema and $id fields, emitting oneOf for the union
    """
    schema = adapter.json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"spec-kitty-events/{name}"
    return schema


def generate_enum_schema(name: str, enum_cls: type) -> Dict[str, Any]:
    """Generate JSON Schema for an enum using TypeAdapter.

    Args:
        name: Schema name for $id field
        enum_cls: Enum class

    Returns:
        JSON Schema dict with $schema and $id fields
    """
    adapter: TypeAdapter[Any] = TypeAdapter(enum_cls)
    schema = adapter.json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"spec-kitty-events/{name}"
    return schema


def schema_to_json(schema: Dict[str, Any]) -> str:
    """Serialize schema to deterministic JSON string.

    Args:
        schema: JSON Schema dict

    Returns:
        Formatted JSON string with trailing newline
    """
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_schema_file(name: str, schema: Dict[str, Any]) -> None:
    """Write schema to disk.

    Args:
        name: Schema name (filename will be {name}.schema.json)
        schema: JSON Schema dict
    """
    path = SCHEMA_DIR / f"{name}.schema.json"
    content = schema_to_json(schema)
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path}")


def generate_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Generate all schemas and return them as a dict.

    Returns:
        Dict mapping schema name to schema dict
    """
    schemas: Dict[str, Dict[str, Any]] = {}

    # Generate Pydantic model schemas
    for name, model in PYDANTIC_MODELS:
        schemas[name] = generate_schema(name, model)

    # Generate enum schemas
    for name, enum_cls in ENUM_TYPES:
        schemas[name] = generate_enum_schema(name, enum_cls)

    # Generate discriminated-union schemas (V1: Opened, Discussing, Resolved)
    for name, adapter in UNION_ADAPTERS:
        schemas[name] = generate_union_schema(name, adapter)

    return schemas


def write_all_schemas(schemas: Dict[str, Dict[str, Any]]) -> None:
    """Write all schemas to disk.

    Args:
        schemas: Dict mapping schema name to schema dict
    """
    for name, schema in schemas.items():
        write_schema_file(name, schema)


def check_drift() -> int:
    """Check if generated schemas match committed files.

    Returns:
        0 if all schemas match, 1 if any drift detected
    """
    schemas = generate_all_schemas()
    drift_detected = False

    for name, schema in schemas.items():
        path = SCHEMA_DIR / f"{name}.schema.json"
        expected_content = schema_to_json(schema)

        if not path.exists():
            print(f"ERROR: Missing schema file: {path}", file=sys.stderr)
            drift_detected = True
            continue

        actual_content = path.read_text(encoding="utf-8")

        if actual_content != expected_content:
            print(f"ERROR: Schema drift detected in {path}", file=sys.stderr)
            print("--- Expected", file=sys.stderr)
            print(expected_content, file=sys.stderr)
            print("--- Actual", file=sys.stderr)
            print(actual_content, file=sys.stderr)
            drift_detected = True

    # Check for orphaned schema files not in the registry
    expected_files = {f"{name}.schema.json" for name in schemas}
    actual_files = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    orphaned = actual_files - expected_files
    for orphan in sorted(orphaned):
        print(f"Orphaned schema {orphan}", file=sys.stderr)
        drift_detected = True

    if drift_detected:
        print("\nSchema drift detected. Run without --check to regenerate.", file=sys.stderr)
        return 1

    print(f"All {len(schemas)} schemas are up to date.")
    return 0


def main() -> int:
    """Main entry point for schema generation script.

    Returns:
        Exit code (0 for success, 1 for failure/drift)
    """
    parser = argparse.ArgumentParser(
        description="Generate JSON schemas for spec-kitty-events models"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for schema drift without writing files (CI mode)",
    )
    args = parser.parse_args()

    if args.check:
        return check_drift()

    schemas = generate_all_schemas()
    write_all_schemas(schemas)
    print(f"\nSuccessfully generated {len(schemas)} schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
