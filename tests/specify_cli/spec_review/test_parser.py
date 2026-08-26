"""Strict contract tests for untrusted review-response payloads."""

import json

import pytest

from specify_cli.spec_review.models import ReviewStatus
from specify_cli.spec_review.parser import InvalidReviewResponse, MAX_RESPONSE_BYTES, parse_review_response_bytes


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _payload(**overrides: object) -> bytes:
    finding: dict[str, object] = {
        "id": "F-1",
        "lens": "clarity",
        "severity": 3,
        "title": "Clarify scope",
        "evidence": {"line_start": 1, "line_end": 2},
        "claim": "The scope is vague.",
        "remediation": "State the boundary.",
    }
    body: dict[str, object] = {"schema": "review-response/v1", "findings": [finding]}
    body.update(overrides)
    return json.dumps(body).encode("utf-8")


@pytest.mark.parametrize(
    "payload",
    [
        _payload(run_id="not-model-owned"),
        _payload(findings=[{"id": "F-1"}] * 101),
    ],
)
def test_parser_rejects_unknown_or_invalid_contract_shapes(payload: bytes) -> None:
    with pytest.raises(InvalidReviewResponse):
        parse_review_response_bytes(payload, line_count=2, source_text="# Synthetic\nline\n")


def test_parser_validates_ranges_and_exact_input_spans_without_echoing_them() -> None:
    sentinel = "P" * 32
    invalid_range = _payload(findings=[{
        "id": "F-1", "lens": "clarity", "severity": 3, "title": "Clarify",
        "evidence": {"line_start": 3, "line_end": 2}, "claim": "Generic", "remediation": "Generic"
    }])
    echoed = _payload(findings=[{
        "id": "F-1", "lens": "privacy", "severity": 3, "title": sentinel,
        "evidence": {"line_start": 1, "line_end": 1}, "claim": "Generic", "remediation": "Generic"
    }])

    for payload in (invalid_range, echoed):
        with pytest.raises(InvalidReviewResponse) as error:
            parse_review_response_bytes(payload, line_count=2, source_text=f"{sentinel}\nshort\n")
        assert sentinel not in str(error.value)


def test_parser_enforces_payload_limit_and_host_failure_shape() -> None:
    with pytest.raises(InvalidReviewResponse):
        parse_review_response_bytes(b" " * (MAX_RESPONSE_BYTES + 1), line_count=1, source_text="x\n")

    assert ReviewStatus.INVALID_OUTPUT.value == "invalid_output"


@pytest.mark.parametrize(
    "payload",
    [bytes([255]), b"{", b"[]", b"{}"],
    ids=["invalid-utf8", "truncated-json", "array-root", "empty-object"],
)
def test_parser_rejects_invalid_encoding_json_and_top_level_shapes(payload: bytes) -> None:
    with pytest.raises(InvalidReviewResponse):
        parse_review_response_bytes(payload, line_count=2, source_text="# Synthetic\nline\n")


def test_parser_accepts_a_valid_empty_findings_response() -> None:
    response = parse_review_response_bytes(
        b'{"schema":"review-response/v1","findings":[]}',
        line_count=1,
        source_text="# Synthetic\n",
    )

    assert response.findings == ()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.update(findings="not-a-list"),
        lambda body: body.update(findings=[{"id": "F-1"}]),
        lambda body: body["findings"][0].update(evidence={"line_start": 1, "line_end": 3}),
        lambda body: body["findings"][0].update(severity=True),
        lambda body: body["findings"][0].update(title=123),
    ],
)
def test_parser_rejects_invalid_finding_shapes_and_types(mutation) -> None:  # type: ignore[no-untyped-def]
    body = json.loads(_payload())
    mutation(body)

    with pytest.raises(InvalidReviewResponse):
        parse_review_response_bytes(json.dumps(body).encode("utf-8"), line_count=2, source_text="# Synthetic\nline\n")


@pytest.mark.parametrize("field", ["claim", "remediation"])
def test_parser_rejects_exact_input_spans_in_every_model_authored_text_field(field: str) -> None:
    sentinel = "P" * 32
    body = json.loads(_payload())
    body["findings"][0][field] = sentinel

    with pytest.raises(InvalidReviewResponse) as error:
        parse_review_response_bytes(json.dumps(body).encode("utf-8"), line_count=2, source_text=f"{sentinel}\nline\n")

    assert sentinel not in str(error.value)


@pytest.mark.parametrize("payload", [b" " + _payload(), _payload() + b"\n"])
def test_parser_rejects_any_bytes_outside_the_single_json_document(payload: bytes) -> None:
    with pytest.raises(InvalidReviewResponse):
        parse_review_response_bytes(payload, line_count=2, source_text="# Synthetic\nline\n")
