"""Scope: compat unit tests — no real git or subprocesses."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.compat import uses_centralized_runtime

pytestmark = pytest.mark.fast


def test_uses_centralized_runtime_does_not_assume_metadata_less_repo_is_2x(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repo with .kittify but no metadata.yaml is not treated as 2.x managed."""
    # Arrange
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.6", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    (project / "kitty-specs").mkdir()

    # Assumption check
    assert not (project / ".kittify" / "metadata.yaml").exists(), "must have no metadata file"

    # Act
    result = uses_centralized_runtime(project)

    # Assert
    assert result is False


def test_uses_centralized_runtime_treats_metadata_less_worktree_as_runtime_managed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worktree path without metadata is treated as runtime-managed (no project-local config needed)."""
    # Arrange
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.6", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    worktree = tmp_path / "repo" / ".worktrees" / "001-mission-WP01"
    (worktree / "kitty-specs").mkdir(parents=True)

    # Assumption check
    assert ".worktrees" in str(worktree), "path must be a worktree path"

    # Act
    result = uses_centralized_runtime(worktree)

    # Assert
    assert result is True
