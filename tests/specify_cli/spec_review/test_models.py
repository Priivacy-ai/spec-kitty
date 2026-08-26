"""Contract tests for the host-owned spec review domain models."""

from dataclasses import fields, replace
from kernel.clock import UTC, datetime
from pathlib import Path

import pytest
import yaml

from specify_cli.spec_review.models import (
    DiagnosticCode,
    DisclosureComponent,
    DisclosureManifest,
    LineEvidence,
    ReviewResponse,
    ReviewStatus,
    SpecReviewFinding,
    SpecReviewRun,
)


def _finding(identifier: str = "F-1", severity: int = 3) -> SpecReviewFinding:
    return SpecReviewFinding(
        identifier=identifier,
        lens="completeness",
        severity=severity,
        title="Missing acceptance criterion",
        evidence=LineEvidence(line_start=1, line_end=1),
        claim="The expected result is not measurable.",
        remediation="Add an observable acceptance criterion.",
    )


def _completed_run() -> SpecReviewRun:
    return SpecReviewRun(
        run_id="run-contract",
        mission="synthetic-mission",
        spec_sha256="a" * 64,
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        actual_model="unverified",
        rubric_version="v1",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        status=ReviewStatus.COMPLETED,
        diagnostic_code=None,
        findings=(),
    )


def test_manifest_is_frozen_deterministic_and_covers_all_components() -> None:
    spec = DisclosureComponent.from_bytes("spec", b"# Synthetic specification\n")
    rubric = DisclosureComponent.from_bytes("rubric", b'{"version":"v1"}')
    schema = DisclosureComponent.from_bytes("response_schema", b"schema: review-response/v1\n")
    template = DisclosureComponent.from_bytes("prompt_template", b"template: review-v1\n")
    manifest = DisclosureManifest.create(
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        spec_path="spec.md",
        spec=spec,
        rubric=rubric,
        response_schema=schema,
        prompt_template=template,
        rubric_version="v1+scanner-heuristic-v1",
    )

    assert manifest.total_payload_bytes == spec.size_bytes + rubric.size_bytes + schema.size_bytes + template.size_bytes
    assert manifest.manifest_sha256 == DisclosureManifest.create(
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        spec_path="spec.md",
        spec=spec,
        rubric=rubric,
        response_schema=schema,
        prompt_template=template,
        rubric_version="v1+scanner-heuristic-v1",
    ).manifest_sha256
    with pytest.raises((AttributeError, TypeError)):
        manifest.transport = "other"  # type: ignore[misc]


def test_response_rejects_duplicate_ids_and_host_provenance() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ReviewResponse.create([_finding(), _finding()])

    with pytest.raises(TypeError):
        ReviewResponse(schema="review-response/v1", findings=(_finding(),), run_id="host-owned")  # type: ignore[call-arg]


def test_run_computes_summary_and_rejects_inconsistent_outcomes() -> None:
    response = ReviewResponse.create([_finding("F-1", 2), _finding("F-2", 5)])
    manifest = DisclosureManifest.create(
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        spec_path="spec.md",
        spec=DisclosureComponent.from_bytes("spec", b"# synthetic\n"),
        rubric=DisclosureComponent.from_bytes("rubric", b"{}"),
        response_schema=DisclosureComponent.from_bytes("response_schema", b"{}"),
        prompt_template=DisclosureComponent.from_bytes("prompt_template", b"{}"),
        rubric_version="v1+scanner-heuristic-v1",
    )
    complete = SpecReviewRun.from_response(
        run_id="run-1",
        mission="synthetic-mission",
        manifest=manifest,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        response=response,
    )

    assert complete.status is ReviewStatus.COMPLETED
    assert complete.schema == "spec-review-run/v1"
    assert complete.diagnostic_code is None
    assert complete.actual_model == "unverified"
    assert complete.summary.total == 2
    assert complete.summary.severity_2 == 1
    assert complete.summary.severity_5 == 1
    with pytest.raises(ValueError, match="failure"):
        SpecReviewRun(
            run_id="run-2",
            mission="synthetic-mission",
            spec_sha256="a" * 64,
            transport="opencode-loopback",
            requested_model_route="opencode/synthetic",
            actual_model="unverified",
            rubric_version="v1",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            status=ReviewStatus.TIMEOUT,
            diagnostic_code=DiagnosticCode.TIMEOUT,
            findings=(_finding(),),
        )


def test_run_rejects_non_persistable_invocation_outcomes() -> None:
    with pytest.raises(ValueError, match="persistable"):
        SpecReviewRun(
            run_id="run-3",
            mission="synthetic-mission",
            spec_sha256="a" * 64,
            transport="opencode-loopback",
            requested_model_route="opencode/synthetic",
            actual_model="unverified",
            rubric_version="v1",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            status=ReviewStatus.REFUSED,
            diagnostic_code=DiagnosticCode.REFUSED,
            findings=(),
        )


def test_run_fields_mirror_the_persisted_yaml_contract() -> None:
    contract_path = (
        Path(__file__).resolve().parents[3]
        / "kitty-specs"
        / "ox-alpha-spec-reviewer-01M0N82A"
        / "contracts"
        / "spec-review-run-v1.schema.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert set(contract["required"]) <= {field.name for field in fields(SpecReviewRun)}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "other/v1"),
        ("transport", "other-transport"),
        ("requested_model_route", "r" * 201),
        ("actual_model", "m" * 201),
    ],
)
def test_run_rejects_values_outside_the_persisted_contract(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="provenance"):
        replace(_completed_run(), **{field: value})
