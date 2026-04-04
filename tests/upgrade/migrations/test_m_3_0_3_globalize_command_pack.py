"""Tests for the 3.0.3 globalize-command-pack migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_0_3_globalize_command_pack import (
    GlobalizeCommandPackMigration,
)

pytestmark = pytest.mark.fast


def _setup_project(tmp_path: Path, agents: list[str]) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir()

    config_content = "agents:\n  available:\n"
    for agent_key in agents:
        config_content += f"    - {agent_key}\n"
    (kittify / "config.yaml").write_text(config_content, encoding="utf-8")
    return project


def _setup_command_templates(tmp_path: Path) -> Path:
    root = tmp_path / "package-missions"
    templates = root / "software-dev" / "command-templates"
    templates.mkdir(parents=True, exist_ok=True)
    for name in (
        "analyze",
        "checklist",
        "constitution",
        "plan",
        "research",
        "specify",
        "tasks",
        "tasks-outline",
        "tasks-packages",
    ):
        (templates / f"{name}.md").write_text(
            f"# {name}\n\nDetailed workflow prompt.\n",
            encoding="utf-8",
        )
    return root


def test_detects_configured_project(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, ["claude"])
    assert GlobalizeCommandPackMigration().detect(project) is True


def test_apply_projects_claude_commands_and_retires_codex_prompts(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(_setup_command_templates(tmp_path)))

    project = _setup_project(tmp_path, ["claude", "codex"])
    legacy_codex = project / ".codex" / "prompts" / "spec-kitty.plan.md"
    legacy_codex.parent.mkdir(parents=True, exist_ok=True)
    legacy_codex.write_text("# stale codex prompt\n", encoding="utf-8")

    result = GlobalizeCommandPackMigration().apply(project)

    assert result.success is True
    assert any(change.startswith("claude: mode=projected") for change in result.changes_made)
    assert any(change.startswith("codex: mode=legacy-retired") for change in result.changes_made)

    claude_project = project / ".claude" / "commands" / "spec-kitty.plan.md"
    claude_global = home / ".claude" / "commands" / "spec-kitty.plan.md"

    assert claude_project.exists()
    assert claude_global.exists()
    assert not legacy_codex.exists()
    assert not (project / ".codex" / "prompts").exists()
