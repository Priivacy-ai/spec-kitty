"""Proof event schema surface for CLI-owned evidence events."""

from .events import (
    MAX_PROOF_PAYLOAD_BYTES,
    PROOF_EVENT_TYPES,
    PROOF_SCHEMA_VERSION,
    BenchmarkEvidenceAttachedPayload,
    HumanApprovalRecordedPayload,
    ProofActor,
    ProofArtifactRef,
    ProofItemRecordedPayload,
    ProofSubject,
    PullRequestLineageRecordedPayload,
    ReviewProofRecordedPayload,
    SecurityScanCompletedPayload,
    TestEvidenceCapturedPayload,
    build_proof_payload,
    infer_proof_aggregate,
    proof_idempotency_key,
)

__all__ = [
    "MAX_PROOF_PAYLOAD_BYTES",
    "PROOF_EVENT_TYPES",
    "PROOF_SCHEMA_VERSION",
    "BenchmarkEvidenceAttachedPayload",
    "HumanApprovalRecordedPayload",
    "ProofActor",
    "ProofArtifactRef",
    "ProofItemRecordedPayload",
    "ProofSubject",
    "PullRequestLineageRecordedPayload",
    "ReviewProofRecordedPayload",
    "SecurityScanCompletedPayload",
    "TestEvidenceCapturedPayload",
    "build_proof_payload",
    "infer_proof_aggregate",
    "proof_idempotency_key",
]
