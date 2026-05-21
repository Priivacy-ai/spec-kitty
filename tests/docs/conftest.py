"""Shared fixtures for ``tests/docs``.

The leakage-check CLI resolves markdown link targets and inventory paths
against the current working directory. The fixtures here stage a fresh
``docs/`` tree (plus an inventory YAML) inside ``tmp_path`` and yield
that staging directory so tests can run the script with ``cwd=staging``.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make ``scripts.docs`` importable. The repository's ``pytest.ini`` only adds
# ``src`` to ``pythonpath`` to avoid double-import problems, so we extend the
# path explicitly here for the tooling under ``scripts/``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PAGES_DIR = FIXTURES_DIR / "sample_pages"


@pytest.fixture()
def clean_workspace(tmp_path: Path) -> Iterator[Path]:
    """Stage the clean sample tree + inventory in ``tmp_path``."""
    workspace = tmp_path / "clean"
    shutil.copytree(SAMPLE_PAGES_DIR / "clean", workspace)
    shutil.copy(FIXTURES_DIR / "clean_inventory.yaml", workspace / "inventory.yaml")
    yield workspace


@pytest.fixture()
def dirty_workspace(tmp_path: Path) -> Iterator[Path]:
    """Stage the dirty sample tree + inventory in ``tmp_path``."""
    workspace = tmp_path / "dirty"
    shutil.copytree(SAMPLE_PAGES_DIR / "dirty", workspace)
    shutil.copy(FIXTURES_DIR / "dirty_inventory.yaml", workspace / "inventory.yaml")
    yield workspace


@pytest.fixture()
def missing_workspace(tmp_path: Path) -> Iterator[Path]:
    """Stage a minimal docs tree + malformed inventory in ``tmp_path``."""
    workspace = tmp_path / "missing"
    workspace.mkdir()
    (workspace / "docs").mkdir()
    shutil.copy(
        FIXTURES_DIR / "missing_inventory.yaml", workspace / "inventory.yaml"
    )
    yield workspace
