from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console

from specify_cli.template import manager, get_local_repo_root
from specify_cli.template.manager import copy_specify_base_from_local


pytestmark = [pytest.mark.unit, pytest.mark.fast]
def test_get_local_repo_root_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    templates_dir = tmp_path / "src" / "doctrine" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "AGENTS.md").write_text("# agents", encoding="utf-8")
    (tmp_path / "src" / "doctrine" / "missions").mkdir(parents=True)

    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(tmp_path))
    try:
        repo_root = get_local_repo_root()
        assert repo_root == tmp_path.resolve()
    finally:
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)


def test_get_local_repo_root_invalid_env_clarifies_packaged_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = io.StringIO()
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setattr(manager, "console", Console(file=output, force_terminal=False, width=240))

    repo_root = get_local_repo_root()

    assert repo_root is None or repo_root.exists()
    assert "not a Spec Kitty checkout/template root" in output.getvalue()
    assert "using packaged templates" in output.getvalue()


def test_copy_specify_base_from_local_copies_expected_assets(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Memory is still copied from .kittify/memory/ (project-specific content)
    memory_src = repo_root / ".kittify" / "memory"
    memory_src.mkdir(parents=True, exist_ok=True)
    (memory_src / "seed.txt").write_text("hello", encoding="utf-8")

    templates_src = repo_root / "src" / "doctrine" / "templates" / "command-templates"
    templates_src.mkdir(parents=True)
    (templates_src / "sample.md").write_text("content", encoding="utf-8")
    (repo_root / "src" / "doctrine" / "templates" / "AGENTS.md").write_text("agents", encoding="utf-8")

    missions_src = repo_root / "src" / "doctrine" / "missions" / "default"
    missions_src.mkdir(parents=True)
    (missions_src / "rules.md").write_text("rules", encoding="utf-8")

    project_path = tmp_path / "project"
    project_path.mkdir()

    commands_dir = copy_specify_base_from_local(repo_root, project_path)

    assert commands_dir.exists()
    assert (project_path / ".kittify" / "memory" / "seed.txt").read_text(encoding="utf-8") == "hello"
    assert (project_path / ".kittify" / "templates" / "command-templates" / "sample.md").exists()
    assert (project_path / ".kittify" / "missions" / "default" / "rules.md").exists()


def test_copy_specify_base_from_package_uses_packaged_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_pkg = tmp_path / "package_data"
    (fake_pkg / "memory").mkdir(parents=True)
    (fake_pkg / "memory" / "seed.txt").write_text("seed", encoding="utf-8")

    # Package uses templates/command-templates
    templates_root = fake_pkg / "templates" / "command-templates"
    templates_root.mkdir(parents=True)
    (templates_root / "sample.md").write_text("demo", encoding="utf-8")
    (fake_pkg / "templates" / "AGENTS.md").write_text("rules", encoding="utf-8")

    missions_root = fake_pkg / "missions" / "default"
    missions_root.mkdir(parents=True)
    (missions_root / "rules.md").write_text("mission rules", encoding="utf-8")

    monkeypatch.setattr(manager, "files", lambda _: fake_pkg)

    project_path = tmp_path / "pkg-project"
    project_path.mkdir()

    commands_dir = manager.copy_specify_base_from_package(project_path)

    assert commands_dir.exists()
    assert (commands_dir / "sample.md").exists()
    assert (project_path / ".kittify" / "memory" / "seed.txt").exists()
