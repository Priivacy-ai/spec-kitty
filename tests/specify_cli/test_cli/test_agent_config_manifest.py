"""Tests for keeping the skills manifest in sync with agent config commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.config import app
from specify_cli.core.agent_config import AgentConfig, save_agent_config
from specify_cli.skills.manifest import (
    ManagedFile,
    SkillsManifest,
    load_manifest,
    write_manifest,
)
from specify_cli.skills.verification import verify_installation

runner = CliRunner()


def _write_manifest(
    repo_root: Path,
    *,
    selected_agents: list[str],
    managed_files: list[ManagedFile] | None = None,
) -> None:
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T16:00:00Z",
        updated_at="2026-03-20T16:00:00Z",
        skills_mode="auto",
        selected_agents=selected_agents,
        installed_skill_roots=[],
        managed_files=managed_files or [],
    )
    write_manifest(repo_root, manifest)


def test_add_updates_manifest_for_wrapper_only_agent(tmp_path: Path) -> None:
    """Adding Amazon Q tracks its wrappers so verification keeps passing."""
    save_agent_config(tmp_path, AgentConfig(available=[]))
    (tmp_path / ".kittify" / "missions" / "software-dev" / "command-templates").mkdir(parents=True)
    (tmp_path / ".kittify" / "missions" / "software-dev" / "command-templates" / "specify.md").write_text(
        "body",
        encoding="utf-8",
    )
    _write_manifest(tmp_path, selected_agents=[])

    with patch(
        "specify_cli.cli.commands.agent.config.find_repo_root",
        return_value=tmp_path,
    ):
        result = runner.invoke(app, ["add", "q"])

    assert result.exit_code == 0

    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert manifest.selected_agents == ["q"]
    wrapper_paths = [mf.path for mf in manifest.managed_files if mf.file_type == "wrapper"]
    assert wrapper_paths == [".amazonq/prompts/spec-kitty.specify.md"]

    verification = verify_installation(tmp_path, ["q"], manifest)
    assert verification.passed is True


def test_remove_prunes_manifest_for_removed_agent(tmp_path: Path) -> None:
    """Removing an agent also removes its manifest tracking entries."""
    save_agent_config(tmp_path, AgentConfig(available=["q"]))
    wrapper_dir = tmp_path / ".amazonq" / "prompts"
    wrapper_dir.mkdir(parents=True)
    wrapper_file = wrapper_dir / "spec-kitty.specify.md"
    wrapper_file.write_text("body", encoding="utf-8")
    _write_manifest(
        tmp_path,
        selected_agents=["q"],
        managed_files=[
            ManagedFile(
                path=".amazonq/prompts/spec-kitty.specify.md",
                sha256="placeholder",
                file_type="wrapper",
            )
        ],
    )

    with patch(
        "specify_cli.cli.commands.agent.config.find_repo_root",
        return_value=tmp_path,
    ):
        result = runner.invoke(app, ["remove", "q"])

    assert result.exit_code == 0
    assert not (tmp_path / ".amazonq").exists()

    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert manifest.selected_agents == []
    assert manifest.managed_files == []
