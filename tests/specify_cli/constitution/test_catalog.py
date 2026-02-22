"""Tests for doctrine catalog loading."""

from specify_cli.constitution.catalog import load_doctrine_catalog


def test_catalog_loads_packaged_directives_and_paradigms() -> None:
    catalog = load_doctrine_catalog()
    assert "TEST_FIRST" in catalog.directives
    assert "test-first" in catalog.paradigms


def test_catalog_includes_mission_template_sets() -> None:
    catalog = load_doctrine_catalog()
    assert "software-dev-default" in catalog.template_sets
