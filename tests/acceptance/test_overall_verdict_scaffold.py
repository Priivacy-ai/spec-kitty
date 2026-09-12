"""Guard tests for #3231 — ``overall_verdict`` exempts ONLY the empty
``finalize-tasks`` scaffold placeholder from the pending-dominates rule.

These are pure-unit tests: :class:`AcceptanceMatrix` and
:class:`AcceptanceCriterion` are constructed directly and ``overall_verdict``
is read as a property. No filesystem, subprocess, or git — the discriminator
under test (``description == SCAFFOLD_TODO_MARKER``, see
``src/specify_cli/acceptance/matrix.py``) is pure dataclass logic.

C-003 (the binding constraint this suite exists to pin): the discriminator is
``description`` and ONLY ``description``.

- Discriminating on ``notes == SCAFFOLD_TODO_MARKER`` would false-accept a
  seeded-but-unauthored per-requirement row (real ``description``, marker
  only in ``notes``) through the acceptance gate — the "partial authoring"
  and "all-scaffold" cases below pin that this does NOT happen.
- Discriminating on ``criterion_id == "AC-001"`` would false-accept a
  genuine, still-pending, hand-authored ``AC-001`` — the "real AC-001" case
  below pins that this does NOT happen.
"""

from __future__ import annotations

import pytest

from specify_cli.acceptance.matrix import (
    SCAFFOLD_TODO_MARKER,
    AcceptanceCriterion,
    AcceptanceMatrix,
)

pytestmark = pytest.mark.unit


def _pass_criterion(criterion_id: str) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id=criterion_id,
        description=f"Verify {criterion_id} is satisfied",
        proof_type="automated_test",
        pass_fail="pass",
        evidence=f"tests/test_{criterion_id.lower()}.py::test_it",
    )


def _seeded_pending_fr_row(criterion_id: str) -> AcceptanceCriterion:
    """A ``finalize-tasks``-seeded per-requirement row: REAL description, marker
    only in ``notes`` — the shape that must NEVER be exempted (matrix.py:517-520).
    """
    return AcceptanceCriterion(
        criterion_id=criterion_id,
        description=f"Verify {criterion_id} is satisfied",
        proof_type="automated_test",
        pass_fail="pending",
        notes=SCAFFOLD_TODO_MARKER,
    )


def _empty_scaffold_placeholder() -> AcceptanceCriterion:
    """The contentless ``AC-001`` placeholder ``finalize-tasks`` writes for an
    un-authored matrix (matrix.py:526-534) — description IS the marker.
    """
    return AcceptanceCriterion(
        criterion_id="AC-001",
        description=SCAFFOLD_TODO_MARKER,
        proof_type="automated_test",
        pass_fail="pending",
        notes=SCAFFOLD_TODO_MARKER,
    )


def _real_ac001() -> AcceptanceCriterion:
    """A genuine, hand-authored, still-pending ``AC-001`` — real description,
    NO marker anywhere. Exists to defeat a ``criterion_id == "AC-001"``
    shortcut discriminator.
    """
    return AcceptanceCriterion(
        criterion_id="AC-001",
        description="Verify the login form rejects an empty password",
        proof_type="manual_qa",
        pass_fail="pending",
    )


def test_real_all_pass_plus_empty_scaffold_placeholder_is_not_pending() -> None:
    """#3231 core repro: real criteria all pass, leftover empty AC-001
    placeholder must not poison the verdict."""
    matrix = AcceptanceMatrix(
        mission_slug="example-mission",
        criteria=[
            _pass_criterion("FR-001"),
            _pass_criterion("FR-003"),
            _empty_scaffold_placeholder(),
        ],
    )

    assert matrix.overall_verdict != "pending"
    assert matrix.overall_verdict == "pass"


def test_partial_authoring_nine_of_ten_seeded_rows_still_pending() -> None:
    """C-003: a real (non-marker) ``description`` on a seeded FR row must
    NEVER be exempted — 9 unauthored + 1 authored FR rows still block
    acceptance."""
    seeded_pending = [_seeded_pending_fr_row(f"FR-{i:03d}") for i in range(1, 10)]
    matrix = AcceptanceMatrix(
        mission_slug="example-mission",
        criteria=[*seeded_pending, _pass_criterion("FR-010")],
    )

    assert matrix.overall_verdict == "pending"


def test_all_scaffold_seeded_fr_rows_only_stays_pending() -> None:
    """All-scaffold matrix (only seeded, unauthored FR rows) — nothing real has
    been authored yet, so the verdict must stay ``pending``."""
    matrix = AcceptanceMatrix(
        mission_slug="example-mission",
        criteria=[_seeded_pending_fr_row(f"FR-{i:03d}") for i in range(1, 4)],
    )

    assert matrix.overall_verdict == "pending"


def test_single_empty_scaffold_only_matrix_stays_pending() -> None:
    """The "no non-scaffold criterion exists" branch: a matrix containing
    ONLY the empty AC-001 placeholder (freshly scaffolded, never touched)
    must stay ``pending`` — there is nothing real to accept yet."""
    matrix = AcceptanceMatrix(
        mission_slug="example-mission",
        criteria=[_empty_scaffold_placeholder()],
    )

    assert matrix.overall_verdict == "pending"


def test_real_ac001_pending_no_marker_stays_pending() -> None:
    """C-003: defeats a ``criterion_id == "AC-001"`` shortcut discriminator —
    a genuine, hand-authored, still-pending AC-001 (real description, no
    marker anywhere) must still block acceptance."""
    matrix = AcceptanceMatrix(
        mission_slug="example-mission",
        criteria=[_pass_criterion("FR-001"), _real_ac001()],
    )

    assert matrix.overall_verdict == "pending"
