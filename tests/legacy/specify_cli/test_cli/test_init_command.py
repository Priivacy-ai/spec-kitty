from __future__ import annotations

from pathlib import Path

import pytest

from tests.specify_cli.test_cli.test_init_command import _invoke, cli_app
from specify_cli.cli.commands import init as init_module


def test_init_local_mode_uses_local_repo(
    cli_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    app, _console, outputs = cli_app
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
