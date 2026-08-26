"""Typed, host-owned contracts for advisory specification review."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256  # noqa: TID251 - exact byte-level disclosure integrity is not charter content
import json
import re
from typing import Final

from kernel.clock import datetime


REVIEW_RESPONSE_SCHEMA: Final = "review-response/v1"
SPEC_REVIEW_RUN_SCHEMA: Final = "spec-review-run/v1"
MAX_FINDINGS: Final = 100
_IDENTIFIER_PATTERN: Final = re.compile(r"^[A-Za-z0-9_-]+$")


class ReviewStatus(StrEnum):
    """Closed invocation statuses owned by the host rather than the model."""

    COMPLETED = "completed"
    REFUSED = "refused"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    WRITE_FAILED = "write_failed"


class DiagnosticCode(StrEnum):
    """Stable, metadata-only diagnostic codes for review outcomes."""

    CLI_UNAVAILABLE = "SPEC_REVIEW_CLI_UNAVAILABLE"
    AUTH_REQUIRED = "SPEC_REVIEW_AUTH_REQUIRED"
    SESSION_CLEANUP_FAILED = "SPEC_REVIEW_SESSION_CLEANUP_FAILED"
    PROVIDER_ERROR = "SPEC_REVIEW_PROVIDER_ERROR"
    TIMEOUT = "SPEC_REVIEW_TIMEOUT"
    INVALID_OUTPUT = "SPEC_REVIEW_INVALID_OUTPUT"
    WRITE_FAILED = "SPEC_REVIEW_WRITE_FAILED"
    REFUSED = "SPEC_REVIEW_REFUSED"


@dataclass(frozen=True)
class DisclosureComponent:
    """A named immutable payload component represented by size and SHA-256."""

    name: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.name or self.size_bytes < 0 or not _is_sha256(self.sha256):
            raise ValueError("invalid disclosure component")

    @classmethod
    def from_bytes(cls, name: str, payload: bytes) -> DisclosureComponent:
        """Create metadata for exact immutable *payload* bytes."""
        return cls(name=name, size_bytes=len(payload), sha256=sha256(payload).hexdigest())


@dataclass(frozen=True)
class DisclosureManifest:
    """The deterministic, consent-bound description of all external input."""

    transport: str
    requested_model_route: str
    spec_path: str
    spec: DisclosureComponent
    rubric: DisclosureComponent
    response_schema: DisclosureComponent
    prompt_template: DisclosureComponent
    rubric_version: str
    total_payload_bytes: int
    manifest_sha256: str

    @classmethod
    def create(
        cls,
        *,
        transport: str,
        requested_model_route: str,
        spec_path: str,
        spec: DisclosureComponent,
        rubric: DisclosureComponent,
        response_schema: DisclosureComponent,
        prompt_template: DisclosureComponent,
        rubric_version: str,
    ) -> DisclosureManifest:
        """Build a canonical manifest whose digest covers every disclosed field."""
        if not transport or not requested_model_route or not spec_path or not rubric_version:
            raise ValueError("manifest metadata must be non-empty")
        total = spec.size_bytes + rubric.size_bytes + response_schema.size_bytes + prompt_template.size_bytes
        document = {
            "requested_model_route": requested_model_route,
            "response_schema": _component_document(response_schema),
            "prompt_template": _component_document(prompt_template),
            "rubric": _component_document(rubric),
            "rubric_version": rubric_version,
            "spec_path": spec_path,
            "spec": _component_document(spec),
            "total_payload_bytes": total,
            "transport": transport,
        }
        digest = sha256(_canonical_json(document)).hexdigest()
        return cls(
            transport=transport,
            requested_model_route=requested_model_route,
            spec_path=spec_path,
            spec=spec,
            rubric=rubric,
            response_schema=response_schema,
            prompt_template=prompt_template,
            rubric_version=rubric_version,
            total_payload_bytes=total,
            manifest_sha256=digest,
        )

    def __post_init__(self) -> None:
        expected_total = self.spec.size_bytes + self.rubric.size_bytes + self.response_schema.size_bytes + self.prompt_template.size_bytes
        if self.total_payload_bytes != expected_total or not _is_sha256(self.manifest_sha256):
            raise ValueError("invalid disclosure manifest")

    def has_valid_digest(self) -> bool:
        """Return whether the stored digest still covers every manifest field."""
        document = {
            "requested_model_route": self.requested_model_route,
            "response_schema": _component_document(self.response_schema),
            "prompt_template": _component_document(self.prompt_template),
            "rubric": _component_document(self.rubric),
            "rubric_version": self.rubric_version,
            "spec_path": self.spec_path,
            "spec": _component_document(self.spec),
            "total_payload_bytes": self.total_payload_bytes,
            "transport": self.transport,
        }
        return self.manifest_sha256 == sha256(_canonical_json(document)).hexdigest()


@dataclass(frozen=True)
class LineEvidence:
    """A line-only reference into a verified specification snapshot."""

    line_start: int
    line_end: int

    def __post_init__(self) -> None:
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError("invalid evidence range")

    def validate_for_line_count(self, line_count: int) -> None:
        """Reject a range outside a snapshot containing *line_count* lines."""
        if line_count < 1 or self.line_end > line_count:
            raise ValueError("evidence range outside specification snapshot")


@dataclass(frozen=True)
class SpecReviewFinding:
    """One validated model observation with line-only evidence."""

    identifier: str
    lens: str
    severity: int
    title: str
    evidence: LineEvidence
    claim: str
    remediation: str

    def __post_init__(self) -> None:
        if not _IDENTIFIER_PATTERN.fullmatch(self.identifier):
            raise ValueError("invalid finding identifier")
        if not _has_length(self.lens, 1, 100) or self.severity not in range(1, 6):
            raise ValueError("invalid finding metadata")
        if not _has_length(self.title, 1, 300):
            raise ValueError("invalid finding title")
        if not _has_length(self.claim, 1, 4000) or not _has_length(self.remediation, 1, 4000):
            raise ValueError("invalid finding text")


@dataclass(frozen=True)
class ReviewResponse:
    """The untrusted, deliberately provenance-free model response contract."""

    schema: str
    findings: tuple[SpecReviewFinding, ...]

    @classmethod
    def create(cls, findings: Iterable[SpecReviewFinding]) -> ReviewResponse:
        """Create the only supported response schema from model findings."""
        return cls(schema=REVIEW_RESPONSE_SCHEMA, findings=tuple(findings))

    def __post_init__(self) -> None:
        if self.schema != REVIEW_RESPONSE_SCHEMA or len(self.findings) > MAX_FINDINGS:
            raise ValueError("invalid review response")
        identifiers = [finding.identifier for finding in self.findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate finding identifier")


@dataclass(frozen=True)
class ReviewSummary:
    """Host-computed severity totals for a persisted review run."""

    total: int
    severity_1: int
    severity_2: int
    severity_3: int
    severity_4: int
    severity_5: int

    @classmethod
    def from_findings(cls, findings: Iterable[SpecReviewFinding]) -> ReviewSummary:
        """Compute deterministic counts without trusting model supplied totals."""
        counts = [0, 0, 0, 0, 0]
        for finding in findings:
            counts[finding.severity - 1] += 1
        return cls(sum(counts), *counts)

    def __post_init__(self) -> None:
        counts = (self.severity_1, self.severity_2, self.severity_3, self.severity_4, self.severity_5)
        if any(count < 0 or count > MAX_FINDINGS for count in counts):
            raise ValueError("invalid review summary")
        if self.total != sum(counts) or self.total > MAX_FINDINGS:
            raise ValueError("inconsistent review summary")


@dataclass(frozen=True)
class SpecReviewRun:
    """A fully host-owned persisted outcome built after response validation."""

    run_id: str
    mission: str
    spec_sha256: str
    transport: str
    requested_model_route: str
    actual_model: str
    rubric_version: str
    started_at: datetime
    completed_at: datetime
    status: ReviewStatus
    diagnostic_code: DiagnosticCode | None
    findings: tuple[SpecReviewFinding, ...]
    summary: ReviewSummary | None = None
    schema: str = SPEC_REVIEW_RUN_SCHEMA

    @classmethod
    def from_response(
        cls,
        *,
        run_id: str,
        mission: str,
        manifest: DisclosureManifest,
        started_at: datetime,
        completed_at: datetime,
        response: ReviewResponse,
        actual_model: str = "unverified",
    ) -> SpecReviewRun:
        """Build a complete host result and its local severity summary."""
        return cls(
            run_id=run_id,
            mission=mission,
            spec_sha256=manifest.spec.sha256,
            transport=manifest.transport,
            requested_model_route=manifest.requested_model_route,
            actual_model=actual_model,
            rubric_version=manifest.rubric_version,
            started_at=started_at,
            completed_at=completed_at,
            status=ReviewStatus.COMPLETED,
            diagnostic_code=None,
            findings=response.findings,
        )

    @classmethod
    def from_failure(
        cls,
        *,
        run_id: str,
        mission: str,
        manifest: DisclosureManifest,
        started_at: datetime,
        completed_at: datetime,
        status: ReviewStatus,
        diagnostic_code: DiagnosticCode,
    ) -> SpecReviewRun:
        """Build a host-owned persistable failure without retaining provider output."""
        return cls(
            run_id=run_id,
            mission=mission,
            spec_sha256=manifest.spec.sha256,
            transport=manifest.transport,
            requested_model_route=manifest.requested_model_route,
            actual_model="unverified",
            rubric_version=manifest.rubric_version,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            diagnostic_code=diagnostic_code,
            findings=(),
        )

    def __post_init__(self) -> None:
        if not _IDENTIFIER_PATTERN.fullmatch(self.run_id) or not self.mission:
            raise ValueError("invalid host provenance")
        if (
            not _is_sha256(self.spec_sha256)
            or self.transport != "opencode-loopback"
            or not _has_length(self.requested_model_route, 1, 200)
            or not _has_length(self.actual_model, 1, 200)
            or not self.rubric_version
            or self.schema != SPEC_REVIEW_RUN_SCHEMA
            or not isinstance(self.status, ReviewStatus)
        ):
            raise ValueError("invalid host provenance")
        expected_summary = ReviewSummary.from_findings(self.findings)
        actual_summary = self.summary or expected_summary
        if actual_summary != expected_summary:
            raise ValueError("inconsistent review summary")
        object.__setattr__(self, "summary", actual_summary)
        if self.status not in {
            ReviewStatus.COMPLETED,
            ReviewStatus.PROVIDER_ERROR,
            ReviewStatus.TIMEOUT,
            ReviewStatus.INVALID_OUTPUT,
        }:
            raise ValueError("run status is not persistable")
        if self.status is ReviewStatus.COMPLETED:
            if self.diagnostic_code is not None:
                raise ValueError("completed run cannot have diagnostic")
        elif self.findings or not isinstance(self.diagnostic_code, DiagnosticCode):
            raise ValueError("failure run requires diagnostic and no findings")


def _component_document(component: DisclosureComponent) -> dict[str, str | int]:
    return {"name": component.name, "sha256": component.sha256, "size_bytes": component.size_bytes}


def _canonical_json(document: object) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _has_length(value: str, minimum: int, maximum: int) -> bool:
    return isinstance(value, str) and minimum <= len(value) <= maximum


def _is_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{64}", value))
