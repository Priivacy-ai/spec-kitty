"""Shared fixtures for DRG test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture()
def valid_graph_path() -> Path:
    return FIXTURES_DIR / "valid_graph.yaml"


@pytest.fixture()
def dangling_ref_graph_path() -> Path:
    return FIXTURES_DIR / "dangling_ref_graph.yaml"


@pytest.fixture()
def cyclic_requires_graph_path() -> Path:
    return FIXTURES_DIR / "cyclic_requires_graph.yaml"


@pytest.fixture()
def duplicate_edge_graph_path() -> Path:
    return FIXTURES_DIR / "duplicate_edge_graph.yaml"


@pytest.fixture()
def empty_graph_path() -> Path:
    return FIXTURES_DIR / "empty_graph.yaml"
