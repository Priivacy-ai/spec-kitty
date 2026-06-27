"""Scope: charter directive interpolation of the operator's documentation_policy answer.

Drives the public ``compile_charter`` generation surface (the same entry the
``spec-kitty charter generate --from-interview`` CLI invokes) and asserts that the
operator's ``documentation_policy`` answer is interpolated verbatim into the
generated ``charter.md`` Project Directives section, mirroring ``risk_boundaries``
(FR-001), while an absent answer emits no directive line (FR-002). Closes #2153.
"""

from charter.compiler import compile_charter
from charter.interview import apply_answer_overrides, default_interview
import pytest

pytestmark = pytest.mark.fast

# Realistic operator-shaped answers (C-007): production-format prose, not placeholders.
SENTINEL_DOCS = "SENTINEL_DOCS: maintain CHANGELOG + CONTRIBUTING; adopt Divio"
SENTINEL_RISK = "SENTINEL_RISK: privacy non-negotiable"


def _compile_with_answers(**answers: str) -> str:
    """Compile a software-dev charter with the supplied interview answers, return markdown."""
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(interview, answers=answers)
    compiled = compile_charter(mission="software-dev", interview=interview)
    return compiled.markdown


def test_documentation_policy_answer_is_interpolated_into_directives() -> None:
    """FR-001: the documentation_policy answer renders verbatim alongside risk_boundaries.

    RED-first proof (C-005): pre-fix the directive line is hardcoded, so SENTINEL_DOCS
    is absent from the generated charter while SENTINEL_RISK (already interpolated) is present.
    """
    # Arrange + Act
    markdown = _compile_with_answers(
        documentation_policy=SENTINEL_DOCS,
        risk_boundaries=SENTINEL_RISK,
    )

    # Assert -- the already-working risk path anchors that the directives section rendered.
    assert SENTINEL_RISK in markdown, "risk_boundaries answer must be interpolated (control)"
    # The dropped answer: this is the contract under test.
    assert SENTINEL_DOCS in markdown, "documentation_policy answer must be interpolated verbatim"


def test_absent_documentation_policy_emits_no_directive_line() -> None:
    """FR-002 (regression guard): an absent answer emits no documentation directive line.

    The surrounding directives must still render -- only the documentation line is gated off.
    """
    # Arrange + Act -- risk present so the directives section is non-empty, docs omitted.
    markdown = _compile_with_answers(risk_boundaries=SENTINEL_RISK)

    # Assert
    assert SENTINEL_RISK in markdown, "surrounding directives must still render"
    assert "Keep documentation synchronized" not in markdown, (
        "no documentation directive line when documentation_policy is absent"
    )
