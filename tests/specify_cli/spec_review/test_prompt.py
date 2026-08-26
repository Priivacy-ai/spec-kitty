"""Tests for the bounded prompt builder and output echo filter."""

import pytest

from specify_cli.spec_review.models import LineEvidence, SpecReviewFinding
from specify_cli.spec_review.preflight import ReviewPromptTemplate, ReviewResponseSchema, ReviewRubric, SpecSnapshot
from specify_cli.spec_review.prompt import OutputPrivacyViolation, build_prompt, validate_finding_privacy


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_prompt_uses_only_immutable_inputs_without_local_context() -> None:
    sentinel = "S" * 32
    snapshot = SpecSnapshot(payload=f"# Synthetic\n{sentinel}\n".encode(), text=f"# Synthetic\n{sentinel}\n", line_count=2, scanner_version="heuristic-v1")
    prompt = build_prompt(
        snapshot=snapshot,
        rubric=ReviewRubric(version="v1", serialized=b'{"rubric":"contract"}', scanner_version="heuristic-v1"),
        response_schema=ReviewResponseSchema(version="review-response/v1", serialized=b"schema: review-response/v1\n"),
        prompt_template=ReviewPromptTemplate(version="review-template/v1", serialized=b"Review only the supplied spec."),
    )

    assert sentinel in prompt.decode("utf-8")
    assert "repo_root" not in prompt.decode("utf-8")
    assert "tasks.md" not in prompt.decode("utf-8")
    assert "Review only the supplied spec." in prompt.decode("utf-8")


def test_exact_input_span_is_rejected_without_echoing_the_span() -> None:
    sentinel = "S" * 32
    finding = SpecReviewFinding(
        identifier="F-1",
        lens="privacy",
        severity=4,
        title=sentinel,
        evidence=LineEvidence(line_start=1, line_end=1),
        claim="Generic claim.",
        remediation="Generic remediation.",
    )

    with pytest.raises(OutputPrivacyViolation) as error:
        validate_finding_privacy(finding, f"# Synthetic\n{sentinel}\n")

    assert sentinel not in str(error.value)


def test_short_generic_text_is_allowed() -> None:
    finding = SpecReviewFinding(
        identifier="F-1",
        lens="clarity",
        severity=2,
        title="Clarify scope",
        evidence=LineEvidence(line_start=1, line_end=1),
        claim="The scope is vague.",
        remediation="State the boundary.",
    )

    validate_finding_privacy(finding, "# Synthetic mission\n")


def test_prompt_rejects_non_utf8_template_bytes_without_echoing_them() -> None:
    snapshot = SpecSnapshot(payload=b"# Synthetic\n", text="# Synthetic\n", line_count=1, scanner_version="heuristic-v1")

    with pytest.raises(ValueError) as error:
        build_prompt(
            snapshot=snapshot,
            rubric=ReviewRubric(version="v1", serialized=b'{"rubric":"contract"}', scanner_version="heuristic-v1"),
            response_schema=ReviewResponseSchema(version="review-response/v1", serialized=b"schema: review-response/v1\n"),
            prompt_template=ReviewPromptTemplate(version="review-template/v1", serialized=b"\xff"),
        )

    assert "\ufffd" not in str(error.value)
