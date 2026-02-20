from __future__ import annotations

import io
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from rich.console import Console

from tests.branch_contract import IS_2X_BRANCH, LEGACY_0X_ONLY_REASON
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command
from specify_cli.core.vcs import VCSBackend


@pytest.fixture()
def cli_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Typer, Console, list[str]]:
    console = Console(file=io.StringIO(), force_terminal=False)
    outputs: list[str] = []
    app = Typer()

    def fake_show_banner():  # noqa: D401
        outputs.append("banner")

    def fake_activate(project_path: Path, mission_key: str, mission_display: str, _console: Console) -> str:
        outputs.append(f"activate:{mission_key}")
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
    monkeypatch.setattr(init_module, "ensure_dashboard_running", lambda project: ("http://localhost", 1111, True))
    monkeypatch.setattr(init_module, "check_tool", lambda *args, **kwargs: True)
    return app, console, outputs


def _invoke(cli: Typer, args: list[str]) -> CliRunner:
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    if result.exit_code != 0:
        raise AssertionError(result.output)
    return runner


@pytest.mark.skipif(IS_2X_BRANCH, reason=LEGACY_0X_ONLY_REASON)
def test_init_local_mode_uses_local_repo(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):  # noqa: D401
        return override_path or tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):  # noqa: D401
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    created_assets: list[Path] = []

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):  # noqa: D401
        target = project_path / f".{agent_key}" / f"run.{script}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(agent_key, encoding="utf-8")
        created_assets.append(target)

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    _invoke(
        app,
        [
            "init",
            "demo",
            "--ai",
            "claude",
            "--script",
            "sh",
            "--no-git",
            "--non-interactive",
        ],
    )

    project_path = tmp_path / "demo"
    assert project_path.exists()
    assert created_assets
    assert any(p.read_text(encoding="utf-8") == "claude" for p in created_assets)
    assert "activate:software-dev" in outputs


