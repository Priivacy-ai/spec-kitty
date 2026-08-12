"""Red-first reproduction of #3231 — a leftover finalize-tasks scaffold row
makes the acceptance aggregate ``pending`` and blocks acceptance.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3231

Root cause (both lines verified against current source):

* ``AcceptanceMatrix.overall_verdict`` (``src/specify_cli/acceptance/matrix.py``)
  makes ``pending`` DOMINATE — one ``pending`` row outvotes any number of
  ``pass`` rows (``if any(v == "pending" ...): return "pending"``).
* The row-union reconciler ``reconcile_acceptance_matrix_documents``
  (``src/specify_cli/cli/commands/merge_driver.py``) admits BOTH sides' rows on
  an add/add divergence (``#3076`` FR-008), so after a mission→target squash
  merge the merged document legitimately contains the ``finalize-tasks``
  placeholder row (``AC-001``, ``pass_fail="pending"``, ``notes=SCAFFOLD_TODO_MARKER``)
  alongside the real, all-``pass`` criteria — and that one scaffold row poisons
  the whole verdict, blocking acceptance even though every real criterion passes.

This drives the REAL production reconciler exactly as the issue measured it
(FILLED as *ours*, the scaffold PLACEHOLDER as *theirs*, empty base — the add/add
divergence).

Desired post-fix outcome (either resolution turns this green): a mission whose
real acceptance criteria all ``pass`` must NOT be blocked by a leftover
``finalize-tasks`` scaffold placeholder — the aggregate is admissible (not
``pending``). Whether the reconciler suppresses the scaffold row or the verdict
computation becomes scaffold-aware is a product decision (issue #3231); this test
pins the observable behavioural contract, not the mechanism.
"""

from __future__ import annotations

import pytest

from specify_cli.acceptance.matrix import SCAFFOLD_TODO_MARKER
from specify_cli.cli.commands.merge_driver import reconcile_acceptance_matrix_documents

pytestmark = pytest.mark.regression


def _pass_criterion(criterion_id: str) -> dict[str, object]:
    return {
        "criterion_id": criterion_id,
        "description": f"Verify {criterion_id} is satisfied",
        "proof_type": "automated_test",
        "pass_fail": "pass",
        "evidence": f"tests/test_{criterion_id.lower()}.py::test_it",
    }


def _scaffold_placeholder_row() -> dict[str, object]:
    # Exactly what `finalize-tasks` writes for an un-authored matrix
    # (src/specify_cli/acceptance/matrix.py scaffold builder).
    return {
        "criterion_id": "AC-001",
        "description": SCAFFOLD_TODO_MARKER,
        "proof_type": "automated_test",
        "pass_fail": "pending",
        "notes": SCAFFOLD_TODO_MARKER,
    }


def test_scaffold_pending_row_does_not_poison_acceptance_verdict() -> None:
    ours_filled = {
        "mission_slug": "example-mission",
        "criteria": [_pass_criterion("FR-001"), _pass_criterion("FR-003")],
    }
    theirs_scaffold = {
        "mission_slug": "example-mission",
        "criteria": [_scaffold_placeholder_row()],
    }
    # Empty base == the add/add divergence the row-union authority model faces.
    merged = reconcile_acceptance_matrix_documents({}, ours_filled, theirs_scaffold)

    real_criteria = [c for c in merged["criteria"] if c["criterion_id"] != "AC-001"]
    assert real_criteria, "sanity: the real, filled criteria survived the merge"
    assert all(c["pass_fail"] == "pass" for c in real_criteria), (
        "sanity: every real criterion is 'pass'; only the scaffold placeholder is 'pending'"
    )

    # RED today: a single admitted scaffold placeholder makes the aggregate
    # 'pending', blocking acceptance despite every real criterion passing.
    assert merged["overall_verdict"] != "pending", (
        "a leftover finalize-tasks scaffold placeholder row must not poison the "
        f"acceptance aggregate; got overall_verdict={merged['overall_verdict']!r} "
        f"with rows={[(c['criterion_id'], c['pass_fail']) for c in merged['criteria']]}"
    )
