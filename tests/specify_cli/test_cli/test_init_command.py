from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command


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
            "--mission",
            "software-dev",
            "--no-git",
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
            "--mission",
            "software-dev",
            "--no-git",
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
            "--mission",
            "software-dev",
            "--skip-tls",
            "--no-git",
        ],
    )

    agent_calls = [c for c in calls if c[0] in {"claude", "gemini"}]
    assert len(agent_calls) == 2
    assert {owner for _, owner, _, _ in agent_calls} == {"octo"}
    assert {repo for _, _, repo, _ in agent_calls} == {"spec-kit"}
    assert skip_flags == [True]
    monkeypatch.delenv("SPECIFY_TEMPLATE_REPO", raising=False)
