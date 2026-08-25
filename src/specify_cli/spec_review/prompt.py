"""Bounded prompt composition and exact-span privacy checks."""

from __future__ import annotations

import json
import unicodedata
from typing import Final

from .models import SpecReviewFinding
from .preflight import ReviewPromptTemplate, ReviewResponseSchema, ReviewRubric, SpecSnapshot


_MIN_ECHO_SPAN: Final = 32


class OutputPrivacyViolation(ValueError):
    """Safe invalid-output signal that never embeds model text or source text."""

    def __init__(self) -> None:
        super().__init__("review response contains an exact input span")


def build_prompt(
    *,
    snapshot: SpecSnapshot,
    rubric: ReviewRubric,
    response_schema: ReviewResponseSchema,
    prompt_template: ReviewPromptTemplate,
) -> bytes:
    """Serialize only immutable spec, rubric, schema, and template inputs for stdin."""
    try:
        document = {
            "response_schema": response_schema.serialized.decode("utf-8"),
            "response_schema_version": response_schema.version,
            "rubric": rubric.serialized.decode("utf-8"),
            "rubric_version": rubric.manifest_version,
            "prompt_template": prompt_template.serialized.decode("utf-8"),
            "prompt_template_version": prompt_template.version,
            "spec": snapshot.text,
        }
    except UnicodeDecodeError as error:
        raise ValueError("rubric must be valid UTF-8") from error
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def validate_finding_privacy(finding: SpecReviewFinding, source_text: str) -> None:
    """Reject model fields containing any normalized source span of 32+ characters."""
    normalized_source = _normalize(source_text)
    for value in (finding.title, finding.claim, finding.remediation):
        if _contains_input_span(_normalize(value), normalized_source):
            raise OutputPrivacyViolation()


def _contains_input_span(candidate: str, source: str) -> bool:
    if len(candidate) < _MIN_ECHO_SPAN:
        return False
    return any(candidate[index : index + _MIN_ECHO_SPAN] in source for index in range(len(candidate) - _MIN_ECHO_SPAN + 1))


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
