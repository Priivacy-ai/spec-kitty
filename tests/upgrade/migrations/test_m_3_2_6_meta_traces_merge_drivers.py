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
