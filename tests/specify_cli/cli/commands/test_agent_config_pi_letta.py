"""Integration tests for agent config add/remove pi and letta."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.config import app
from specify_cli.core.agent_config import AgentConfig, load_agent_config, save_agent_config
from specify_cli.skills import command_installer, manifest_store

pytestmark = [pytest.mark.integration, pytest.mark.non_sandbox]
runner = CliRunner()


def _write_config(tmp_path: Path, agents: list[str]) -> None:
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)
    save_agent_config(tmp_path, AgentConfig(available=agents))


@pytest.mark.parametrize("agent_key", ["pi", "letta"])
def test_add_pi_letta_updates_config_and_installs_skills(
    tmp_path: Path, agent_key: str
) -> None:
    _write_config(tmp_path, [])

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["add", agent_key])

    assert result.exit_code == 0, result.output
    config = load_agent_config(tmp_path)
    assert agent_key in config.available

    manifest = manifest_store.load(tmp_path)
    assert len(manifest.entries) == len(command_installer.CANONICAL_COMMANDS)
    for entry in manifest.entries:
        assert entry.agents == (agent_key,)


@pytest.mark.parametrize("agent_key", ["pi", "letta"])
def test_remove_pi_letta_removes_skill_claims(tmp_path: Path, agent_key: str) -> None:
    _write_config(tmp_path, [agent_key])
    command_installer.install(tmp_path, agent_key)

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["remove", agent_key])

    assert result.exit_code == 0, result.output
    config = load_agent_config(tmp_path)
    assert agent_key not in config.available
    assert manifest_store.load(tmp_path).entries == []


def test_sync_create_missing_reinstalls_codex_command_skills(tmp_path: Path) -> None:
    _write_config(tmp_path, ["codex"])

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["sync", "--create-missing"])

    assert result.exit_code == 0, result.output
    assert "Unknown agent: codex" not in result.output

    manifest = manifest_store.load(tmp_path)
    assert len(manifest.entries) == len(command_installer.CANONICAL_COMMANDS)
    for entry in manifest.entries:
        assert entry.agents == ("codex",)
        assert (tmp_path / entry.path).is_file()
