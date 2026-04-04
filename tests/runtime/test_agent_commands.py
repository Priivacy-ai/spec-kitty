"""Tests for the global managed command bootstrap and projection helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.agent_commands import (
    AgentCommandInstallResult,
    ensure_global_agent_commands,
    install_project_commands_for_agent,
    iter_command_agents,
    retire_legacy_codex_prompts,
    supports_managed_commands,
)

pytestmark = pytest.mark.fast


def test_supports_managed_commands_skips_codex_and_unknown() -> None:
    assert supports_managed_commands("claude") is True
    assert supports_managed_commands("codex") is False
    assert supports_managed_commands("unknown-agent") is False


def test_ensure_global_agent_commands_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    synced: list[str] = []

    def fake_sync(agent_key: str, templates: Path, script_type: str) -> list[Path]:
        synced.append(agent_key)
        assert templates == templates_dir
        assert script_type == "sh"
        return []

    monkeypatch.setattr("specify_cli.runtime.agent_commands._command_templates_dir", lambda: templates_dir)
    monkeypatch.setattr("specify_cli.runtime.agent_commands._get_cli_version", lambda: "3.0.3-test")
    monkeypatch.setattr("specify_cli.runtime.agent_commands._resolve_script_type", lambda: "sh")
    monkeypatch.setattr("specify_cli.runtime.agent_commands._sync_global_command_root", fake_sync)

    ensure_global_agent_commands()
    ensure_global_agent_commands()

    assert synced == iter_command_agents()
    version_file = home / ".kittify" / "cache" / "agent-commands.lock"
    assert version_file.read_text(encoding="utf-8") == "3.0.3-test"


def test_install_project_commands_dispatches_to_global_projection(tmp_path: Path, monkeypatch) -> None:
    expected = AgentCommandInstallResult(agent_key="claude", mode="projected")
    monkeypatch.setattr("specify_cli.runtime.agent_commands._project_global_commands", lambda project, agent: expected)

    result = install_project_commands_for_agent(tmp_path, "claude")

    assert result is expected


def test_install_project_commands_dispatches_to_override_render(tmp_path: Path, monkeypatch) -> None:
    override_dir = tmp_path / ".kittify" / "command-templates"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "specify.md").write_text("# override\n", encoding="utf-8")

    expected = AgentCommandInstallResult(agent_key="claude", mode="override-local")
    monkeypatch.setattr("specify_cli.runtime.agent_commands._render_override_commands", lambda project, agent: expected)

    result = install_project_commands_for_agent(tmp_path, "claude")

    assert result is expected


def test_install_project_commands_dispatches_codex_to_legacy_retirement(tmp_path: Path, monkeypatch) -> None:
    expected = AgentCommandInstallResult(agent_key="codex", mode="legacy-retired")
    monkeypatch.setattr("specify_cli.runtime.agent_commands.retire_legacy_codex_prompts", lambda project: expected)

    result = install_project_commands_for_agent(tmp_path, "codex")

    assert result is expected


def test_install_project_commands_returns_unsupported_for_unknown_agent(tmp_path: Path) -> None:
    result = install_project_commands_for_agent(tmp_path, "unknown-agent")
    assert result.mode == "unsupported"


def test_retire_legacy_codex_prompts_archives_and_removes_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    legacy_file = project / ".codex" / "prompts" / "spec-kitty.plan.md"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text("# stale codex prompt\n", encoding="utf-8")

    result = retire_legacy_codex_prompts(project)

    assert result.mode == "legacy-retired"
    assert legacy_file in result.files_removed
    assert not legacy_file.exists()
    assert not (project / ".codex" / "prompts").exists()

    backup_root = project / ".kittify" / ".migration-backup" / "agent-commands"
    archived = list(backup_root.rglob("spec-kitty.plan.md"))
    assert len(archived) == 1
