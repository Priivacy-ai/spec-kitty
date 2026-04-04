"""Scope: mock-boundary tests for doctrine catalog loading — no real git."""

import pytest
from charter.catalog import load_doctrine_catalog

pytestmark = pytest.mark.fast


def test_catalog_loads_packaged_directives_and_paradigms() -> None:
    """Packaged catalog contains expected directives and paradigms."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    catalog = load_doctrine_catalog()

    # Assert — shipped directives use DIRECTIVE_NNN identifiers
    assert "DIRECTIVE_003" in catalog.directives  # decision-documentation-requirement


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
