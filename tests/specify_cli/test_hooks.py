from __future__ import annotations

import os
from pathlib import Path

from specify_cli.hooks import (
    MANAGED_SHIM_MARKER,
    get_project_hook_status,
    install_global_hook_assets,
    install_or_update_hooks,
    install_project_hook_shims,
    remove_project_hook_shims,
)


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    (project / ".git" / "hooks").mkdir(parents=True)
    return project


def _make_template_hooks(tmp_path: Path) -> Path:
    hooks_dir = tmp_path / "package" / "templates" / "git-hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (hooks_dir / "commit-msg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (hooks_dir / "pre-commit-agent-check").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    return hooks_dir


def test_install_or_update_hooks_creates_global_hooks_and_project_shims(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    template_hooks = _make_template_hooks(tmp_path)
    global_home = tmp_path / "global-home"

    result = install_or_update_hooks(
        project,
        global_home=global_home,
        template_hooks_dir=template_hooks,
    )

    assert (global_home / "hooks" / "pre-commit").exists()
    assert (global_home / "hooks" / "commit-msg").exists()
    assert set(result.global_hooks) >= {"pre-commit", "commit-msg"}

    pre_commit = project / ".git" / "hooks" / "pre-commit"
    commit_msg = project / ".git" / "hooks" / "commit-msg"
    assert pre_commit.exists()
    assert commit_msg.exists()
    assert MANAGED_SHIM_MARKER in pre_commit.read_text(encoding="utf-8")
    assert MANAGED_SHIM_MARKER in commit_msg.read_text(encoding="utf-8")

    if os.name != "nt":
        assert os.access(pre_commit, os.X_OK)
        assert os.access(commit_msg, os.X_OK)


def test_install_project_hook_shims_skips_existing_custom_hook(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    template_hooks = _make_template_hooks(tmp_path)
    global_home = tmp_path / "global-home"
    install_global_hook_assets(global_home=global_home, template_hooks_dir=template_hooks)

    pre_commit = project / ".git" / "hooks" / "pre-commit"
    pre_commit.write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")

    result = install_project_hook_shims(project, global_home=global_home, force=False)

    assert result.skipped_custom == ("pre-commit",)
    assert (project / ".git" / "hooks" / "commit-msg").exists()
    assert pre_commit.read_text(encoding="utf-8") == "#!/usr/bin/env bash\necho custom\n"


def test_remove_project_hook_shims_preserves_custom_hooks_by_default(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    template_hooks = _make_template_hooks(tmp_path)
    global_home = tmp_path / "global-home"

    install_or_update_hooks(project, global_home=global_home, template_hooks_dir=template_hooks)

    commit_msg = project / ".git" / "hooks" / "commit-msg"
    commit_msg.write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")

    result = remove_project_hook_shims(project, force=False)

    assert "pre-commit" in result.removed
    assert "commit-msg" in result.skipped_custom
    assert not (project / ".git" / "hooks" / "pre-commit").exists()
    assert commit_msg.exists()


def test_get_project_hook_status_reports_mixed_managed_and_custom(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    template_hooks = _make_template_hooks(tmp_path)
    global_home = tmp_path / "global-home"

    install_global_hook_assets(global_home=global_home, template_hooks_dir=template_hooks)
    install_project_hook_shims(project, global_home=global_home)

    # Replace one managed shim with a custom script and remove global target.
    commit_msg = project / ".git" / "hooks" / "commit-msg"
    commit_msg.write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")
    (global_home / "hooks" / "commit-msg").unlink()

    status = {item.name: item for item in get_project_hook_status(project, global_home=global_home)}

    assert status["pre-commit"].global_exists is True
    assert status["pre-commit"].project_managed is True
    assert status["pre-commit"].project_points_to_global is True

    assert status["commit-msg"].global_exists is False
    assert status["commit-msg"].project_exists is True
    assert status["commit-msg"].project_managed is False
