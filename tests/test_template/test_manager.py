from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.template import manager
from specify_cli.template.manager import copy_specify_base_from_local, get_local_repo_root


def test_get_local_repo_root_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates" / "commands"
    templates_dir.mkdir(parents=True)
    marker = templates_dir / "demo.md"
    marker.write_text("# demo", encoding="utf-8")

    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(tmp_path))
    try:
        repo_root = get_local_repo_root()
        assert repo_root == tmp_path.resolve()
    finally:
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)


def test_copy_specify_base_from_local_copies_expected_assets(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    memory_src = repo_root / "memory"
    (memory_src / "seed.txt").parent.mkdir(parents=True, exist_ok=True)
    (memory_src / "seed.txt").write_text("hello", encoding="utf-8")

    scripts_src = repo_root / "scripts"
    (scripts_src / "bash").mkdir(parents=True)
    (scripts_src / "bash" / "bootstrap.sh").write_text("echo hi", encoding="utf-8")
    (scripts_src / "tasks").mkdir()
    (scripts_src / "tasks" / "tasks_cli.py").write_text("print('ok')", encoding="utf-8")

    templates_src = repo_root / "templates" / "commands"
    templates_src.mkdir(parents=True)
    (templates_src / "sample.md").write_text("content", encoding="utf-8")
    (repo_root / "templates" / "AGENTS.md").write_text("agents", encoding="utf-8")

    missions_src = repo_root / ".kittify" / "missions" / "default"
    missions_src.mkdir(parents=True)
    (missions_src / "rules.md").write_text("rules", encoding="utf-8")

    project_path = tmp_path / "project"
    project_path.mkdir()

    commands_dir = copy_specify_base_from_local(repo_root, project_path, "sh")

    assert commands_dir.exists()
    assert (project_path / ".kittify" / "memory" / "seed.txt").read_text(encoding="utf-8") == "hello"
    assert (project_path / ".kittify" / "scripts" / "bash" / "bootstrap.sh").exists()
    assert (project_path / ".kittify" / "scripts" / "tasks" / "tasks_cli.py").exists()
    assert (project_path / ".kittify" / "templates" / "commands" / "sample.md").exists()
    assert (project_path / ".kittify" / "missions" / "default" / "rules.md").exists()


def test_copy_specify_base_from_package_uses_packaged_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_pkg = tmp_path / "package_data"
    (fake_pkg / "memory").mkdir(parents=True)
    (fake_pkg / "memory" / "seed.txt").write_text("seed", encoding="utf-8")

    scripts_root = fake_pkg / "scripts"
    (scripts_root / "bash").mkdir(parents=True)
    (scripts_root / "bash" / "bootstrap.sh").write_text("echo hi", encoding="utf-8")
    (scripts_root / "tasks").mkdir()
    (scripts_root / "tasks" / "tasks_cli.py").write_text("print('ok')", encoding="utf-8")

    templates_root = fake_pkg / "templates" / "commands"
    templates_root.mkdir(parents=True)
    (templates_root / "sample.md").write_text("demo", encoding="utf-8")
    (fake_pkg / "templates" / "AGENTS.md").write_text("rules", encoding="utf-8")

    missions_root = fake_pkg / ".kittify" / "missions" / "default"
    missions_root.mkdir(parents=True)
    (missions_root / "rules.md").write_text("mission rules", encoding="utf-8")

    monkeypatch.setattr(manager, "files", lambda _: fake_pkg)

    project_path = tmp_path / "pkg-project"
    project_path.mkdir()

    commands_dir = manager.copy_specify_base_from_package(project_path, "sh")

    assert commands_dir.exists()
    assert (commands_dir / "sample.md").exists()
    assert (project_path / ".kittify" / "scripts" / "bash" / "bootstrap.sh").exists()
    assert (project_path / ".kittify" / "scripts" / "tasks" / "tasks_cli.py").exists()
    assert (project_path / ".kittify" / "memory" / "seed.txt").exists()
