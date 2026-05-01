"""Tests for the occurrence-map JSON Schema + starter template resources.

These tests pin the invariants the reviewer asked for on PR #616:
the schema is stored explicitly under ``src/doctrine/schemas/``, the starter
template is stored under ``src/doctrine/templates/``, and both are loaded
through a Python API so the SKILL file cannot drift out of sync with what
the runtime actually enforces.
"""

from __future__ import annotations

import yaml

from specify_cli.bulk_edit.occurrence_map import (
    STANDARD_CATEGORIES,
    VALID_ACTIONS,
    VALID_OPERATIONS,
    load_schema,
    load_template_text,
    template_path,
    validate_against_schema,
)


class TestSchemaResource:
    def test_schema_loads_and_has_metadata(self) -> None:
        schema = load_schema()
        assert schema.get("$schema", "").startswith("https://json-schema.org/draft/2020-12/")
        assert schema["title"] == "OccurrenceMap"
        assert schema["type"] == "object"

    def test_schema_action_enum_matches_constants(self) -> None:
        actions = set(load_schema()["definitions"]["action"]["enum"])
        assert actions == set(VALID_ACTIONS)

    def test_schema_operation_enum_matches_constants(self) -> None:
        ops = set(load_schema()["definitions"]["operation"]["enum"])
        assert ops == set(VALID_OPERATIONS)

    def test_schema_standard_categories_match_constants(self) -> None:
        cats = set(load_schema()["definitions"]["standard_category"]["enum"])
        assert cats == set(STANDARD_CATEGORIES)


class TestTemplateResource:
    def test_template_path_exists(self) -> None:
        assert template_path().is_file()

    def test_template_is_valid_yaml(self) -> None:
        data = yaml.safe_load(load_template_text())
        assert isinstance(data, dict)
        assert "target" in data
        assert "categories" in data

    def test_template_validates_against_schema(self) -> None:
        data = yaml.safe_load(load_template_text())
        result = validate_against_schema(data)
        assert result.valid, result.errors

    def test_template_classifies_every_standard_category(self) -> None:
        data = yaml.safe_load(load_template_text())
        assert set(data["categories"].keys()) == set(STANDARD_CATEGORIES)


class TestValidateAgainstSchema:
    def test_rejects_invalid_action(self) -> None:
        data = {
            "target": {"term": "x", "operation": "rename"},
            "categories": {"code_symbols": {"action": "nuke"}},
        }
        result = validate_against_schema(data)
        assert not result.valid
        assert any("nuke" in e or "enum" in e for e in result.errors)

    def test_rejects_missing_target(self) -> None:
        data = {"categories": {"code_symbols": {"action": "rename"}}}
        result = validate_against_schema(data)
        assert not result.valid

    def test_accepts_minimal_valid_map(self) -> None:
        data = {
            "target": {"term": "x"},
            "categories": {"code_symbols": {"action": "rename"}},
        }
        result = validate_against_schema(data)
        assert result.valid, result.errors
