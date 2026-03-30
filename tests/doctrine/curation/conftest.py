"""Fixtures for curation engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML


@pytest.fixture()
def doctrine_root(tmp_path: Path) -> Path:
    """Create a minimal doctrine root with _proposed/ and shipped/ dirs."""
    yaml = YAML()
    yaml.default_flow_style = False

    # Directives
    proposed = tmp_path / "directives" / "_proposed"
    proposed.mkdir(parents=True)
    shipped = tmp_path / "directives" / "shipped"
    shipped.mkdir(parents=True)

    with (proposed / "001-test.directive.yaml").open("w") as f:
        yaml.dump(
            {
                "schema_version": "1.0",
                "id": "DIRECTIVE_001",
                "title": "Test Directive",
                "intent": "Test intent.",
                "enforcement": "required",
            },
            f,
        )

    with (proposed / "002-another.directive.yaml").open("w") as f:
        yaml.dump(
            {
                "schema_version": "1.0",
                "id": "DIRECTIVE_002",
                "title": "Another Directive",
                "intent": "Another intent.",
                "enforcement": "advisory",
            },
            f,
        )

    # Tactics
    t_proposed = tmp_path / "tactics" / "_proposed"
    t_proposed.mkdir(parents=True)
    (tmp_path / "tactics" / "shipped").mkdir(parents=True)

    with (t_proposed / "test-tactic.tactic.yaml").open("w") as f:
        yaml.dump(
            {
                "schema_version": "1.0",
                "id": "test-tactic",
                "name": "Test Tactic",
                "steps": [{"title": "Step 1"}],
            },
            f,
        )

    # Styleguides (empty proposed + shipped)
    (tmp_path / "styleguides" / "_proposed").mkdir(parents=True)
    (tmp_path / "styleguides" / "shipped").mkdir(parents=True)

    # Toolguides
    (tmp_path / "toolguides" / "_proposed").mkdir(parents=True)
    (tmp_path / "toolguides" / "shipped").mkdir(parents=True)

    # Paradigms
    (tmp_path / "paradigms" / "_proposed").mkdir(parents=True)
    (tmp_path / "paradigms" / "shipped").mkdir(parents=True)

    return tmp_path
