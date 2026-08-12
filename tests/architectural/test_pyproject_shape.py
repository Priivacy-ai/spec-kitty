"""Consumed packaging invariants for the published CLI distribution."""

from __future__ import annotations

import ast
import copy
import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_SRC = _REPO_ROOT / "src"
_SHARED_PACKAGES = ("spec-kitty-events", "spec-kitty-tracker")
_RETIRED_PACKAGE = "spec-kitty-runtime"
_SHIPPED_TREES = ("specify_cli", "runtime")
_DEP_NAME_TERMINATORS = "[=<>!~;@ "


def _load_pyproject() -> dict[str, Any]:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _dep_name(entry: str) -> str:
    for index, char in enumerate(entry):
        if char in _DEP_NAME_TERMINATORS:
            return entry[:index].strip()
    return entry.strip()


def _metadata_violations(data: dict[str, Any]) -> list[str]:
    dependencies = data.get("project", {}).get("dependencies", [])
    by_name = {_dep_name(entry): entry for entry in dependencies}
    failures: list[str] = []
    for package in _SHARED_PACKAGES:
        entry = by_name.get(package)
        if entry is None:
            failures.append(f"missing consumed dependency {package}")
        elif "==" in entry:
            failures.append(f"exact runtime pin for {package}: {entry}")
    if _RETIRED_PACKAGE in by_name:
        failures.append(f"retired dependency present: {by_name[_RETIRED_PACKAGE]}")

    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    for package in (*_SHARED_PACKAGES, _RETIRED_PACKAGE):
        if package in sources:
            failures.append(f"committed local source for {package}: {sources[package]!r}")
    return failures


def _imported_first_party_packages(src_root: Path) -> set[str]:
    first_party = {child.name for child in src_root.iterdir() if child.is_dir() and any(child.rglob("*.py"))}
    imported: set[str] = set()
    for shipped_tree in _SHIPPED_TREES:
        for path in (src_root / shipped_tree).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                imported.update(name.split(".", 1)[0] for name in names if name.split(".", 1)[0] in first_party)
    return imported


def _missing_wheel_packages(data: dict[str, Any], src_root: Path) -> set[str]:
    configured = {Path(path).name for path in data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]}
    return _imported_first_party_packages(src_root) - configured


def test_published_metadata_uses_consumable_shared_dependencies() -> None:
    """Published metadata must remain installable outside the checkout."""
    data = _load_pyproject()
    assert data["project"]["dependencies"]
    assert _metadata_violations(data) == []

    exact_pin = copy.deepcopy(data)
    exact_pin["project"]["dependencies"] = [
        "spec-kitty-events==6.1.0" if _dep_name(entry) == "spec-kitty-events" else entry for entry in exact_pin["project"]["dependencies"]
    ]
    assert _metadata_violations(exact_pin)

    local_source = copy.deepcopy(data)
    local_source.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})["spec-kitty-tracker"] = {"path": "../spec-kitty-tracker", "editable": True}
    assert _metadata_violations(local_source)


def test_wheel_contains_every_first_party_runtime_import() -> None:
    """A clean wheel must contain every first-party package shipped code imports."""
    data = _load_pyproject()
    imported = _imported_first_party_packages(_SRC)
    assert imported
    assert _missing_wheel_packages(data, _SRC) == set()

    omitted = copy.deepcopy(data)
    victim = sorted(imported)[0]
    packages = omitted["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    omitted["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] = [path for path in packages if Path(path).name != victim]
    assert _missing_wheel_packages(omitted, _SRC) == {victim}
