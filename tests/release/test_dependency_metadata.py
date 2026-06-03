from __future__ import annotations

from pathlib import Path
import tomllib

from packaging.requirements import Requirement


REPO_ROOT = Path(__file__).resolve().parents[2]


def _project_dependencies() -> dict[str, Requirement]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    return {
        requirement.name: requirement
        for requirement in (
            Requirement(value) for value in pyproject["project"]["dependencies"]
        )
    }


def test_click_is_declared_as_direct_runtime_dependency() -> None:
    dependencies = _project_dependencies()

    assert "click" in dependencies
    assert ">=8.2.1" in str(dependencies["click"].specifier)


def test_typer_is_capped_below_click_vendoring_release() -> None:
    dependencies = _project_dependencies()

    assert "typer" in dependencies
    specifier = str(dependencies["typer"].specifier)
    assert ">=0.24.1" in specifier
    assert "<0.26" in specifier
