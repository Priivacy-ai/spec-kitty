"""Scope: init command unit tests — no real git or subprocesses."""

from __future__ import annotations

import io
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from rich.console import Console

from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command

pytestmark = pytest.mark.fast


@pytest.fixture()
def cli_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Typer, Console, list[str]]:
    console = Console(file=io.StringIO(), force_terminal=False)
    outputs: list[str] = []
    app = Typer()

    def fake_show_banner():  # noqa: D401
        outputs.append("banner")

    def fake_activate(project_path: Path, mission_type: str, mission_display: str, _console: Console) -> str:
        outputs.append(f"activate:{mission_type}")
        return mission_display

    def fake_ensure_scripts(path: Path, tracker=None):  # noqa: D401
        outputs.append(f"scripts:{path}")

    register_init_command(
        app,
        console=console,
        show_banner=fake_show_banner,
        activate_mission=fake_activate,
        ensure_executable_scripts=fake_ensure_scripts,
    )
    return app, console, outputs


def _invoke(cli: Typer, args: list[str]) -> CliRunner:
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    if result.exit_code != 0:
        raise AssertionError(result.output)
    return runner


# =============================================================================
# VCS Detection and Configuration Tests
# =============================================================================


def test_init_creates_vcs_config(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Init should create config.yaml with git vcs section."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)

    # Git available
    with patch.object(init_module, "is_git_available", return_value=True):
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "init",
                "config-project",
                "--ai",
                "claude",
                "--non-interactive",
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Check config.yaml was created
    config_file = tmp_path / "config-project" / ".kittify" / "config.yaml"
    assert config_file.exists(), f"Config file not found at {config_file}"

    config = yaml.safe_load(config_file.read_text())
    assert "vcs" in config
    assert config["vcs"]["type"] == "git"


def test_init_non_interactive_requires_ai(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "missing-ai",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 1
    console_output = console.file.getvalue()
    assert "--ai is required in non-interactive mode" in console_output


def test_init_non_interactive_no_project_name_defaults_to_current_directory(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "--ai",
            "claude",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".templates").exists()
    console_output = console.file.getvalue()
    assert "Target Path" not in console_output


def test_init_non_interactive_env_var(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, _, _ = cli_app
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "env-non-interactive",
            "--ai",
            "claude",
        ],
    )
    assert result.exit_code == 0, result.output


def test_init_writes_event_log_merge_attributes(
    cli_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    app, _, _ = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "event-log-project",
            "--ai",
            "claude",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0, result.output
    attributes = (tmp_path / "event-log-project" / ".gitattributes").read_text(encoding="utf-8")
    assert "kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log" in attributes


# test_init_amends_initial_commit_after_cleanup deleted in feature 076:
# the initial git commit block was removed from init.py.


def test_init_rejects_removed_agent_strategy_option(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, _, _ = cli_app
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "bad-strategy-option",
            "--ai",
            "codex",
            "--agent-strategy",
            "random",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 2
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert re.search(r"No such option:\s+-{1,2}agent-strategy", plain_output)
