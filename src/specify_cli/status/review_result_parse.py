"""Canonical parser for external review-outcome JSON (FR-010, FR-011).

Co-located with :class:`~specify_cli.status.models.ReviewResult` so both verdict
surfaces -- ``orchestrator-api transition`` and (WP09) ``agent status emit`` --
validate ``--review-result-json`` through the SAME function rather than each
re-implementing the shape checks. Depends only on ``json`` and the two ``status``
siblings (:class:`ReviewResult`, :func:`event_verdicts`) -- no new import cycle,
since every consumer already imports ``status``.
"""

from __future__ import annotations

import json

from .models import ReviewResult
from .verdict_vocab import event_verdicts

__all__ = ["parse_review_result_json"]


def parse_review_result_json(raw: str) -> ReviewResult:
    """Parse the external review outcome accepted by the verdict surfaces.

    Raises :class:`ValueError` with a surface-neutral message on any invalid
    shape; each surface renders its own envelope/CLI error from that message.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in --review-result-json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--review-result-json must decode to a JSON object")

    reviewer = parsed.get("reviewer")
    verdict = parsed.get("verdict")
    reference = parsed.get("reference")
    if not all(isinstance(value, str) and value.strip() for value in (reviewer, verdict, reference)):
        raise ValueError("--review-result-json requires non-empty reviewer, verdict, and reference strings")
    if verdict not in event_verdicts():
        raise ValueError("--review-result-json verdict must be 'approved' or 'changes_requested'")
    feedback_path = parsed.get("feedback_path")
    if feedback_path is not None and not isinstance(feedback_path, str):
        raise ValueError("--review-result-json feedback_path must be a string")
    return ReviewResult(
        reviewer=reviewer,
        verdict=verdict,
        reference=reference,
        feedback_path=feedback_path,
    )
