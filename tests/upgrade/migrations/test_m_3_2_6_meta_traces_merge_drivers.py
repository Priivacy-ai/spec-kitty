"""Tests for migration 3.2.6_meta_traces_merge_drivers (#2709 / C-006)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_6_meta_traces_merge_drivers import (
    MetaTracesMergeDriverMigration,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_META_ENTRY = "kitty-specs/**/meta.json merge=spec-kitty-meta"
_TRACES_ENTRY = "kitty-specs/**/traces/*.md merge=spec-kitty-traces"


def _git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *cmd], cwd=cwd, text=True, capture_output=True, check=True)


def test_apply_installs_both_drivers_attributes_and_config(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Spec Kitty"], tmp_path)

    migration = MetaTracesMergeDriverMigration()
    assert migration.detect(tmp_path) is True

    result = migration.apply(tmp_path)
    assert result.success is True

    attributes = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
    assert _META_ENTRY in attributes
    assert _TRACES_ENTRY in attributes
    assert (
        _git(["config", "--local", "--get", "merge.spec-kitty-meta.driver"], tmp_path)
        .stdout.strip()
        == "spec-kitty merge-driver-meta %O %A %B"
    )
    assert (
        _git(["config", "--local", "--get", "merge.spec-kitty-traces.driver"], tmp_path)
        .stdout.strip()
        == "spec-kitty merge-driver-traces %O %A %B"
    )
    assert migration.detect(tmp_path) is False


def test_apply_non_git_project_warns_but_writes_attributes(tmp_path: Path) -> None:
    result = MetaTracesMergeDriverMigration().apply(tmp_path)
    assert result.success is True
    attributes = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
    assert _META_ENTRY in attributes
    assert _TRACES_ENTRY in attributes
    assert any("not a git repository" in warning for warning in result.warnings)


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    migration = MetaTracesMergeDriverMigration()
    first = migration.apply(tmp_path)
    second = migration.apply(tmp_path)
    assert first.success is True
    assert second.success is True
    assert second.changes_made == []


def test_can_apply_rejects_missing_path(tmp_path: Path) -> None:
    absent = tmp_path / "does-not-exist"
    ok, reason = MetaTracesMergeDriverMigration().can_apply(absent)
    assert ok is False
    assert "does not exist" in reason


def test_can_apply_accepts_existing_path(tmp_path: Path) -> None:
    ok, reason = MetaTracesMergeDriverMigration().can_apply(tmp_path)
    assert ok is True
    assert reason == ""


def test_dry_run_reports_change_without_writing(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    result = MetaTracesMergeDriverMigration().apply(tmp_path, dry_run=True)
    assert result.success is True
    assert any("Would install" in change for change in result.changes_made)
    assert not (tmp_path / ".gitattributes").exists()  # dry run wrote nothing


def test_config_missing_false_without_git(tmp_path: Path) -> None:
    """No ``.git`` — driver config cannot be missing (nothing to configure)."""
    assert MetaTracesMergeDriverMigration()._config_missing(tmp_path) is False


def test_config_missing_true_when_git_config_absent(tmp_path: Path) -> None:
    """A git repo with no merge-driver config reported as config-missing."""
    _git(["init", "-b", "main"], tmp_path)
    assert MetaTracesMergeDriverMigration()._config_missing(tmp_path) is True