def test_init_package_mode_falls_back_when_no_local(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(init_module, "get_local_repo_root", lambda override_path=None: None)

    def fake_copy(project_path: Path, script: str):  # noqa: D401
        pkg_dir = project_path / ".pkg"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return pkg_dir

    generated: list[str] = []

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):  # noqa: D401
        generated.append(agent_key)

    monkeypatch.setattr(init_module, "copy_specify_base_from_package", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    _invoke(
        app,
        [
            "init",
            "pkg-demo",
            "--ai",
            "gemini",
            "--script",
            "ps",
            "--no-git",
            "--non-interactive",
        ],
    )

    assert generated == ["gemini"]


def test_init_remote_mode_downloads_for_each_agent(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(init_module, "get_local_repo_root", lambda override_path=None: None)

    calls: list[tuple[str, str, bool]] = []

    skip_flags: list[bool] = []

    class DummyClient:
        def close(self):  # noqa: D401
            calls.append(("close", "", False))

    def fake_client(skip_tls: bool = False):  # noqa: D401
        skip_flags.append(skip_tls)
        return DummyClient()

    monkeypatch.setattr(init_module, "build_http_client", fake_client)

    def fake_download(project_path: Path, agent_key: str, script: str, is_current_dir: bool, **kwargs):  # noqa: D401
        calls.append((agent_key, kwargs.get("repo_owner"), kwargs.get("repo_name"), is_current_dir))
        (project_path / f"agent-{agent_key}").mkdir(parents=True, exist_ok=True)
        return project_path

    monkeypatch.setattr(init_module, "download_and_extract_template", fake_download)

    monkeypatch.setenv("SPECIFY_TEMPLATE_REPO", "octo/spec-kit")

    _invoke(
        app,
        [
            "init",
            "remote-demo",
            "--ai",
            "claude,gemini",
            "--script",
            "sh",
            "--skip-tls",
            "--no-git",
            "--non-interactive",
        ],
    )

    agent_calls = [c for c in calls if c[0] in {"claude", "gemini"}]
    assert len(agent_calls) == 2
    assert {owner for _, owner, _, _ in agent_calls} == {"octo"}
    assert {repo for _, _, repo, _ in agent_calls} == {"spec-kit"}
    assert skip_flags == [True]
    monkeypatch.delenv("SPECIFY_TEMPLATE_REPO", raising=False)


# =============================================================================
# VCS Detection and Configuration Tests
# =============================================================================


def test_init_with_jj_shows_confirmation(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Init should show 'git detected' message (jj no longer supported)."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        pass

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    # Git available (jj support removed)
    with patch.object(init_module, "is_git_available", return_value=True):
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "init",
                "git-project",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--non-interactive",
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    # Check the Rich console output (not CliRunner output)
    console_output = console.file.getvalue()
    assert "git detected" in console_output


def test_init_without_jj_shows_recommendation(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Init should work with git (jj no longer supported)."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        pass

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    # Git available (jj support removed)
    with patch.object(init_module, "is_git_available", return_value=True):
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "init",
                "git-project",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--non-interactive",
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    # Check the Rich console output (not CliRunner output)
    console_output = console.file.getvalue()
    assert "git detected" in console_output


def test_init_creates_vcs_config(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Init should create config.yaml with git vcs section."""
    app, console, outputs = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        pass

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    # Git available (jj support removed)
    with patch.object(init_module, "is_git_available", return_value=True):
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "init",
                "config-project",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
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


def test_init_non_interactive_requires_force_for_nonempty_here(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)
    (tmp_path / "existing.txt").write_text("data", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "--here",
            "--ai",
            "claude",
            "--script",
            "sh",
            "--no-git",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 1
    console_output = console.file.getvalue()
    assert "Non-interactive mode requires --force when using --here" in console_output


def test_init_non_interactive_env_var(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, _, _ = cli_app
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        (project_path / f".{agent_key}" / f"run.{script}").parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "env-non-interactive",
            "--ai",
            "claude",
            "--script",
            "sh",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, result.output


def test_init_amends_initial_commit_after_cleanup(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Fresh git init should end in a clean amended initial commit."""
    app, _, _ = cli_app
    monkeypatch.chdir(tmp_path)

    def fake_local_repo(override_path=None):
        return tmp_path / "templates"

    def fake_copy(local_repo: Path, project_path: Path, script: str):
        (project_path / ".kittify" / "templates").mkdir(parents=True, exist_ok=True)
        commands_dir = project_path / ".templates"
        commands_dir.mkdir(parents=True, exist_ok=True)
        return commands_dir

    def fake_assets(commands_dir: Path, project_path: Path, agent_key: str, script: str):
        (project_path / f".{agent_key}" / f"run.{script}").parent.mkdir(parents=True, exist_ok=True)

    def fake_init_git_repo(project_path: Path, quiet: bool = False, console=None):
        (project_path / ".git").mkdir(parents=True, exist_ok=True)
        return True

    git_calls: list[list[str]] = []

    def fake_subprocess_run(cmd, **kwargs):
        git_calls.append(list(cmd))
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(init_module, "get_local_repo_root", fake_local_repo)
    monkeypatch.setattr(init_module, "copy_specify_base_from_local", fake_copy)
    monkeypatch.setattr(init_module, "generate_agent_assets", fake_assets)
    monkeypatch.setattr(init_module, "init_git_repo", fake_init_git_repo)
    monkeypatch.setattr(init_module, "is_git_repo", lambda path: (path / ".git").exists())
    monkeypatch.setattr(init_module.subprocess, "run", fake_subprocess_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "git-clean-demo",
            "--ai",
            "codex",
            "--script",
            "sh",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    assert any(call[:4] == ["git", "commit", "--amend", "--no-edit"] for call in git_calls)


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


def test_init_non_interactive_preferred_agent_not_selected(cli_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app, console, _ = cli_app
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "bad-preferred",
            "--ai",
            "codex",
            "--preferred-implementer",
            "gemini",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 1
    console_output = console.file.getvalue()
    assert "Preferred implementer must be one of the selected agents" in console_output
