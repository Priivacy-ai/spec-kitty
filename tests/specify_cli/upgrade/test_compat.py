from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.compat import uses_centralized_runtime


def test_uses_centralized_runtime_does_not_assume_metadata_less_repo_is_2x(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.6", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    (project / "kitty-specs").mkdir()

    assert uses_centralized_runtime(project) is False


def test_uses_centralized_runtime_treats_metadata_less_worktree_as_runtime_managed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("2.0.6", encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    worktree = tmp_path / "repo" / ".worktrees" / "001-feature-WP01"
    (worktree / "kitty-specs").mkdir(parents=True)

    assert uses_centralized_runtime(worktree) is True
