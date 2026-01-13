from __future__ import annotations

from pathlib import Path

from specify_cli.upgrade.migrations.m_0_11_3_workflow_agent_flag import (
    WorkflowAgentFlagMigration,
)


def _write_prompt(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{line}\n", encoding="utf-8")


def test_workflow_agent_flag_migration_updates_prompts(tmp_path: Path) -> None:
    project_path = tmp_path
    (project_path / ".kittify").mkdir()

    _write_prompt(
        project_path / ".claude" / "commands" / "spec-kitty.implement.md",
        "spec-kitty agent workflow implement WP01",
    )
    _write_prompt(
        project_path / ".claude" / "commands" / "spec-kitty.review.md",
        "spec-kitty agent workflow review WP01",
    )
    _write_prompt(
        project_path / ".github" / "prompts" / "spec-kitty.review.md",
        "spec-kitty agent workflow review WP02",
    )

    migration = WorkflowAgentFlagMigration()
    assert migration.detect(project_path) is True

    result = migration.apply(project_path, dry_run=False)
    assert result.success is True

    claude_implement = (project_path / ".claude" / "commands" / "spec-kitty.implement.md").read_text(
        encoding="utf-8"
    )
    claude_review = (project_path / ".claude" / "commands" / "spec-kitty.review.md").read_text(
        encoding="utf-8"
    )
    copilot_review = (project_path / ".github" / "prompts" / "spec-kitty.review.md").read_text(
        encoding="utf-8"
    )

    assert "spec-kitty agent workflow implement WP01 --agent claude" in claude_implement
    assert "spec-kitty agent workflow review WP01 --agent claude" in claude_review
    assert "spec-kitty agent workflow review WP02 --agent copilot" in copilot_review
