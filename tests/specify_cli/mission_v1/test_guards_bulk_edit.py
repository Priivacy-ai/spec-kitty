"""Tests for the occurrence_map_complete guard in the v1 guard registry."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.mission_v1.guards import GUARD_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _write_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
    """Write a meta.json file."""
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def _write_occurrence_map(feature_dir: Path, content: str) -> None:
    """Write an occurrence_map.yaml file."""
    (feature_dir / "occurrence_map.yaml").write_text(content, encoding="utf-8")


def _make_event_data(feature_dir: Path | None) -> SimpleNamespace:
    """Build a minimal event_data object matching what guards expect."""
    model = SimpleNamespace(feature_dir=feature_dir)
    return SimpleNamespace(model=model)


# ---------------------------------------------------------------------------
# Factory smoke test
# ---------------------------------------------------------------------------


class TestGuardRegistered:
    """The occurrence_map_complete guard must be present in GUARD_REGISTRY."""

    def test_registry_contains_key(self) -> None:
        assert "occurrence_map_complete" in GUARD_REGISTRY

    def test_factory_returns_callable(self) -> None:
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])  # no args needed
        assert callable(guard)


# ---------------------------------------------------------------------------
# Guard behavior
# ---------------------------------------------------------------------------


class TestGuardPassesNonBulkEdit:
    """Guard passes when the mission is not a bulk_edit mission."""

    def test_no_change_mode(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {
            "slug": "feat", "mission_slug": "feat",
            "friendly_name": "Test", "mission_type": "software-dev",
            "target_branch": "main", "created_at": "2026-01-01",
        })
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])
        event_data = _make_event_data(tmp_path)
        assert guard(event_data) is True

    def test_standard_change_mode(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {
            "slug": "feat", "mission_slug": "feat",
            "friendly_name": "Test", "mission_type": "software-dev",
            "target_branch": "main", "created_at": "2026-01-01",
            "change_mode": "standard",
        })
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])
        event_data = _make_event_data(tmp_path)
        assert guard(event_data) is True


class TestGuardPassesNoFeatureDir:
    """Guard passes when feature_dir is None (can't check -- don't block)."""

    def test_none_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])
        event_data = _make_event_data(None)
        assert guard(event_data) is True


class TestGuardFailsBulkEditNoMap:
    """Guard fails when change_mode=bulk_edit but no occurrence_map.yaml."""

    def test_blocks_missing_map(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {
            "slug": "feat", "mission_slug": "feat",
            "friendly_name": "Test", "mission_type": "software-dev",
            "target_branch": "main", "created_at": "2026-01-01",
            "change_mode": "bulk_edit",
        })
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])
        event_data = _make_event_data(tmp_path)
        assert guard(event_data) is False


class TestGuardPassesBulkEditValidMap:
    """Guard passes when change_mode=bulk_edit and a valid occurrence map exists."""

    def test_passes_valid_map(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, {
            "slug": "feat", "mission_slug": "feat",
            "friendly_name": "Test", "mission_type": "software-dev",
            "target_branch": "main", "created_at": "2026-01-01",
            "change_mode": "bulk_edit",
        })
        _write_occurrence_map(tmp_path, VALID_OCCURRENCE_MAP)
        factory = GUARD_REGISTRY["occurrence_map_complete"]
        guard = factory([])
        event_data = _make_event_data(tmp_path)
        assert guard(event_data) is True
