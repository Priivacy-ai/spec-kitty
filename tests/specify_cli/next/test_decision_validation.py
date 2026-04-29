"""Construction-time validation tests for ``Decision`` (#844 / WP02 / T009).

Locks in the ``kind="step"`` prompt-file contract (C1/C2 in
``kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md``):

- C1: ``kind="step"`` ``prompt_file`` is non-null and non-empty.
- C2: ``kind="step"`` ``prompt_file`` resolves on disk (``Path.is_file()``).
- C3: non-step kinds (``blocked``, ``terminal``, ``decision_required``,
  ``query``) remain permissive — ``prompt_file=None`` is legal there.

Constraint C-005: do NOT weaken the ``kind="step"`` contract. The validator
fires at construction time so the wire format is self-consistent by
definition.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.next.decision import (
    Decision,
    DecisionKind,
    InvalidStepDecision,
)

pytestmark = pytest.mark.fast


_TIMESTAMP = "2026-04-28T00:00:00+00:00"
_MISSION_SLUG = "charter-e2e-827-followups-01KQAJA0"
_MISSION = "software-dev"


def _step_kwargs(prompt_file: str | None) -> dict[str, object]:
    """Common kwargs for a ``kind="step"`` Decision under test."""
    return {
        "kind": DecisionKind.step,
        "agent": "claude",
        "mission_slug": _MISSION_SLUG,
        "mission": _MISSION,
        "mission_state": "implement",
        "timestamp": _TIMESTAMP,
        "action": "implement",
        "wp_id": "WP02",
        "prompt_file": prompt_file,
    }


class TestStepDecisionContract:
    """C1/C2: kind=step requires a non-null, on-disk-resolvable prompt_file."""

    def test_step_with_real_prompt_file_succeeds(self, tmp_path: Path) -> None:
        prompt = tmp_path / "implement-WP02.md"
        prompt.write_text("# implement prompt\n", encoding="utf-8")

        decision = Decision(**_step_kwargs(prompt_file=str(prompt)))

        assert decision.kind == DecisionKind.step
        assert decision.prompt_file == str(prompt)

    def test_step_with_null_prompt_raises(self) -> None:
        with pytest.raises(InvalidStepDecision) as exc_info:
            Decision(**_step_kwargs(prompt_file=None))

        # The exception is a ValueError so call sites can catch it cleanly.
        assert isinstance(exc_info.value, ValueError)
        assert "non-empty" in str(exc_info.value)

    def test_step_with_empty_prompt_raises(self) -> None:
        with pytest.raises(InvalidStepDecision) as exc_info:
            Decision(**_step_kwargs(prompt_file=""))

        assert "non-empty" in str(exc_info.value)

    def test_step_with_nonexistent_prompt_raises(self, tmp_path: Path) -> None:
        bogus = tmp_path / "definitely-does-not-exist-9f2c7a.md"
        assert not bogus.exists()

        with pytest.raises(InvalidStepDecision) as exc_info:
            Decision(**_step_kwargs(prompt_file=str(bogus)))

        assert "resolve on disk" in str(exc_info.value)


class TestNonStepKindsArePermissive:
    """C3: non-step kinds remain permissive — prompt_file=None is legal."""

    def test_blocked_with_null_prompt_succeeds(self) -> None:
        decision = Decision(
            kind=DecisionKind.blocked,
            agent="claude",
            mission_slug=_MISSION_SLUG,
            mission=_MISSION,
            mission_state="implement",
            timestamp=_TIMESTAMP,
            reason="prompt_file_not_resolvable",
            prompt_file=None,
        )

        assert decision.kind == DecisionKind.blocked
        assert decision.prompt_file is None

    def test_terminal_with_null_prompt_succeeds(self) -> None:
        decision = Decision(
            kind=DecisionKind.terminal,
            agent="claude",
            mission_slug=_MISSION_SLUG,
            mission=_MISSION,
            mission_state="done",
            timestamp=_TIMESTAMP,
            reason="Mission complete",
            prompt_file=None,
        )

        assert decision.kind == DecisionKind.terminal
        assert decision.prompt_file is None

    def test_decision_required_with_null_prompt_succeeds(self) -> None:
        decision = Decision(
            kind=DecisionKind.decision_required,
            agent="claude",
            mission_slug=_MISSION_SLUG,
            mission=_MISSION,
            mission_state="planning",
            timestamp=_TIMESTAMP,
            question="Pick an option",
            options=["A", "B"],
            decision_id="dec-1",
            prompt_file=None,
        )

        assert decision.kind == DecisionKind.decision_required
        assert decision.prompt_file is None

    def test_query_with_null_prompt_succeeds(self) -> None:
        decision = Decision(
            kind=DecisionKind.query,
            agent="claude",
            mission_slug=_MISSION_SLUG,
            mission=_MISSION,
            mission_state="specify",
            timestamp=_TIMESTAMP,
            is_query=True,
            prompt_file=None,
        )

        assert decision.kind == DecisionKind.query
        assert decision.is_query is True
        assert decision.prompt_file is None
