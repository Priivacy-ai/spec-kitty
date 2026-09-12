"""Structural regression tests for shared Zeitgeist test fixtures."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


def _is_pytest_fixture(node: ast.stmt) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            decorator = decorator.func
        if isinstance(decorator, ast.Attribute) and decorator.attr == "fixture":
            return True
        if isinstance(decorator, ast.Name) and decorator.id == "fixture":
            return True
    return False


def _fixture_definition_paths(package: Path, fixture_name: str) -> list[str]:
    definitions = []
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        definitions.extend(path.relative_to(package).as_posix() for node in ast.walk(tree) if _is_pytest_fixture(node) and node.name == fixture_name)
    return definitions


def test_ancestor_boundary_fixture_is_defined_only_in_conftest() -> None:
    package = Path(__file__).parent
    assert _fixture_definition_paths(package, "no_git_ancestry_inside_tmp_path") == ["conftest.py"]


def test_fixture_definition_scan_covers_decorator_forms_and_nested_files(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef example(): ...\n",
        encoding="utf-8",
    )
    (nested / "test_example.py").write_text(
        "from pytest import fixture\n\nclass TestExample:\n    @fixture(scope='function')\n    def example(self): ...\n",
        encoding="utf-8",
    )

    assert _fixture_definition_paths(tmp_path, "example") == [
        "conftest.py",
        "nested/test_example.py",
    ]
