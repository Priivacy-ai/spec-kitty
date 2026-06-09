"""Typed schemas for CLI proof/evidence sync events.

These event types are CLI-owned until the external ``spec-kitty-events``
package grows canonical models for them.  Keep payloads summary-only: logs,
reports, coverage, and scan bodies travel as artifact references.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROOF_SCHEMA_VERSION = "1.0.0"
MAX_PROOF_SUMMARY_BYTES = 4096
MAX_PROOF_PAYLOAD_BYTES = 16_384
MAX_PROOF_ARTIFACT_REFS = 20

ProofEventType = Literal[
    "ProofItemRecorded",
    "ReviewProofRecorded",
    "TestEvidenceCaptured",
    "BenchmarkEvidenceAttached",
    "SecurityScanCompleted",
    "PullRequestLineageRecorded",
    "HumanApprovalRecorded",
]

PROOF_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "ProofItemRecorded",
        "ReviewProofRecorded",
        "TestEvidenceCaptured",
        "BenchmarkEvidenceAttached",
        "SecurityScanCompleted",
        "PullRequestLineageRecorded",
        "HumanApprovalRecorded",
    }
)

_SHA256_HEX_LENGTH = 64


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProofActor(_StrictModel):
    actor_id: str = Field(min_length=1)
    actor_type: Literal["human", "llm", "service"]
    display_name: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    tool: str | None = Field(default=None, min_length=1)


class ProofSubject(_StrictModel):
    subject_type: Literal["mission", "work_package", "mission_run", "review", "pull_request"]
    subject_id: str = Field(min_length=1)
    team_slug: str | None = Field(default=None, min_length=1)
    project_uuid: str | None = Field(default=None, min_length=1)
    project_slug: str | None = Field(default=None, min_length=1)
    repo_slug: str | None = Field(default=None, min_length=1)
    build_id: str | None = Field(default=None, min_length=1)
    git_branch: str | None = Field(default=None, min_length=1)
    head_commit_sha: str | None = Field(default=None, min_length=1)
    mission_id: str | None = Field(default=None, min_length=1)
    mission_slug: str | None = Field(default=None, min_length=1)
    wp_id: str | None = Field(default=None, min_length=1)
    step_id: str | None = Field(default=None, min_length=1)
    run_id: str | None = Field(default=None, min_length=1)
    pull_request_url: str | None = Field(default=None, min_length=1)
    pull_request_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_subject_binding(self) -> ProofSubject:
        if self.subject_type == "work_package" and not self.wp_id:
            raise ValueError("work_package proof subjects require wp_id")
        if self.subject_type == "mission" and not (self.mission_id or self.mission_slug):
            raise ValueError("mission proof subjects require mission_id or mission_slug")
        if self.subject_type == "mission_run" and not self.run_id:
            raise ValueError("mission_run proof subjects require run_id")
        return self


class ProofArtifactRef(_StrictModel):
    kind: Literal[
        "file",
        "log",
        "junit",
        "coverage",
        "report",
        "url",
        "commit",
        "pull_request",
        "benchmark",
        "security_scan",
        "other",
    ]
    uri: str = Field(min_length=1)
    sha256: str | None = Field(default=None, min_length=_SHA256_HEX_LENGTH, max_length=_SHA256_HEX_LENGTH)
    size_bytes: int | None = Field(default=None, ge=0)
    media_type: str | None = Field(default=None, min_length=1)
    label: str | None = Field(default=None, min_length=1)

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if any(char not in "0123456789abcdef" for char in lowered):
            raise ValueError("sha256 must be lowercase hex")
        return lowered


class BaseProofPayload(_StrictModel):
    proof_schema_version: Literal["1.0.0"] = PROOF_SCHEMA_VERSION
    subject: ProofSubject
    source: str = Field(min_length=1)
    actor: ProofActor
    confidence: float = Field(ge=0.0, le=1.0)
    occurred_at: datetime
    observed_at: datetime
    artifact_refs: list[ProofArtifactRef] = Field(max_length=MAX_PROOF_ARTIFACT_REFS)
    summary: dict[str, Any]
    idempotency_key: str | None = Field(default=None, min_length=_SHA256_HEX_LENGTH, max_length=_SHA256_HEX_LENGTH)

    event_type: ClassVar[str]

    @field_validator("idempotency_key")
    @classmethod
    def _validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if any(char not in "0123456789abcdef" for char in lowered):
            raise ValueError("idempotency_key must be lowercase hex")
        return lowered

    @model_validator(mode="after")
    def _validate_bounded_summary(self) -> BaseProofPayload:
        summary_size = _json_size(self.summary)
        if summary_size > MAX_PROOF_SUMMARY_BYTES:
            raise ValueError(
                "summary must be artifact-backed when larger than "
                f"{MAX_PROOF_SUMMARY_BYTES} bytes"
            )
        return self


class ProofItemRecordedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "ProofItemRecorded"
    proof_kind: Literal["artifact", "claim", "observation", "note", "other"]


class ReviewProofRecordedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "ReviewProofRecorded"
    review_kind: Literal["code_review", "qa", "mission_review", "security_review", "other"]
    verdict: Literal["approved", "changes_requested", "commented", "rejected", "unknown"]
    review_ref: str | None = Field(default=None, min_length=1)


class TestEvidenceCapturedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "TestEvidenceCaptured"
    test_command: str = Field(min_length=1)
    exit_code: int = Field(ge=0)
    status: Literal["passed", "failed", "error", "skipped"]
    runner: str | None = Field(default=None, min_length=1)
    cwd: str | None = Field(default=None, min_length=1)
    duration_ms: int | None = Field(default=None, ge=0)
    total_tests: int | None = Field(default=None, ge=0)
    passed_tests: int | None = Field(default=None, ge=0)
    failed_tests: int | None = Field(default=None, ge=0)
    skipped_tests: int | None = Field(default=None, ge=0)
    failure_summary: str | None = Field(default=None, max_length=2000)
    branch: str | None = Field(default=None, min_length=1)
    commit: str | None = Field(default=None, min_length=1)
    build_id: str | None = Field(default=None, min_length=1)


class BenchmarkEvidenceAttachedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "BenchmarkEvidenceAttached"
    benchmark_name: str = Field(min_length=1)
    benchmark_suite: str | None = Field(default=None, min_length=1)
    baseline_ref: str | None = Field(default=None, min_length=1)
    comparison_ref: str | None = Field(default=None, min_length=1)


class SecurityScanCompletedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "SecurityScanCompleted"
    scanner: str = Field(min_length=1)
    status: Literal["passed", "failed", "completed", "error"]
    findings_summary: dict[str, Any]


class PullRequestLineageRecordedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "PullRequestLineageRecorded"
    provider: Literal["github", "gitlab", "bitbucket", "other"]
    repository: str = Field(min_length=1)
    pull_request_url: str = Field(min_length=1)
    pull_request_number: int | None = Field(default=None, ge=1)
    base_ref: str | None = Field(default=None, min_length=1)
    head_ref: str | None = Field(default=None, min_length=1)


class HumanApprovalRecordedPayload(BaseProofPayload):
    event_type: ClassVar[str] = "HumanApprovalRecorded"
    approver: str = Field(min_length=1)
    approval_status: Literal["approved", "rejected", "requested_changes", "acknowledged"]
    approval_ref: str | None = Field(default=None, min_length=1)


PROOF_PAYLOAD_MODELS: dict[str, type[BaseProofPayload]] = {
    model.event_type: model
    for model in (
        ProofItemRecordedPayload,
        ReviewProofRecordedPayload,
        TestEvidenceCapturedPayload,
        BenchmarkEvidenceAttachedPayload,
        SecurityScanCompletedPayload,
        PullRequestLineageRecordedPayload,
        HumanApprovalRecordedPayload,
    )
}

PROOF_COMMON_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "proof_schema_version",
        "subject",
        "source",
        "actor",
        "confidence",
        "occurred_at",
        "observed_at",
        "artifact_refs",
        "summary",
        "idempotency_key",
    }
)

PROOF_EVENT_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "ProofItemRecorded": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"proof_kind"}),
    "ReviewProofRecorded": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"review_kind", "verdict"}),
    "TestEvidenceCaptured": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"test_command", "exit_code", "status"}),
    "BenchmarkEvidenceAttached": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"benchmark_name"}),
    "SecurityScanCompleted": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"scanner", "status", "findings_summary"}),
    "PullRequestLineageRecorded": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"provider", "repository", "pull_request_url"}),
    "HumanApprovalRecorded": PROOF_COMMON_REQUIRED_FIELDS | frozenset({"approver", "approval_status"}),
}


def build_proof_payload(event_type: str, payload: BaseProofPayload | dict[str, Any]) -> dict[str, Any]:
    """Validate and serialize a proof payload for the sync envelope."""
    model_cls = PROOF_PAYLOAD_MODELS.get(event_type)
    if model_cls is None:
        raise ValueError(f"Unknown proof event type: {event_type}")

    model = payload if isinstance(payload, BaseProofPayload) else model_cls(**payload)
    if model.event_type != event_type:
        raise ValueError(
            f"Payload model {model.__class__.__name__} cannot be emitted as {event_type}"
        )

    data = model.model_dump(mode="json", exclude_none=True)
    if "idempotency_key" not in data:
        data["idempotency_key"] = proof_idempotency_key(event_type, data)

    if _json_size(data) > MAX_PROOF_PAYLOAD_BYTES:
        raise ValueError(
            "proof payload exceeds bounded sync envelope; attach large data as artifact_refs"
        )
    return data


def proof_idempotency_key(event_type: str, payload: dict[str, Any]) -> str:
    """Return the deterministic idempotency key for a proof payload."""
    canonical = {
        key: value
        for key, value in payload.items()
        if key not in {"idempotency_key", "observed_at"}
    }
    encoded = json.dumps(
        {"event_type": event_type, "payload": canonical},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    # Stable cross-process event idempotency digest; unrelated to charter hashing.
    return hashlib.sha256(encoded).hexdigest()  # noqa: TID251


def infer_proof_aggregate(payload: dict[str, Any]) -> tuple[str, str]:
    """Infer ``(aggregate_type, aggregate_id)`` from a serialized proof payload."""
    subject = payload.get("subject")
    if not isinstance(subject, dict):
        return ("Mission", "proof")

    subject_type = subject.get("subject_type")
    if subject_type == "work_package":
        return ("WorkPackage", str(subject.get("wp_id") or subject.get("subject_id")))

    return (
        "Mission",
        str(
            subject.get("mission_id")
            or subject.get("mission_slug")
            or subject.get("run_id")
            or subject.get("subject_id")
            or "proof"
        ),
    )


def _json_size(value: Any) -> int:
    return len(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    )
