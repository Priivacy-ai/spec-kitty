"""Tests for the 0.9.2 research mission template migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_9_2_research_mission_templates import (
    ResearchMissionTemplatesMigration,
)

pytestmark = pytest.mark.fast


def _write_file(path: Path, content: str = "content\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _package_research_dir(tmp_path: Path, *, include_legacy_tasks_command: bool) -> Path:
    package_research = tmp_path / "package" / "research"
    _write_file(package_research / "templates" / "task-prompt-template.md", "task prompt\n")
    if include_legacy_tasks_command:
        _write_file(package_research / "command-templates" / "tasks.md", "legacy tasks command\n")
    return package_research


def _project_research_dir(tmp_path: Path) -> Path:
    project_research = tmp_path / "project" / ".kittify" / "missions" / "research"
    project_research.mkdir(parents=True, exist_ok=True)
    return project_research


def test_detect_ignores_legacy_tasks_command_when_runtime_no_longer_ships_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = ResearchMissionTemplatesMigration()
    package_research = _package_research_dir(tmp_path, include_legacy_tasks_command=False)
    monkeypatch.setattr(migration, "_find_package_research_mission", lambda: package_research)

    project = tmp_path / "project"
    project_research = _project_research_dir(tmp_path)
    _write_file(project_research / "templates" / "task-prompt-template.md", "existing task prompt\n")

    assert migration.detect(project) is False


def test_can_apply_accepts_modern_runtime_without_research_tasks_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = ResearchMissionTemplatesMigration()
    package_research = _package_research_dir(tmp_path, include_legacy_tasks_command=False)
    monkeypatch.setattr(migration, "_find_package_research_mission", lambda: package_research)

    project = tmp_path / "project"
    _project_research_dir(tmp_path)

    can_apply, reason = migration.can_apply(project)

    assert can_apply is True, reason
    assert reason == ""


def test_apply_copies_only_supported_assets_for_modern_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = ResearchMissionTemplatesMigration()
    package_research = _package_research_dir(tmp_path, include_legacy_tasks_command=False)
    monkeypatch.setattr(migration, "_find_package_research_mission", lambda: package_research)

    project = tmp_path / "project"
    project_research = _project_research_dir(tmp_path)

    result = migration.apply(project)

    assert result.success is True, result
    assert (project_research / "templates" / "task-prompt-template.md").exists()
    assert not (project_research / "command-templates" / "tasks.md").exists()
