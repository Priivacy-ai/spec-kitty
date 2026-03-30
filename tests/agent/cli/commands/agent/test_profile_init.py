"""Tests for `spec-kitty agent profile init` command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.profile import app
import pytest
pytestmark = pytest.mark.fast



runner = CliRunner()


def _write_profile(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_tool_config(repo_root: Path, key: str = "tools") -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        f"{key}:\n  available:\n    - codex\n",
        encoding="utf-8",
    )


def test_profile_init_writes_tool_context(tmp_path: Path, monkeypatch) -> None:
    project_profiles = tmp_path / ".kittify" / "constitution" / "agents"
    _write_profile(
        project_profiles / "my-impl.agent.yaml",
        """profile-id: my-impl
name: My Impl
purpose: Implement features
role: implementer
specialization:
  primary-focus: implementation
""",
    )
    _write_tool_config(tmp_path)

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init", "my-impl", "--project-dir", str(project_profiles)])
    assert result.exit_code == 0, result.output

    context_file = tmp_path / ".codex" / "prompts" / "spec-kitty.profile-context.md"
    assert context_file.exists()
    content = context_file.read_text(encoding="utf-8")
    assert "profile_id: my-impl" in content


def test_profile_init_missing_profile_fails(tmp_path: Path, monkeypatch) -> None:
    project_profiles = tmp_path / ".kittify" / "constitution" / "agents"
    project_profiles.mkdir(parents=True, exist_ok=True)
    _write_tool_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init", "does-not-exist", "--project-dir", str(project_profiles)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_profile_init_uses_inherited_mode_defaults(tmp_path: Path, monkeypatch) -> None:
    project_profiles = tmp_path / ".kittify" / "constitution" / "agents"
    _write_profile(
        project_profiles / "base.agent.yaml",
        """profile-id: base
name: Base
purpose: Base profile
role: implementer
specialization:
  primary-focus: base
mode-defaults:
  - mode: analysis
    description: Analyze
    use-case: planning
""",
    )
    _write_profile(
        project_profiles / "child.agent.yaml",
        """profile-id: child
name: Child
purpose: Child profile
role: implementer
specializes-from: base
specialization:
  primary-focus: child
""",
    )
    _write_tool_config(tmp_path, key="agents")  # legacy fallback
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init", "child", "--project-dir", str(project_profiles)])
    assert result.exit_code == 0, result.output

    context_file = tmp_path / ".codex" / "prompts" / "spec-kitty.profile-context.md"
    content = context_file.read_text(encoding="utf-8")
    assert "mode_defaults: analysis" in content
