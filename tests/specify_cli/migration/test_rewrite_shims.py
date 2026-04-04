"""Tests for migration/rewrite_shims.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.migration.rewrite_shims import RewriteResult, rewrite_agent_shims

pytestmark = pytest.mark.fast


def _setup_project(tmp_path: Path, agents: list[str]) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)

    config_lines = ["agents:\n", "  available:\n"]
    for agent in agents:
        config_lines.append(f"    - {agent}\n")
    (kittify / "config.yaml").write_text("".join(config_lines), encoding="utf-8")
    return project


class TestRewriteAgentShims:
    def test_projects_managed_claude_commands(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

        project = _setup_project(tmp_path, ["claude"])
        result = rewrite_agent_shims(project)

        assert isinstance(result, RewriteResult)
        assert result.agents_processed == 1

        claude_dir = project / ".claude" / "commands"
        command_files = list(claude_dir.glob("spec-kitty.*.md"))
        assert len(command_files) == 16
        assert any(path.name == "spec-kitty.implement.md" for path in result.files_written)

    def test_retires_legacy_codex_prompts(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

        project = _setup_project(tmp_path, ["codex"])
        legacy_file = project / ".codex" / "prompts" / "spec-kitty.plan.md"
        legacy_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_file.write_text("# stale\n", encoding="utf-8")

        result = rewrite_agent_shims(project)

        assert result.agents_processed == 1
        assert legacy_file in result.files_deleted
        assert not legacy_file.exists()
        assert not (project / ".codex" / "prompts").exists()

    def test_stale_command_file_removed(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

        project = _setup_project(tmp_path, ["claude"])
        claude_dir = project / ".claude" / "commands"
        claude_dir.mkdir(parents=True, exist_ok=True)
        stale = claude_dir / "spec-kitty.old-workflow.md"
        stale.write_text("# stale\n", encoding="utf-8")

        result = rewrite_agent_shims(project)

        assert stale in result.files_deleted
        assert not stale.exists()

    def test_idempotent(self, tmp_path: Path, monkeypatch) -> None:
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

        project = _setup_project(tmp_path, ["claude"])
        result1 = rewrite_agent_shims(project)
        result2 = rewrite_agent_shims(project)

        assert len(result2.files_deleted) == 0
        assert len(result2.files_written) <= len(result1.files_written)

    def test_no_config_handled(self, tmp_path: Path) -> None:
        result = rewrite_agent_shims(tmp_path)
        assert isinstance(result, RewriteResult)
        assert result.agents_processed == 0
