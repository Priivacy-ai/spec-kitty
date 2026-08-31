"""Structural regression tests for shared Zeitgeist test fixtures."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


def _is_pytest_fixture(node: ast.stmt) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return any(
        isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "fixture" for decorator in node.decorator_list
    )


def test_ancestor_boundary_fixture_is_defined_only_in_conftest() -> None:
    package = Path(__file__).parent
    definitions = [
        path.relative_to(package).as_posix()
        for path in sorted(package.glob("*.py"))
        for node in ast.parse(path.read_text(encoding="utf-8"), filename=str(path)).body
        if _is_pytest_fixture(node) and node.name == "no_git_ancestry_inside_tmp_path"
    ]

    assert definitions == ["conftest.py"]
