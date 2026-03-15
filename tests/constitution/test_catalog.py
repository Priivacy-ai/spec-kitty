"""Scope: mock-boundary tests for doctrine catalog loading — no real git."""

import pytest
from specify_cli.constitution.catalog import load_doctrine_catalog

pytestmark = pytest.mark.fast


def test_catalog_loads_packaged_directives_and_paradigms() -> None:
    """Packaged catalog contains expected directives and paradigms."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    catalog = load_doctrine_catalog()

    # Assert
    assert "TEST_FIRST" in catalog.directives
    assert "test-first" in catalog.paradigms


def test_catalog_includes_mission_template_sets() -> None:
    """Packaged catalog includes the default software-dev template set."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    catalog = load_doctrine_catalog()

    # Assert
    assert "software-dev-default" in catalog.template_sets
