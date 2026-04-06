"""Scope: project resolver unit tests — no real git or subprocesses."""

import pytest
from specify_cli.core.project_resolver import (
    locate_project_root,
    resolve_template_path,
    resolve_worktree_aware_feature_dir,
)

pytestmark = pytest.mark.fast


def test_locate_project_root_and_template_resolution(tmp_path):
    """locate_project_root finds .kittify root and resolve_template_path prefers mission-local template."""
    # Arrange
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

    # Assumption check
    assert nested.exists(), "nested directory must exist for root search to traverse upward"

    # Act
    root = locate_project_root(nested)
    template_path = resolve_template_path(project, "software-dev", "foo.txt")

    # Assert
    assert root == project
    assert template_path == project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt"


def test_resolve_worktree_awareness(tmp_path):
    """resolve_worktree_aware_feature_dir uses worktree path when CWD is inside a worktree."""
    # Arrange
    repo_root = tmp_path / "spec-kitty"
    mission_slug = "004-modular-code-refactoring"
    worktree = repo_root / ".worktrees" / mission_slug / "kitty-specs" / mission_slug / "tasks"
    worktree.mkdir(parents=True)

    cwd_inside = worktree / "doing"
    cwd_inside.mkdir()

    # Assumption check
    assert cwd_inside.exists(), "CWD inside worktree must exist"

    # Act
    resolved = resolve_worktree_aware_feature_dir(repo_root, mission_slug, cwd=cwd_inside)

    # Assert
    assert resolved == repo_root / ".worktrees" / mission_slug / "kitty-specs" / mission_slug

    repo_root.mkdir(exist_ok=True)
    fallback = resolve_worktree_aware_feature_dir(repo_root, "999-new-feature")
    assert fallback == repo_root / "kitty-specs" / "999-new-feature"
