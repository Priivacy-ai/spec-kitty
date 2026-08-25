"""Fail-closed parser for the untrusted ``review-response/v1`` contract."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final, cast

from .models import LineEvidence, ReviewResponse, SpecReviewFinding
from .prompt import OutputPrivacyViolation, validate_finding_privacy


MAX_RESPONSE_BYTES: Final = 2 * 1024 * 1024
_RESPONSE_FIELDS: Final = frozenset({"schema", "findings"})
_FINDING_FIELDS: Final = frozenset({"id", "lens", "severity", "title", "evidence", "claim", "remediation"})
_EVIDENCE_FIELDS: Final = frozenset({"line_start", "line_end"})


class InvalidReviewResponse(ValueError):
    """A stable invalid-output error that never exposes untrusted payload text."""

    def __init__(self) -> None:
        super().__init__("invalid review response")


def parse_review_response_bytes(payload: bytes, *, line_count: int, source_text: str) -> ReviewResponse:
    """Parse a bounded JSON payload and validate it against the review-response contract."""
    if not payload or len(payload) > MAX_RESPONSE_BYTES or payload != payload.strip():
        raise InvalidReviewResponse()
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidReviewResponse() from error
    if not isinstance(decoded, dict):
        raise InvalidReviewResponse()
    return parse_review_response(cast(Mapping[str, object], decoded), line_count=line_count, source_text=source_text)


def parse_review_response(payload: Mapping[str, object], *, line_count: int, source_text: str) -> ReviewResponse:
    """Validate a decoded model object without accepting host provenance fields."""
    if set(payload) != _RESPONSE_FIELDS or payload.get("schema") != "review-response/v1":
        raise InvalidReviewResponse()
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list) or len(raw_findings) > 100:
        raise InvalidReviewResponse()
    findings = tuple(_parse_finding(raw, line_count=line_count, source_text=source_text) for raw in raw_findings)
    try:
        return ReviewResponse.create(findings)
    except ValueError as error:
        raise InvalidReviewResponse() from error


def _parse_finding(raw: object, *, line_count: int, source_text: str) -> SpecReviewFinding:
    if not isinstance(raw, dict) or set(raw) != _FINDING_FIELDS:
        raise InvalidReviewResponse()
    evidence = raw.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != _EVIDENCE_FIELDS:
        raise InvalidReviewResponse()
    try:
        finding = SpecReviewFinding(
            identifier=_text(raw, "id"),
            lens=_text(raw, "lens"),
            severity=_integer(raw, "severity"),
            title=_text(raw, "title"),
            evidence=LineEvidence(
                line_start=_integer(cast(Mapping[str, object], evidence), "line_start"),
                line_end=_integer(cast(Mapping[str, object], evidence), "line_end"),
            ),
            claim=_text(raw, "claim"),
            remediation=_text(raw, "remediation"),
        )
        finding.evidence.validate_for_line_count(line_count)
        validate_finding_privacy(finding, source_text)
    except (OutputPrivacyViolation, ValueError) as error:
        raise InvalidReviewResponse() from error
    return finding


def _text(document: Mapping[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str):
        raise InvalidReviewResponse()
    return value


def _integer(document: Mapping[str, object], key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidReviewResponse()
    return value
