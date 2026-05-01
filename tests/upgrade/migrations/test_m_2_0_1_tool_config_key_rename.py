"""Tests for 2.0.1 tool config key rename migration."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.upgrade.migrations.m_2_0_1_tool_config_key_rename import (
    ToolConfigKeyRenameMigration,
)
import pytest

pytestmark = pytest.mark.fast


def _write_config(tmp_path: Path, text: str) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config_file = kittify / "config.yaml"
    config_file.write_text(text, encoding="utf-8")
    return config_file


def _read_yaml(path: Path) -> dict:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.load(fh) or {}


def test_detect_true_for_legacy_agents_key(tmp_path: Path) -> None:
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n")
    migration = ToolConfigKeyRenameMigration()
    assert migration.detect(tmp_path) is True


def test_detect_false_when_tools_already_present(tmp_path: Path) -> None:
    _write_config(tmp_path, "tools:\n  available:\n    - codex\n")
    migration = ToolConfigKeyRenameMigration()
    assert migration.detect(tmp_path) is False


def test_apply_renames_agents_to_tools(tmp_path: Path) -> None:
    config = _write_config(
        tmp_path,
        "agents:\n  available:\n    - claude\n",
    )
    migration = ToolConfigKeyRenameMigration()

    result = migration.apply(tmp_path, dry_run=False)
    assert result.success
    data = _read_yaml(config)
    assert "tools" in data
    assert "agents" not in data
    assert data["tools"]["available"] == ["claude"]


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _write_config(tmp_path, "tools:\n  available:\n    - gemini\n")
    migration = ToolConfigKeyRenameMigration()

    first = migration.apply(tmp_path, dry_run=False)
    second = migration.apply(tmp_path, dry_run=False)

    assert first.success and second.success
    assert "already uses canonical `tools` key" in " ".join(first.changes_made)
    assert "already uses canonical `tools` key" in " ".join(second.changes_made)


def test_apply_dry_run_reports_change_without_writing(tmp_path: Path) -> None:
    config = _write_config(tmp_path, "agents:\n  available:\n    - claude\n")
    migration = ToolConfigKeyRenameMigration()

    result = migration.apply(tmp_path, dry_run=True)
    assert result.success
    assert any("Would rename" in change for change in result.changes_made)

    data = _read_yaml(config)
    assert "agents" in data
    assert "tools" not in data
