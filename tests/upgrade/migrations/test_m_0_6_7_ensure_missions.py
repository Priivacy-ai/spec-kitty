"""Scope: mock-boundary tests for the 0.6.7 ensure-missions migration — no real git."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.m_0_6_7_ensure_missions import (
    EnsureMissionsMigration,
)

pytestmark = pytest.mark.fast


def test_detect_skips_when_global_runtime_is_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2.x runtime-managed installs do not require project-local missions."""
    # Arrange
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

    # Assumption check
    assert (project / ".kittify").exists(), "project .kittify directory must exist"

    # Act
    result = migration.detect(project)

    # Assert
    assert result is False


def test_detect_still_repairs_metadata_less_legacy_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 0.x repo with .kittify but no metadata should not be treated as 2.x."""
    # Arrange
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.6", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    (project / "kitty-specs").mkdir()

    migration = EnsureMissionsMigration()

    # Assumption check
    assert not (project / ".kittify" / "metadata.yaml").exists(), "no metadata.yaml must be present"

    # Act
    result = migration.detect(project)

    # Assert
    assert result is True
