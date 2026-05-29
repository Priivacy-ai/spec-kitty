"""Doctor coverage for command-skill manifest drift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.doctor as doctor_mod
from specify_cli.cli.commands.doctor import app
from specify_cli.skills import command_installer, manifest_store

pytestmark = [pytest.mark.unit]

runner = CliRunner()


def _write_config(repo_root: Path, *agents: str) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    lines = ["agents:", "  available:"]
    lines.extend(f"    - {agent}" for agent in agents)
    (kittify / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _invoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *args: str,
):
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
    return runner.invoke(app, ["skills", *args])


def _payload(output: str) -> dict[str, object]:
    return json.loads(output)


def test_skills_reports_missing_manifest_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, "codex")
    command_installer.install(tmp_path, "codex")

    deleted = tmp_path / ".agents" / "skills" / "spec-kitty.tasks" / "SKILL.md"
    deleted.unlink()

    result = _invoke(tmp_path, monkeypatch, "--json")

    assert result.exit_code == 1
    data = _payload(result.output)
    assert data["ok"] is False
    assert data["gaps"] == [".agents/skills/spec-kitty.tasks/SKILL.md"]
    assert data["uninstalled_agents"] == []


def test_skills_fix_repairs_partial_codex_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, "codex")
    command_installer.install(tmp_path, "codex")

    for command in command_installer.CANONICAL_COMMANDS:
        if command == "specify":
            continue
        skill_md = tmp_path / ".agents" / "skills" / f"spec-kitty.{command}" / "SKILL.md"
        skill_md.unlink()

    result = _invoke(tmp_path, monkeypatch, "--fix", "--json")

    assert result.exit_code == 0
    data = _payload(result.output)
    assert data["ok"] is True
    assert data["gaps"] == []
    assert data["entries"] == len(command_installer.CANONICAL_COMMANDS)
    manifest = manifest_store.load(tmp_path)
    assert len(manifest.entries) == len(command_installer.CANONICAL_COMMANDS)
    for command in command_installer.CANONICAL_COMMANDS:
        assert (
            tmp_path / ".agents" / "skills" / f"spec-kitty.{command}" / "SKILL.md"
        ).is_file()


def test_skills_fix_installs_configured_command_agent_without_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, "codex")

    before = _invoke(tmp_path, monkeypatch, "--json")
    assert before.exit_code == 1
    assert _payload(before.output)["uninstalled_agents"] == ["codex"]

    fixed = _invoke(tmp_path, monkeypatch, "--fix", "--json")

    assert fixed.exit_code == 0
    data = _payload(fixed.output)
    assert data["ok"] is True
    assert data["manifest_agents"] == ["codex"]
    assert data["entries"] == len(command_installer.CANONICAL_COMMANDS)


def test_skills_fix_refuses_when_managed_file_drifted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, "codex")
    command_installer.install(tmp_path, "codex")
    drifted = tmp_path / ".agents" / "skills" / "spec-kitty.specify" / "SKILL.md"
    drifted.write_text(
        drifted.read_text(encoding="utf-8") + "\n# local edit\n",
        encoding="utf-8",
    )
    missing = tmp_path / ".agents" / "skills" / "spec-kitty.tasks" / "SKILL.md"
    missing.unlink()

    result = _invoke(tmp_path, monkeypatch, "--fix", "--json")

    assert result.exit_code == 1
    data = _payload(result.output)
    assert data["gaps"] == [".agents/skills/spec-kitty.tasks/SKILL.md"]
    assert data["drift"] == [".agents/skills/spec-kitty.specify/SKILL.md"]
    assert data["repaired_agents"] == []
    assert data["repair_errors"] == [
        "Refusing --fix while managed skill files have edited-file drift."
    ]
    assert not missing.exists()
