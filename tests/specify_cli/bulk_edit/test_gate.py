"""Unit tests for the bulk edit occurrence classification gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.bulk_edit.gate import GateResult, ensure_occurrence_classification_ready


def _write_meta(feature_dir: Path, meta: dict) -> None:
    """Helper to write a meta.json file."""
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _write_occurrence_map(feature_dir: Path, content: str) -> None:
    """Helper to write an occurrence_map.yaml file."""
    omap_path = feature_dir / "occurrence_map.yaml"
    omap_path.write_text(content, encoding="utf-8")


VALID_OCCURRENCE_MAP = """\
target:
  term: oldName
  replacement: newName
  operation: rename
categories:
  code_symbols:
    action: rename
  import_paths:
    action: rename
  filesystem_paths:
    action: manual_review
  serialized_keys:
    action: do_not_change
  cli_commands:
    action: do_not_change
  user_facing_strings:
    action: rename_if_user_visible
  tests_fixtures:
    action: rename
  logs_telemetry:
    action: do_not_change
"""

INVALID_OCCURRENCE_MAP_MISSING_TARGET = """\
categories:
  code_symbols:
    action: rename
"""

# Map that passes validation and has >= 3 categories, but is missing
# several of the 8 standard categories — fails FR-004 admissibility.
INADMISSIBLE_OCCURRENCE_MAP_FEW_CATEGORIES = """\
target:
  term: oldName
  replacement: newName
  operation: rename
categories:
  code_symbols:
    action: rename
  import_paths:
    action: rename
"""


class TestGatePassesNonBulkEdit:
    """Gate should pass for missions that are not bulk_edit."""

    def test_no_change_mode_in_meta(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01"})
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is True
        assert result.change_mode is None
        assert result.errors == []

    def test_different_change_mode(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01", "change_mode": "standard"})
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is True
        assert result.change_mode == "standard"


class TestGatePassesNoMeta:
    """Gate should pass when there is no meta.json at all."""

    def test_missing_meta_json(self, tmp_path: Path) -> None:
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is True
        assert result.change_mode is None
        assert result.errors == []


class TestGateBlocksBulkEditNoMap:
    """Gate should block when change_mode=bulk_edit but no occurrence_map.yaml exists."""

    def test_blocks_with_error(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01", "change_mode": "bulk_edit"})
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is False
        assert result.change_mode == "bulk_edit"
        assert len(result.errors) == 1
        assert "Occurrence map required" in result.errors[0]
        assert "occurrence_map.yaml" in result.errors[0]


class TestGateBlocksBulkEditInvalidMap:
    """Gate should block when occurrence_map.yaml has structural validation errors."""

    def test_blocks_missing_target(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01", "change_mode": "bulk_edit"})
        _write_occurrence_map(tmp_path, INVALID_OCCURRENCE_MAP_MISSING_TARGET)
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is False
        assert result.change_mode == "bulk_edit"
        assert any("target" in e.lower() for e in result.errors)


class TestGateBlocksBulkEditInadmissible:
    """Gate should block when occurrence_map is structurally valid but has <3 categories."""

    def test_blocks_too_few_categories(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01", "change_mode": "bulk_edit"})
        _write_occurrence_map(tmp_path, INADMISSIBLE_OCCURRENCE_MAP_FEW_CATEGORIES)
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is False
        assert result.change_mode == "bulk_edit"
        assert any("at least" in e.lower() or "categories" in e.lower() for e in result.errors)


class TestGatePassesBulkEditValidMap:
    """Gate should pass when change_mode=bulk_edit and a valid, admissible map exists."""

    def test_passes_valid_map(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {"slug": "my-feature", "mission_slug": "my-feature", "friendly_name": "Test", "mission_type": "software-dev", "target_branch": "main", "created_at": "2026-01-01", "change_mode": "bulk_edit"})
        _write_occurrence_map(tmp_path, VALID_OCCURRENCE_MAP)
        result = ensure_occurrence_classification_ready(tmp_path)
        assert result.passed is True
        assert result.change_mode == "bulk_edit"
        assert result.errors == []
