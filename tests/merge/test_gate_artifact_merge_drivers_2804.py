"""Unit coverage for the #2804 coord gate-artifact merge drivers.

The regression test ``tests/regression/test_issue_2804_merge_resets_gate_artifacts.py``
proves the end-to-end merge behavior. These tests pin the decision function
directly, including the orderings that integration test cannot reach: the reverse
case (fill authored on the mission branch, target still a scaffold), the tie, and
corrupt input.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.merge_driver import (
    _acceptance_matrix_fill_score,
    _issue_matrix_fill_score,
    merge_driver_acceptance_matrix,
    merge_driver_issue_matrix,
)

pytestmark = [pytest.mark.unit]

_SCAFFOLD_MATRIX = {
    "mission_slug": "m-01ABC",
    "overall_verdict": "pending",
    "criteria": [
        {
            "criterion_id": "AC-001",
            "description": "TODO: replace with a real acceptance criterion",
            "pass_fail": "pending",
            "evidence": None,
        }
    ],
    "negative_invariants": [],
}

_FILLED_MATRIX = {
    "mission_slug": "m-01ABC",
    "overall_verdict": "pass",
    "criteria": [
        {
            "criterion_id": "AC-001",
            "description": "The driver keeps the filled side",
            "pass_fail": "pass",
            "evidence": "tests/merge/test_gate_artifact_merge_drivers_2804.py",
        }
    ],
    "negative_invariants": [],
}

_SCAFFOLD_ISSUE_MATRIX = """# Issue matrix

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2804 | <fill at WP-implementation time> | unknown | <link or commit> |
"""

_FILLED_ISSUE_MATRIX = """# Issue matrix

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2804 | merge resets gate artifacts | fixed | abc1234 |
"""


def test_filled_acceptance_matrix_outscores_scaffold() -> None:
    filled = _acceptance_matrix_fill_score(json.dumps(_FILLED_MATRIX))
    scaffold = _acceptance_matrix_fill_score(json.dumps(_SCAFFOLD_MATRIX))
    assert filled > scaffold


def test_corrupt_acceptance_matrix_scores_below_any_valid_document() -> None:
    assert _acceptance_matrix_fill_score("{not json") == -1
    assert _acceptance_matrix_fill_score("[]") == -1
    assert _acceptance_matrix_fill_score(json.dumps(_SCAFFOLD_MATRIX)) > -1


def test_filled_issue_matrix_outscores_scaffold() -> None:
    assert _issue_matrix_fill_score(_FILLED_ISSUE_MATRIX) > _issue_matrix_fill_score(_SCAFFOLD_ISSUE_MATRIX)


def test_issue_matrix_score_ignores_non_table_prose() -> None:
    assert _issue_matrix_fill_score("# Heading\n\nplain prose, no rows\n") == 0


def _run_driver(
    tmp_path: Path,
    ours_text: str,
    theirs_text: str,
    *,
    filename: str,
    driver: object,
) -> str:
    base = tmp_path / f"base-{filename}"
    ours = tmp_path / f"ours-{filename}"
    theirs = tmp_path / f"theirs-{filename}"
    base.write_text("", encoding="utf-8")
    ours.write_text(ours_text, encoding="utf-8")
    theirs.write_text(theirs_text, encoding="utf-8")
    driver(str(base), str(ours), str(theirs))  # type: ignore[operator]
    return ours.read_text(encoding="utf-8")


def test_driver_keeps_target_fill_when_mission_branch_is_scaffold(tmp_path: Path) -> None:
    """The #2804 shape: accept filled the target, mission branch still scaffold."""
    result = _run_driver(
        tmp_path,
        json.dumps(_FILLED_MATRIX),
        json.dumps(_SCAFFOLD_MATRIX),
        filename="acceptance-matrix.json",
        driver=merge_driver_acceptance_matrix,
    )
    assert json.loads(result)["overall_verdict"] == "pass"


def test_driver_takes_mission_fill_when_target_is_scaffold(tmp_path: Path) -> None:
    """Reverse ordering: the fill was authored in a lane, target is still scaffold."""
    result = _run_driver(
        tmp_path,
        json.dumps(_SCAFFOLD_MATRIX),
        json.dumps(_FILLED_MATRIX),
        filename="acceptance-matrix.json",
        driver=merge_driver_acceptance_matrix,
    )
    assert json.loads(result)["overall_verdict"] == "pass"


def test_driver_resolves_equal_fill_to_target(tmp_path: Path) -> None:
    """Ties go to ``ours`` — the target, where accept happened."""
    ours = dict(_FILLED_MATRIX, mission_slug="target-side")
    theirs = dict(_FILLED_MATRIX, mission_slug="mission-side")
    result = _run_driver(
        tmp_path,
        json.dumps(ours),
        json.dumps(theirs),
        filename="acceptance-matrix.json",
        driver=merge_driver_acceptance_matrix,
    )
    assert json.loads(result)["mission_slug"] == "target-side"


def test_issue_matrix_driver_keeps_terminal_verdicts(tmp_path: Path) -> None:
    result = _run_driver(
        tmp_path,
        _FILLED_ISSUE_MATRIX,
        _SCAFFOLD_ISSUE_MATRIX,
        filename="issue-matrix.md",
        driver=merge_driver_issue_matrix,
    )
    assert "fixed" in result
    assert "unknown" not in result


def test_issue_matrix_driver_takes_mission_side_when_target_is_scaffold(tmp_path: Path) -> None:
    result = _run_driver(
        tmp_path,
        _SCAFFOLD_ISSUE_MATRIX,
        _FILLED_ISSUE_MATRIX,
        filename="issue-matrix.md",
        driver=merge_driver_issue_matrix,
    )
    assert "fixed" in result
