"""Tests for the multi-path structural-move extension (IC-10, #1815).

Covers C-OMAP-1 backward compatibility (a legacy single-term map validates
and gates exactly as before) and the new optional ``moves:`` block (parse,
validate, gate, and review-time diff exemption).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from specify_cli.bulk_edit.diff_check import assess_file, check_diff_compliance
from specify_cli.bulk_edit.occurrence_map import (
    MoveEntry,
    OccurrenceMap,
    check_admissibility,
    load_occurrence_map,
    validate_against_schema,
    validate_occurrence_map,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


ALL_EIGHT_CATEGORIES = {
    "code_symbols": {"action": "rename"},
    "import_paths": {"action": "rename"},
    "filesystem_paths": {"action": "manual_review"},
    "serialized_keys": {"action": "do_not_change"},
    "cli_commands": {"action": "do_not_change"},
    "user_facing_strings": {"action": "rename_if_user_visible"},
    "tests_fixtures": {"action": "rename"},
    "logs_telemetry": {"action": "do_not_change"},
}


def _legacy_map_data() -> dict[str, Any]:
    """A complete, valid single-term map with NO moves block."""
    return {
        "target": {
            "term": "constitution",
            "replacement": "charter",
            "operation": "rename",
        },
        "categories": copy.deepcopy(ALL_EIGHT_CATEGORIES),
        "exceptions": [],
    }


def _write(feature_dir: Path, content: dict[str, Any]) -> Path:
    yaml = YAML()
    path = feature_dir / "occurrence_map.yaml"
    with open(path, "w") as f:
        yaml.dump(content, f)
    return path


# ---------------------------------------------------------------------------
# C-OMAP-1 — legacy maps validate EXACTLY as before
# ---------------------------------------------------------------------------


class TestLegacyBackwardCompat:
    def test_legacy_map_has_empty_moves(self, tmp_path: Path) -> None:
        _write(tmp_path, _legacy_map_data())
        omap = load_occurrence_map(tmp_path)
        assert omap is not None
        assert omap.moves == []

    def test_legacy_map_structural_validation_unchanged(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, _legacy_map_data())
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)

        assert result.valid is True
        assert result.errors == []
        # No spurious warning about a missing moves block.
        assert not any("moves" in w for w in result.warnings)

    def test_legacy_map_admissibility_unchanged(self, tmp_path: Path) -> None:
        _write(tmp_path, _legacy_map_data())
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = check_admissibility(omap)

        assert result.valid is True
        assert result.errors == []

    def test_legacy_map_passes_schema(self) -> None:
        result = validate_against_schema(_legacy_map_data())
        assert result.valid, result.errors

    def test_null_moves_is_treated_as_legacy(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = None
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None
        assert omap.moves == []
        assert validate_occurrence_map(omap).valid is True


# ---------------------------------------------------------------------------
# moves: block — parse, validate, gate
# ---------------------------------------------------------------------------


class TestMovesParsing:
    def test_moves_block_parsed_into_entries(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = [
            {
                "from": ["src/legacy/auth/login.py", "src/legacy/auth/session.py"],
                "to": "src/auth",
                "reason": "Consolidate auth modules",
            },
            {"from": ["docs/old.md"], "to": "docs/new.md"},
        ]
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        assert len(omap.moves) == 2
        first = omap.moves[0]
        assert isinstance(first, MoveEntry)
        assert first.sources == [
            "src/legacy/auth/login.py",
            "src/legacy/auth/session.py",
        ]
        assert first.destination == "src/auth"
        assert first.reason == "Consolidate auth modules"
        assert omap.moves[1].reason is None


class TestMovesValidation:
    def test_valid_moves_block_validates_and_gates(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = [
            {"from": ["src/legacy/a.py"], "to": "src/new/a.py"},
        ]
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        assert validate_occurrence_map(omap).valid is True
        assert check_admissibility(omap).valid is True
        assert validate_against_schema(data).valid is True

    def test_move_missing_to_is_rejected(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = [{"from": ["src/a.py"]}]
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)
        assert result.valid is False
        assert any("to" in e and "moves[0]" in e for e in result.errors)

    def test_move_empty_from_is_rejected(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = [{"from": [], "to": "src/new.py"}]
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)
        assert result.valid is False
        assert any("from" in e and "moves[0]" in e for e in result.errors)

    def test_moves_not_a_list_is_rejected(self, tmp_path: Path) -> None:
        data = _legacy_map_data()
        data["moves"] = {"from": ["a"], "to": "b"}
        _write(tmp_path, data)
        omap = load_occurrence_map(tmp_path)
        assert omap is not None

        result = validate_occurrence_map(omap)
        assert result.valid is False
        assert any("moves" in e and "list" in e for e in result.errors)

    def test_schema_rejects_move_without_to(self) -> None:
        data = _legacy_map_data()
        data["moves"] = [{"from": ["src/a.py"]}]
        result = validate_against_schema(data)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Review-time diff exemption for declared moves
# ---------------------------------------------------------------------------


def _map_with_moves(moves: list[MoveEntry]) -> OccurrenceMap:
    raw = {
        "target": {"term": "oldName", "operation": "rename"},
        "categories": copy.deepcopy(ALL_EIGHT_CATEGORIES),
        "exceptions": [],
        "moves": [
            {"from": m.sources, "to": m.destination, **({"reason": m.reason} if m.reason else {})}
            for m in moves
        ],
    }
    return OccurrenceMap(
        target_term="oldName",
        target_replacement=None,
        target_operation="rename",
        categories=copy.deepcopy(ALL_EIGHT_CATEGORIES),
        exceptions=[],
        status=None,
        raw=raw,
        moves=moves,
    )


class TestMoveDiffExemption:
    def test_move_source_exempt_from_do_not_change(self) -> None:
        # logs_telemetry is do_not_change; a .yaml normally classifies as
        # serialized_keys (also do_not_change). Declaring the path as a move
        # source must exempt it.
        omap = _map_with_moves(
            [MoveEntry(sources=["config/old.yaml"], destination="config/new.yaml")]
        )
        a = assess_file("config/old.yaml", omap)
        assert a.violation is False
        assert a.source == "move"

    def test_move_destination_exempt(self) -> None:
        omap = _map_with_moves(
            [MoveEntry(sources=["config/old.yaml"], destination="config/new.yaml")]
        )
        a = assess_file("config/new.yaml", omap)
        assert a.violation is False
        assert a.source == "move"

    def test_directory_prefix_destination_covers_children(self) -> None:
        omap = _map_with_moves(
            [MoveEntry(sources=["src/legacy/auth"], destination="src/auth")]
        )
        a = assess_file("src/auth/login.py", omap)
        assert a.violation is False
        assert a.source == "move"

    def test_glob_source_matches(self) -> None:
        omap = _map_with_moves(
            [MoveEntry(sources=["src/legacy/**/*.py"], destination="src/new")]
        )
        a = assess_file("src/legacy/auth/login.py", omap)
        assert a.violation is False
        assert a.source == "move"

    def test_non_move_do_not_change_still_blocks(self) -> None:
        # A serialized_keys file NOT covered by any move still blocks.
        omap = _map_with_moves(
            [MoveEntry(sources=["config/old.yaml"], destination="config/new.yaml")]
        )
        a = assess_file("config/unrelated.yaml", omap)
        assert a.violation is True

    def test_check_diff_compliance_passes_with_moves(self) -> None:
        omap = _map_with_moves(
            [MoveEntry(sources=["config/old.yaml"], destination="config/new.yaml")]
        )
        result = check_diff_compliance(
            ["config/old.yaml", "config/new.yaml"], omap
        )
        assert result.passed is True
