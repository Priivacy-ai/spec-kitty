"""Regression tests for acceptance clarification marker detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.acceptance import _check_needs_clarification
from specify_cli.decisions.models import (
    DecisionIndex,
    DecisionStatus,
    IndexEntry,
    OriginFlow,
)
from specify_cli.decisions.store import save_index

pytestmark = pytest.mark.fast


def test_needs_clarification_ignores_descriptive_prose(tmp_path: Path) -> None:
    """Mentioning the marker syntax in prose is not an unresolved marker."""
    artifact = tmp_path / "research.md"
    artifact.write_text(
        "| Spec marker | Resolution |\n"
        "|-------------|------------|\n"
        "| (no `[NEEDS CLARIFICATION]` markers in spec) | n/a |\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == []


def test_needs_clarification_flags_canonical_marker(tmp_path: Path) -> None:
    """The acceptance gate still flags real deferred-decision markers."""
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "The system must choose a queue backend. "
        "[NEEDS CLARIFICATION: choose durable queue] <!-- decision_id: 01KS0ABCDEF0123456789ABCDE -->\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == [str(artifact)]


def test_needs_clarification_flags_malformed_decision_marker(tmp_path: Path) -> None:
    """Malformed clarification markers remain acceptance blockers."""
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "The system must choose a queue backend. "
        "[NEEDS CLARIFICATION: choose durable queue] <!-- decision_id: malformed -->\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == [str(artifact)]


def test_needs_clarification_handles_long_non_matching_line(tmp_path: Path) -> None:
    """Long prose near the marker syntax should not require regex backtracking."""
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "[NEEDS CLARIFICATION: " + ("x" * 20000) + "] <!-- not-a-decision marker -->\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == []


def test_needs_clarification_ignores_closed_decision_marker(tmp_path: Path) -> None:
    """A stale marker for a closed decision no longer blocks acceptance."""
    decision_id = "01KS0ABCDEF0123456789ABCDE"
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "The system accepted the plan default. "
        f"[NEEDS CLARIFICATION: choose durable queue] <!-- decision_id: {decision_id} -->\n",
        encoding="utf-8",
    )
    save_index(
        tmp_path,
        DecisionIndex(
            mission_id="mission-id",
            entries=(
                IndexEntry(
                    decision_id=decision_id,
                    origin_flow=OriginFlow.SPECIFY,
                    step_id="specify.queue",
                    input_key="queue",
                    question="Which queue?",
                    status=DecisionStatus.RESOLVED,
                    final_answer="accept plan default",
                    created_at=datetime(2026, 5, 21, tzinfo=UTC),
                    resolved_at=datetime(2026, 5, 21, tzinfo=UTC),
                    mission_id="mission-id",
                    mission_slug="mission-slug",
                ),
            ),
        ),
    )

    assert _check_needs_clarification([artifact]) == []


def test_needs_clarification_accepts_trailing_comment_metadata(tmp_path: Path) -> None:
    """Decision IDs keep the previous first-token parsing semantics."""
    decision_id = "01KS0ABCDEF0123456789ABCDE"
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "The system accepted the plan default. "
        f"[NEEDS CLARIFICATION: choose durable queue] <!-- decision_id: {decision_id} source: specify -->\n",
        encoding="utf-8",
    )
    save_index(
        tmp_path,
        DecisionIndex(
            mission_id="mission-id",
            entries=(
                IndexEntry(
                    decision_id=decision_id,
                    origin_flow=OriginFlow.SPECIFY,
                    step_id="specify.queue",
                    input_key="queue",
                    question="Which queue?",
                    status=DecisionStatus.RESOLVED,
                    final_answer="accept plan default",
                    created_at=datetime(2026, 5, 21, tzinfo=UTC),
                    resolved_at=datetime(2026, 5, 21, tzinfo=UTC),
                    mission_id="mission-id",
                    mission_slug="mission-slug",
                ),
            ),
        ),
    )

    assert _check_needs_clarification([artifact]) == []
