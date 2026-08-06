"""WP03 row 12: ``_resolve_planning_branch.load_mission_target_branch`` fail-closed.

Census row 12 routes
``specify_cli.missions._resolve_planning_branch.load_mission_target_branch``
onto :func:`specify_cli.core.paths.load_meta_fail_closed`.

This is the one site where the ``if data is None:`` arm ALREADY exists — but it
is dead-by-comment (``# Unreachable``) and carries the wrong cause ("is not a
JSON object").  Routing makes it the live absent-file arm, so it must carry the
missing-file message AND the ``--target-branch`` remediation that the
``FileNotFoundError`` arm carried and this arm did not.

The remediation substring is the assertion the pre-existing arm cannot satisfy.
It is asserted explicitly here, because every arm in this function raises
``PlanningBranchResolutionFailed`` — a type-only guard is green at baseline,
after routing, and under arm-deletion.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.missions._resolve_planning_branch import (
    PlanningBranchResolutionFailed,
    load_mission_target_branch,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MODULE_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "specify_cli"
    / "missions"
    / "_resolve_planning_branch.py"
)

_REMEDIATION = "Re-run with --target-branch <ref> to override."


def _mission_dir(tmp_path: Path, *, meta_text: str | None) -> Path:
    """Materialize a mission directory; ``meta_text=None`` leaves meta.json absent."""
    mission_dir = tmp_path / "kitty-specs" / "test-mission"
    mission_dir.mkdir(parents=True, exist_ok=True)
    if meta_text is not None:
        (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    return mission_dir


class TestRow12PlanningBranchFailClosed:
    """Behavioural contract of the routed ``load_mission_target_branch`` site."""

    def test_absent_meta_json_names_the_missing_file(self, tmp_path: Path) -> None:
        """The live absent-file arm reports the MISSING-FILE cause."""
        mission_dir = _mission_dir(tmp_path, meta_text=None)

        with pytest.raises(PlanningBranchResolutionFailed) as excinfo:
            load_mission_target_branch(mission_dir)

        assert "meta.json not found at" in str(excinfo.value), (
            f"absent meta.json reported the wrong cause: {excinfo.value}"
        )

    def test_absent_meta_json_keeps_the_target_branch_remediation(self, tmp_path: Path) -> None:
        """The remediation must survive the dead-arm removal (SC-015).

        This is the assertion the pre-existing ``if data is None:`` arm ("is not
        a JSON object") CANNOT satisfy — it is the reason the arm is re-purposed
        rather than left alone, and it is what T017's mutation probe breaks.
        """
        mission_dir = _mission_dir(tmp_path, meta_text=None)

        with pytest.raises(PlanningBranchResolutionFailed) as excinfo:
            load_mission_target_branch(mission_dir)

        assert _REMEDIATION in str(excinfo.value), (
            "the --target-branch remediation was lost when the FileNotFoundError "
            f"arm was removed; got: {excinfo.value}"
        )

    def test_absent_meta_json_is_not_reported_as_a_non_object(self, tmp_path: Path) -> None:
        """Absence must not be reported with the retired 'not a JSON object' cause."""
        mission_dir = _mission_dir(tmp_path, meta_text=None)

        with pytest.raises(PlanningBranchResolutionFailed) as excinfo:
            load_mission_target_branch(mission_dir)

        assert "is not a JSON object" not in str(excinfo.value)

    def test_malformed_meta_json_stays_a_planning_branch_failure(self, tmp_path: Path) -> None:
        """C-002 / coupling 4: the handler must catch the ROUTED exception type.

        ``MissionMetaReadError`` is a ``RuntimeError``; an un-widened
        ``except ValueError`` lets it leak past the contracted refusal.
        """
        mission_dir = _mission_dir(tmp_path, meta_text="{ not valid json")

        with pytest.raises(PlanningBranchResolutionFailed) as excinfo:
            load_mission_target_branch(mission_dir)

        assert "is unreadable" in str(excinfo.value)
        assert _REMEDIATION in str(excinfo.value)

    def test_valid_meta_json_resolves_cleanly(self, tmp_path: Path) -> None:
        """SC-003 negative control: a valid read must not fail closed."""
        mission_dir = _mission_dir(
            tmp_path, meta_text=json.dumps({"target_branch": "feat/some-branch"})
        )

        assert load_mission_target_branch(mission_dir) == "feat/some-branch"


class TestRow12HandlerShape:
    """C-002: catch ``MissionMetaReadError`` by name, never a bare Exception."""

    def test_handler_names_mission_meta_read_error(self) -> None:
        tree = ast.parse(_MODULE_SOURCE.read_text(encoding="utf-8"))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "load_mission_target_branch"
        )

        caught: list[str] = []
        for handler in (h for n in ast.walk(target) if isinstance(n, ast.Try) for h in n.handlers):
            assert handler.type is not None, "bare except in load_mission_target_branch"
            nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
            caught.extend(n.id for n in nodes if isinstance(n, ast.Name))

        assert "MissionMetaReadError" in caught, (
            "specify_cli.missions._resolve_planning_branch.load_mission_target_branch "
            f"must catch MissionMetaReadError by name; caught {caught}"
        )
        assert "Exception" not in caught
        assert "BaseException" not in caught

    def test_no_unreachable_comment_survives_in_the_routed_function(self) -> None:
        """The ``# Unreachable`` comment must go — the arm is now live."""
        source = _MODULE_SOURCE.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "load_mission_target_branch"
        )
        body = source[target.lineno - 1 : (target.end_lineno or target.lineno)]

        assert not [line for line in body if "Unreachable" in line], (
            "load_mission_target_branch still documents its None arm as unreachable; "
            "after routing it is the live absent-file arm"
        )


class TestRow12RoutedCallBudget:
    """Structural budget: exactly one routed call, matched on the exact callee."""

    def test_load_mission_target_branch_body_has_one_fail_closed_call(self) -> None:
        """1 ``load_meta_fail_closed``, 0 ``load_meta``, matched on exact callee name."""
        tree = ast.parse(_MODULE_SOURCE.read_text(encoding="utf-8"))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "load_mission_target_branch"
        )

        callee_names = [
            node.func.id
            for node in ast.walk(target)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]

        assert callee_names.count("load_meta_fail_closed") == 1, (
            "specify_cli.missions._resolve_planning_branch.load_mission_target_branch "
            "must contain exactly one load_meta_fail_closed() call; found "
            f"{callee_names.count('load_meta_fail_closed')}"
        )
        assert callee_names.count("load_meta") == 0, (
            "specify_cli.missions._resolve_planning_branch.load_mission_target_branch "
            f"must contain zero load_meta() calls; found {callee_names.count('load_meta')}"
        )
