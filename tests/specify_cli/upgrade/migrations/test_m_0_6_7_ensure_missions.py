"""Tests for the 0.6.7 ensure-missions detector in runtime-managed installs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.m_0_6_7_ensure_missions import (
    EnsureMissionsMigration,
)


def test_detect_skips_when_global_runtime_is_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2.x runtime-managed installs do not require project-local missions."""
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.5", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    (project / "kitty-specs").mkdir()
    ProjectMetadata(
        version="2.0.6",
        initialized_at=datetime.now(),
    ).save(project / ".kittify")

    migration = EnsureMissionsMigration()
    assert migration.detect(project) is False
