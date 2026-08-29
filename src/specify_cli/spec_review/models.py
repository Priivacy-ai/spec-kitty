"""Typed, host-owned contracts for advisory specification review."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from enum import StrEnum
from hashlib import sha256  # noqa: TID251 - exact byte-level disclosure integrity is not charter content
import json
import re
from typing import Final

from kernel.clock import datetime


REVIEW_RESPONSE_SCHEMA: Final = "review-response/v1"
SPEC_REVIEW_RUN_SCHEMA: Final = "spec-review-run/v1"
PAID_SPEC_REVIEW_RUN_SCHEMA: Final = "spec-review-run/v2"
MAX_FINDINGS: Final = 100
_IDENTIFIER_PATTERN: Final = re.compile(r"^[A-Za-z0-9_-]+$")
_PAID_PRICE_KEYS: Final = frozenset({"input", "output", "cache.read", "cache.write"})
_MONEY_QUANTUM: Final = Decimal("0.000001")
_TOKENS_PER_MILLION: Final = Decimal(1_000_000)
_MAX_LOCAL_ESTIMATE_USD: Final = Decimal(5)


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
class PaidPricingDisclosure:
    """Consent-bound advertised pricing metadata for the one paid route."""

    route: str
    max_estimated_cost_usd: str
    price_leaves: tuple[tuple[str, str], ...]
    context_limit: int
    output_limit: int
    advertised_max_estimate_usd: str
    metadata_sha256: str

    @classmethod
    def create(
        cls,
        *,
        route: str,
        max_estimated_cost_usd: str,
        price_leaves: Iterable[tuple[str, str]],
        context_limit: int,
        output_limit: int,
    ) -> PaidPricingDisclosure:
        """Validate, canonicalize, and conservatively price advertised ceilings."""
        threshold, canonical_leaves, estimate, metadata_digest = _paid_pricing_values(
            route=route,
            max_estimated_cost_usd=max_estimated_cost_usd,
            price_leaves=tuple(price_leaves),
            context_limit=context_limit,
            output_limit=output_limit,
        )
        return cls(
            route=route,
            max_estimated_cost_usd=threshold,
            price_leaves=canonical_leaves,
            context_limit=context_limit,
            output_limit=output_limit,
            advertised_max_estimate_usd=estimate,
            metadata_sha256=metadata_digest,
        )

    def __post_init__(self) -> None:
        threshold, leaves, estimate, metadata_digest = _paid_pricing_values(
            route=self.route,
            max_estimated_cost_usd=self.max_estimated_cost_usd,
            price_leaves=self.price_leaves,
            context_limit=self.context_limit,
            output_limit=self.output_limit,
        )
        if (
            threshold != self.max_estimated_cost_usd
            or leaves != self.price_leaves
            or estimate != self.advertised_max_estimate_usd
            or metadata_digest != self.metadata_sha256
        ):
            raise ValueError("non-canonical paid pricing disclosure")

    def consent_document(self) -> dict[str, object]:
        """Return the complete paid section covered by the consent digest."""
        return {
            "advertised_max_estimate_usd": self.advertised_max_estimate_usd,
            "limit": {"context": self.context_limit, "output": self.output_limit},
            "max_estimated_cost_usd": self.max_estimated_cost_usd,
            "metadata_sha256": self.metadata_sha256,
            "prices": dict(self.price_leaves),
            "route": self.route,
        }


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
    paid_pricing: PaidPricingDisclosure | None = None

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
        paid_pricing: PaidPricingDisclosure | None = None,
    ) -> DisclosureManifest:
        """Build a canonical manifest whose digest covers every disclosed field."""
        if not transport or not requested_model_route or not spec_path or not rubric_version:
            raise ValueError("manifest metadata must be non-empty")
        total = spec.size_bytes + rubric.size_bytes + response_schema.size_bytes + prompt_template.size_bytes
        if paid_pricing is not None and paid_pricing.route != requested_model_route:
            raise ValueError("paid pricing route does not match manifest route")
        document = _manifest_document(
            transport=transport,
            requested_model_route=requested_model_route,
            spec_path=spec_path,
            spec=spec,
            rubric=rubric,
            response_schema=response_schema,
            prompt_template=prompt_template,
            rubric_version=rubric_version,
            total_payload_bytes=total,
            paid_pricing=paid_pricing,
        )
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
            paid_pricing=paid_pricing,
        )

    def __post_init__(self) -> None:
        expected_total = self.spec.size_bytes + self.rubric.size_bytes + self.response_schema.size_bytes + self.prompt_template.size_bytes
        if (
            self.total_payload_bytes != expected_total
            or not _is_sha256(self.manifest_sha256)
            or (self.paid_pricing is not None and self.paid_pricing.route != self.requested_model_route)
        ):
            raise ValueError("invalid disclosure manifest")

    def has_valid_digest(self) -> bool:
        """Return whether the stored digest still covers every manifest field."""
        document = _manifest_document(
            transport=self.transport,
            requested_model_route=self.requested_model_route,
            spec_path=self.spec_path,
            spec=self.spec,
            rubric=self.rubric,
            response_schema=self.response_schema,
            prompt_template=self.prompt_template,
            rubric_version=self.rubric_version,
            total_payload_bytes=self.total_payload_bytes,
            paid_pricing=self.paid_pricing,
        )
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
    paid_pricing: PaidPricingDisclosure | None = None

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
            schema=PAID_SPEC_REVIEW_RUN_SCHEMA if manifest.paid_pricing is not None else SPEC_REVIEW_RUN_SCHEMA,
            paid_pricing=manifest.paid_pricing,
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
            schema=PAID_SPEC_REVIEW_RUN_SCHEMA if manifest.paid_pricing is not None else SPEC_REVIEW_RUN_SCHEMA,
            paid_pricing=manifest.paid_pricing,
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
            or self.schema != (PAID_SPEC_REVIEW_RUN_SCHEMA if self.paid_pricing is not None else SPEC_REVIEW_RUN_SCHEMA)
            or not isinstance(self.status, ReviewStatus)
        ):
            raise ValueError("invalid host provenance")
        if self.paid_pricing is not None and self.paid_pricing.route != self.requested_model_route:
            raise ValueError("invalid paid pricing provenance")
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


def _manifest_document(
    *,
    transport: str,
    requested_model_route: str,
    spec_path: str,
    spec: DisclosureComponent,
    rubric: DisclosureComponent,
    response_schema: DisclosureComponent,
    prompt_template: DisclosureComponent,
    rubric_version: str,
    total_payload_bytes: int,
    paid_pricing: PaidPricingDisclosure | None,
) -> dict[str, object]:
    document: dict[str, object] = {
        "requested_model_route": requested_model_route,
        "response_schema": _component_document(response_schema),
        "prompt_template": _component_document(prompt_template),
        "rubric": _component_document(rubric),
        "rubric_version": rubric_version,
        "spec_path": spec_path,
        "spec": _component_document(spec),
        "total_payload_bytes": total_payload_bytes,
        "transport": transport,
    }
    if paid_pricing is not None:
        document["paid_pricing"] = paid_pricing.consent_document()
    return document


def _paid_pricing_values(
    *,
    route: str,
    max_estimated_cost_usd: str,
    price_leaves: tuple[tuple[str, str], ...],
    context_limit: int,
    output_limit: int,
) -> tuple[str, tuple[tuple[str, str], ...], str, str]:
    if not route or isinstance(context_limit, bool) or isinstance(output_limit, bool):
        raise ValueError("invalid paid pricing metadata")
    if context_limit <= 0 or output_limit <= 0:
        raise ValueError("invalid paid pricing limits")
    threshold = _decimal_value(max_estimated_cost_usd)
    if threshold <= 0 or threshold > _MAX_LOCAL_ESTIMATE_USD:
        raise ValueError("invalid maximum estimated cost")
    if not price_leaves:
        raise ValueError("paid pricing leaves are required")
    parsed: dict[str, Decimal] = {}
    for key, raw_value in price_leaves:
        if key not in _PAID_PRICE_KEYS or key in parsed:
            raise ValueError("unknown or duplicate paid price leaf")
        value = _decimal_value(raw_value)
        if value < 0:
            raise ValueError("paid price leaves must be non-negative")
        parsed[key] = value
    if not {"input", "output"} <= parsed.keys():
        raise ValueError("input and output prices are required")
    canonical_leaves = tuple(sorted((key, _canonical_decimal(value)) for key, value in parsed.items()))
    input_rate = sum((value for key, value in parsed.items() if key != "output"), Decimal(0))
    estimated = (
        (input_rate * context_limit + parsed["output"] * output_limit) / _TOKENS_PER_MILLION
    ).quantize(_MONEY_QUANTUM, rounding=ROUND_CEILING)
    if estimated > threshold:
        raise ValueError("advertised maximum estimate exceeds local threshold")
    metadata_document = {
        "limit": {"context": context_limit, "output": output_limit},
        "prices": dict(canonical_leaves),
        "route": route,
    }
    return (
        _canonical_decimal(threshold),
        canonical_leaves,
        format(estimated, ".6f"),
        sha256(_canonical_json(metadata_document)).hexdigest(),
    )


def _decimal_value(raw_value: str | Decimal) -> Decimal:
    if isinstance(raw_value, bool):
        raise ValueError("boolean is not a decimal")
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal value") from None
    if not value.is_finite():
        raise ValueError("decimal value must be finite")
    return value


def _canonical_decimal(value: Decimal) -> str:
    canonical = format(value.normalize(), "f")
    return "0" if canonical in {"-0", ""} else canonical


def _canonical_json(document: object) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _has_length(value: str, minimum: int, maximum: int) -> bool:
    return isinstance(value, str) and minimum <= len(value) <= maximum


def _is_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{64}", value))
