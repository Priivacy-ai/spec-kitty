"""Architectural guard: the pytest marker registry has a single source of truth.

Background (Priivacy-ai/spec-kitty#2034, workstream 2):
``pytest.ini`` and ``pyproject.toml [tool.pytest.ini_options]`` both used to
declare ``markers``. pytest reads exactly one configuration file, preferring
``pytest.ini`` over ``[tool.pytest.ini_options]`` when both exist — so the
``pyproject`` copy was dead config that never took effect and had silently
drifted ~10 markers out of sync with the live ``pytest.ini`` registry.

These tests pin ``pytest.ini`` as the single source of truth and fail if a
``[tool.pytest.ini_options]`` markers list is reintroduced into
``pyproject.toml``, so the duplication cannot silently come back.

Like the rest of ``tests/architectural/``, these are pure file-shape
assertions (parse two text files) and run in milliseconds.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
_PYTEST_INI_PATH = _REPO_ROOT / "pytest.ini"


def test_pytest_ini_exists_and_declares_markers() -> None:
    """The single source of truth must exist and carry a non-empty registry.

    If ``pytest.ini`` is renamed or loses its ``markers`` block, the
    duplication guard below would pass vacuously while the registry silently
    moved (or vanished); this guard prevents that.
    """
    assert _PYTEST_INI_PATH.is_file(), (
        f"pytest.ini not found at {_PYTEST_INI_PATH}. It is the single source "
        "of truth for the pytest marker registry (see #2034)."
    )
    text = _PYTEST_INI_PATH.read_text(encoding="utf-8")
    assert "markers =" in text, (
        "pytest.ini no longer declares a `markers =` block. It is the single "
        "source of truth for registered markers; restore the block here rather "
        "than moving markers into pyproject.toml."
    )


def test_pyproject_does_not_redeclare_pytest_markers() -> None:
    """``pyproject.toml`` must NOT carry a ``[tool.pytest.ini_options].markers``.

    Because ``pytest.ini`` wins when both files are present, any markers
    declared here are dead config that drifts from the live registry. Keep the
    registry in ``pytest.ini`` only.
    """
    data = tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))
    ini_options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert "markers" not in ini_options, (
        "pyproject.toml reintroduced [tool.pytest.ini_options].markers. pytest "
        "reads only pytest.ini when present, so these markers are dead config "
        "that silently drifts from the live registry (the regression #2034 "
        "fixed). Declare markers in pytest.ini instead — it is the single "
        "source of truth."
    )
