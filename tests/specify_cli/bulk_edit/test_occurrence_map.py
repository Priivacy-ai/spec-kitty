"""Tests for the bulk_edit occurrence map schema, validation, and admissibility."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.bulk_edit.occurrence_map import (
    OccurrenceMap,
    check_admissibility,
    load_occurrence_map,
    validate_occurrence_map,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_EIGHT_CATEGORIES = {
    "code_symbols": {"action": "rename"},
    "import_paths": {"action": "rename"},
    "filesystem_paths": {"action": "rename"},
    "serialized_keys": {"action": "do_not_change"},
    "cli_commands": {"action": "rename_if_user_visible"},
    "user_facing_strings": {"action": "rename_if_user_visible"},
    "tests_fixtures": {"action": "rename"},
    "logs_telemetry": {"action": "manual_review"},
}


def _valid_map_data() -> dict:
    """Return a complete, valid occurrence map dict."""
    return {
        "target": {
            "term": "constitution",
            "replacement": "charter",
            "operation": "rename",
        },
        "categories": copy.deepcopy(ALL_EIGHT_CATEGORIES),
        "exceptions": [],
    }


def write_occurrence_map(feature_dir: Path, content: dict) -> Path:
    yaml = YAML()
    path = feature_dir / "occurrence_map.yaml"
    with open(path, "w") as f:
        yaml.dump(content, f)
    return path


# ---------------------------------------------------------------------------
# load_occurrence_map
# ---------------------------------------------------------------------------


class TestLoadOccurrenceMap:
    def test_load_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert load_occurrence_map(tmp_path) is None

    def test_load_valid_yaml_returns_occurrence_map(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        write_occurrence_map(tmp_path, data)

        omap = load_occurrence_map(tmp_path)

        assert omap is not None
        assert isinstance(omap, OccurrenceMap)
        assert omap.target_term == "constitution"
        assert omap.target_replacement == "charter"
        assert omap.target_operation == "rename"
        assert len(omap.categories) == 8
        assert omap.exceptions == []
        assert omap.status is None
        assert omap.raw == data


# ---------------------------------------------------------------------------
# validate_occurrence_map
# ---------------------------------------------------------------------------


class TestValidateOccurrenceMap:
    def test_valid_complete_map_passes(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is True
        assert result.errors == []

    def test_missing_target_section_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        del data["target"]
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("target" in e.lower() for e in result.errors)

    def test_missing_target_term_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        del data["target"]["term"]
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("target.term" in e for e in result.errors)

    def test_empty_target_term_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["target"]["term"] = ""
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("non-empty" in e for e in result.errors)

    def test_invalid_target_operation_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["target"]["operation"] = "destroy"
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("operation" in e and "destroy" in e for e in result.errors)

    def test_missing_categories_section_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        del data["categories"]
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("categories" in e.lower() for e in result.errors)

    def test_empty_categories_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["categories"] = {}
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("non-empty" in e for e in result.errors)

    def test_category_missing_action_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["categories"]["code_symbols"] = {"description": "no action here"}
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("code_symbols" in e and "action" in e for e in result.errors)

    def test_category_invalid_action_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["categories"]["code_symbols"]["action"] = "nuke"
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is False
        assert any("code_symbols" in e and "nuke" in e for e in result.errors)

    def test_unknown_top_level_keys_warn(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["bonus_section"] = {"foo": "bar"}
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is True
        assert any("bonus_section" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# check_admissibility
# ---------------------------------------------------------------------------


class TestCheckAdmissibility:
    def test_admissible_map_passes(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is True
        assert result.errors == []

    @pytest.mark.parametrize("placeholder", ["TODO", "TBD"])
    def test_placeholder_term_fails(self, tmp_path: Path, placeholder: str) -> None:
        data = _valid_map_data()
        data["target"]["term"] = placeholder
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is False
        assert any("placeholder" in e for e in result.errors)

    def test_fewer_than_3_categories_fails(self, tmp_path: Path) -> None:
        data = _valid_map_data()
        data["categories"] = {
            "code_symbols": {"action": "rename"},
            "import_paths": {"action": "rename"},
        }
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is False
        assert any("3" in e for e in result.errors)

    def test_exactly_3_categories_fails_missing_standards(self, tmp_path: Path) -> None:
        """With only 3 categories, admissibility fails because the other 5
        standard categories (FR-004) are missing."""
        data = _valid_map_data()
        data["categories"] = {
            "code_symbols": {"action": "rename"},
            "import_paths": {"action": "rename"},
            "filesystem_paths": {"action": "rename"},
        }
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        # Min-category rule still passes (3 >= 3) but FR-004 fails
        assert result.valid is False
        assert any("standard categories" in e.lower() for e in result.errors)

    def test_all_8_standard_categories_passes(self, tmp_path: Path) -> None:
        """Admissibility accepts a map that classifies every standard category."""
        # _valid_map_data() already classifies all 8 standards (ALL_EIGHT_CATEGORIES).
        data = _valid_map_data()
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is True
        assert result.errors == []

    def test_missing_one_standard_category_fails(self, tmp_path: Path) -> None:
        """Omitting even one of the 8 standard categories blocks admissibility."""
        data = _valid_map_data()
        # Drop logs_telemetry — a high-risk surface that must be classified.
        del data["categories"]["logs_telemetry"]
        write_occurrence_map(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is False
        assert any("logs_telemetry" in e and "standard" in e.lower() for e in result.errors)
