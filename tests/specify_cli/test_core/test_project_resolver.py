from pathlib import Path

from specify_cli.core.project_resolver import (
    get_active_mission_key,
    locate_project_root,
    resolve_template_path,
    resolve_worktree_aware_feature_dir,
)


def test_locate_project_root_and_template_resolution(tmp_path):
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
    assert locate_project_root(nested) == project

    template_path = resolve_template_path(project, "software-dev", "foo.txt")
    assert template_path == project / ".kittify" / "missions" / "software-dev" / "templates" / "foo.txt"


def test_get_active_mission_key_prefers_file(tmp_path):
    project = tmp_path / "workspace"
    (project / ".kittify").mkdir(parents=True)
    marker = project / ".kittify" / "active-mission"
    marker.write_text("research\n", encoding="utf-8")

    assert get_active_mission_key(project) == "research"


def test_resolve_worktree_awareness(tmp_path):
    repo_root = tmp_path / "spec-kitty"
    feature_slug = "004-modular-code-refactoring"
    worktree = repo_root / ".worktrees" / feature_slug / "kitty-specs" / feature_slug / "tasks"
    worktree.mkdir(parents=True)

    cwd_inside = worktree / "doing"
    cwd_inside.mkdir()
    resolved = resolve_worktree_aware_feature_dir(repo_root, feature_slug, cwd=cwd_inside)
    assert resolved == repo_root / ".worktrees" / feature_slug / "kitty-specs" / feature_slug

    repo_root.mkdir(exist_ok=True)
    fallback = resolve_worktree_aware_feature_dir(repo_root, "999-new-feature")
    assert fallback == repo_root / "kitty-specs" / "999-new-feature"
