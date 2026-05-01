"""Tests for migration 3.1.1_event_log_merge_driver."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_1_1_event_log_merge_driver import (
    EventLogMergeDriverMigration,
)

pytestmark = pytest.mark.fast


def _git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *cmd],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def test_apply_installs_attributes_and_local_git_config(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Spec Kitty"], tmp_path)

    migration = EventLogMergeDriverMigration()

    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)

    assert result.success is True
    attributes = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
    assert "kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log" in attributes
    assert _git(["config", "--local", "--get", "merge.spec-kitty-event-log.driver"], tmp_path).stdout.strip() == "spec-kitty merge-driver-event-log %O %A %B"
    assert _git(["config", "--local", "--get", "merge.spec-kitty-event-log.name"], tmp_path).stdout.strip() == "Spec Kitty event log union merge"
    assert migration.detect(tmp_path) is False


def test_apply_non_git_project_warns_but_writes_attributes(tmp_path: Path) -> None:
    migration = EventLogMergeDriverMigration()

    result = migration.apply(tmp_path)

    assert result.success is True
    assert (tmp_path / ".gitattributes").exists()
    assert any("not a git repository" in warning for warning in result.warnings)


def test_apply_is_idempotent_for_existing_config(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    migration = EventLogMergeDriverMigration()
    first = migration.apply(tmp_path)
    second = migration.apply(tmp_path)

    assert first.success is True
    assert second.success is True
    assert second.changes_made == []
