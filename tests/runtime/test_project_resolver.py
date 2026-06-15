"""Scope: project resolver unit tests — no real git or subprocesses."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from specify_cli.core.project_resolver import (
    locate_project_root,
    resolve_template_path,
)

pytestmark = pytest.mark.fast


def test_locate_project_root_and_template_resolution(tmp_path: Path) -> None:
    """locate_project_root finds .kittify root and resolve_template_path prefers mission-local template."""
    project = tmp_path / "workspace"
    (project / ".kittify" / "missions" / "software-dev" / "templates").mkdir(parents=True)
    (project / ".kittify" / "templates").mkdir(parents=True)
    (project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt").write_text(
        "mission template",
        encoding="utf-8",
    )
    (project / ".kittify" / "templates" / "foo.txt").write_text("fallback", encoding="utf-8")

    nested = project / "nested" / "deeper"
    nested.mkdir(parents=True)

    assert nested.exists(), "nested directory must exist for root search to traverse upward"

    root = locate_project_root(nested)
    template_path = resolve_template_path(project, "software-dev", "foo.txt")

    assert root == project
    assert template_path == project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt"


def test_resolve_template_path_returns_none_when_no_template_exists(tmp_path: Path) -> None:
    """resolve_template_path returns None when no template file is found at any tier (line 70)."""
    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)

    result = resolve_template_path(project, "software-dev", "missing.txt")

    assert result is None


def test_resolve_template_path_swallows_runtime_error_from_home(tmp_path: Path) -> None:
    """resolve_template_path silently skips global tiers when get_kittify_home() raises RuntimeError."""
    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)

    with patch(
        "specify_cli.runtime.home.get_kittify_home",
        side_effect=RuntimeError("no home configured"),
    ):
        result = resolve_template_path(project, "software-dev", "missing.txt")

    assert result is None


def test_env_root_authoritative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T004: SPECIFY_REPO_ROOT overrides everything — no .kittify needed (#1965)."""
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))
    result = locate_project_root(start=tmp_path)
    assert result == tmp_path.resolve()


def test_worktree_pointer_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T005: locate_project_root follows .git file pointer to main repo."""
    main_repo = tmp_path / "main_repo"
    (main_repo / ".kittify").mkdir(parents=True)
    worktrees_dir = main_repo / ".git" / "worktrees" / "test_lane"
    worktrees_dir.mkdir(parents=True)

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n", encoding="utf-8")

    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    result = locate_project_root(start=worktree)
    assert result == main_repo


def test_locate_project_root_with_explicit_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T006: locate_project_root respects the start parameter for .kittify walk (Tier 3)."""
    (tmp_path / ".kittify").mkdir()
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    result = locate_project_root(start=tmp_path)
    assert result == tmp_path
