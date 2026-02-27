"""Tests for generated prompt repair migration (2.0.1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from specify_cli.core.agent_config import AgentConfig, save_agent_config
from specify_cli.upgrade.migrations.m_2_0_1_fix_generated_command_templates import (
    FixGeneratedCommandTemplatesMigration,
)


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".kittify").mkdir()
    save_agent_config(project, AgentConfig(available=["codex", "opencode"]))
    (project / ".codex" / "prompts").mkdir(parents=True)
    (project / ".opencode" / "command").mkdir(parents=True)
    return project


def test_detects_stale_generated_prompts(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".codex" / "prompts" / "spec-kitty.analyze.md"
    stale.write_text(
        "spec-kitty agent check-prerequisites --json --require-tasks --include-tasks\n",
        encoding="utf-8",
    )

    migration = FixGeneratedCommandTemplatesMigration()
    assert migration.detect(project) is True


def test_applies_replacements_to_generated_prompts(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".opencode" / "command" / "spec-kitty.merge.md"
    stale.write_text(
        "\n".join(
            [
                "spec-kitty agent check-prerequisites --json --require-tasks",
                "(Missing script command for sh)",
                "The command merges each WP branch into main in sequence",
                "Run from main repository root",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    migration = FixGeneratedCommandTemplatesMigration()
    result = migration.apply(project, dry_run=False)

    assert result.success is True
    updated = stale.read_text(encoding="utf-8")
    assert "spec-kitty agent feature check-prerequisites" in updated
    assert "--require-tasks" not in updated
    assert "(Missing script command for sh)" not in updated
    assert "ancestry pruning" in updated
    assert "primary repository checkout root" in updated


def test_dry_run_reports_without_modifying(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".codex" / "prompts" / "spec-kitty.clarify.md"
    original = "spec-kitty agent check-prerequisites --json --paths-only\n"
    stale.write_text(original, encoding="utf-8")

    migration = FixGeneratedCommandTemplatesMigration()
    result = migration.apply(project, dry_run=True)

    assert result.success is True
    assert any("Would update" in change for change in result.changes_made)
    assert stale.read_text(encoding="utf-8") == original


def test_noop_when_files_are_already_clean(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    clean = project / ".codex" / "prompts" / "spec-kitty.tasks.md"
    clean.write_text(
        "spec-kitty agent feature check-prerequisites --json --include-tasks\n",
        encoding="utf-8",
    )

    migration = FixGeneratedCommandTemplatesMigration()
    assert migration.detect(project) is False
    result = migration.apply(project, dry_run=False)
    assert result.success is True
    assert result.changes_made == ["No generated prompt files needed repair"]


def test_detect_skips_unreadable_generated_prompt(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".codex" / "prompts" / "spec-kitty.analyze.md"
    stale.write_text("spec-kitty agent check-prerequisites --json --require-tasks\n", encoding="utf-8")

    migration = FixGeneratedCommandTemplatesMigration()
    with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
        assert migration.detect(project) is False


def test_apply_records_warning_for_unreadable_file(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".codex" / "prompts" / "spec-kitty.merge.md"
    stale.write_text("spec-kitty agent check-prerequisites --json --require-tasks\n", encoding="utf-8")

    migration = FixGeneratedCommandTemplatesMigration()
    with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
        result = migration.apply(project, dry_run=False)

    assert result.success is True
    assert any("Skipped unreadable file" in warning for warning in result.warnings)


def test_apply_records_error_when_write_fails(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    stale = project / ".codex" / "prompts" / "spec-kitty.merge.md"
    stale.write_text("spec-kitty agent check-prerequisites --json --require-tasks\n", encoding="utf-8")

    migration = FixGeneratedCommandTemplatesMigration()
    with patch.object(Path, "write_text", side_effect=OSError("disk full")):
        result = migration.apply(project, dry_run=False)

    assert result.success is False
    assert any("Failed to update" in error for error in result.errors)


def test_iter_generated_prompt_files_skips_missing_agent_dir(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    opencode_dir = project / ".opencode" / "command"
    opencode_dir.rmdir()

    migration = FixGeneratedCommandTemplatesMigration()
    files = migration._iter_generated_prompt_files(project)
    assert all(str(path).startswith(str(project / ".codex")) for path in files) or files == []
