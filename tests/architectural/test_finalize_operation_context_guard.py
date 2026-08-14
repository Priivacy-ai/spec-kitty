"""Architectural guard for the finalize-tasks operation-context seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural


FINALIZE_MODULE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "specify_cli"
    / "cli"
    / "commands"
    / "agent"
    / "mission_finalize.py"
)


def _finalize_function() -> ast.FunctionDef:
    tree = ast.parse(FINALIZE_MODULE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "finalize_tasks"
    )
    assert isinstance(function, ast.FunctionDef)
    return function


def _has_operation_context_call(function: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_resolve_mission_operation_context"
        for node in ast.walk(function)
    )


def _has_anchor_bound_placement_call(function: ast.FunctionDef) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "placement_seam"):
            continue
        for keyword in node.keywords:
            if keyword.arg != "effective_root":
                continue
            return isinstance(keyword.value, ast.Name) and keyword.value.id == "mission_anchor_root"
    return False


def test_finalize_tasks_is_bound_to_shared_operation_context() -> None:
    """The command must resolve identity before selecting its planning surface."""
    function = _finalize_function()

    assert _has_operation_context_call(function), (
        "finalize_tasks must resolve MissionOperationContext before reading mission artifacts"
    )
    assert _has_anchor_bound_placement_call(function), (
        "finalize_tasks must pass mission_anchor_root into placement_seam"
    )


def test_guard_is_non_vacuous() -> None:
    """A legacy direct seam call is rejected by the same structural predicate."""
    legacy_tree = ast.parse(
        """
def finalize_tasks():
    placement_seam(repo_root, mission_slug)
"""
    )
    legacy_function = legacy_tree.body[0]
    assert isinstance(legacy_function, ast.FunctionDef)
    assert not _has_anchor_bound_placement_call(legacy_function)
