"""Integration tests for the spec-kitty lint command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

pytestmark = [pytest.mark.integration]

from typer.testing import CliRunner

import typer

from specify_cli.cli.commands import register_commands

@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture()
def app() -> typer.Typer:
    _app = typer.Typer()
    register_commands(_app)
    return _app

def test_lint_file_not_found(runner: CliRunner, app: typer.Typer, tmp_path: Path) -> None:
    """Ensure we handle missing files gracefully."""
    result = runner.invoke(app, ["lint", str(tmp_path / "404.py")])
    assert result.exit_code == 1
    assert "Error" in result.output

def test_lint_non_python_file(runner: CliRunner, app: typer.Typer, tmp_path: Path) -> None:
    """Ensure we skip non-python files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    result = runner.invoke(app, ["lint", str(test_file)])
    assert result.exit_code == 0
    assert "is not a Python file" in " ".join(result.output.split())

@patch("subprocess.run")
def test_lint_success_mock(mock_run: MagicMock, runner: CliRunner, app: typer.Typer, tmp_path: Path) -> None:
    """Verify success path with mocked subprocesses."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo(): pass")

    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    result = runner.invoke(app, ["lint", str(test_file)])
    assert result.exit_code == 0
    assert "passed all checks" in " ".join(result.output.split())

@patch("subprocess.run")
def test_lint_json_failure_mock(mock_run: MagicMock, runner: CliRunner, app: typer.Typer, tmp_path: Path) -> None:
    """Verify JSON error reporting."""
    test_file = tmp_path / "test.py"
    test_file.write_text("bad code")

    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="ruff error", stderr=""),
        MagicMock(returncode=1, stdout="mypy error", stderr="")
    ]

    result = runner.invoke(app, ["lint", str(test_file), "--json"])
    assert result.exit_code == 1

    data = json.loads(result.output)
    assert data["success"] is False
    assert data["ruff_errors"] == ["ruff error"]
    assert data["mypy_errors"] == ["mypy error"]

def test_lint_uses_spec_repo_root_as_cwd(
    runner: CliRunner, app: typer.Typer, tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """When SPECIFY_REPO_ROOT is set, lint_command uses it as cwd for subprocess calls.

    Regression guard for FR-007: locate_project_root() must honour the env-var
    override so that ruff/mypy run with the correct project root even when the
    process cwd is a worktree or unrelated directory.
    """
    project_root = tmp_path / "my_project"
    project_root.mkdir()
    (project_root / ".kittify").mkdir()

    test_file = tmp_path / "test.py"
    test_file.write_text("x: int = 1\n")

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(project_root))

    captured_cwds: list[Path] = []

    def fake_subprocess_run(
        args: list[str], *, cwd: Path, capture_output: bool, text: bool, check: bool
    ) -> MagicMock:
        captured_cwds.append(Path(cwd))
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("specify_cli.cli.commands.lint.subprocess.run", side_effect=fake_subprocess_run):
        result = runner.invoke(app, ["lint", str(test_file)])

    assert result.exit_code == 0, result.output
    # Both ruff and mypy calls must have used the SPECIFY_REPO_ROOT path as cwd.
    assert len(captured_cwds) == 2
    assert all(cwd == project_root for cwd in captured_cwds), (
        f"Expected cwd={project_root!r} for all subprocess calls; got {captured_cwds!r}"
    )


def test_lint_config_sync_idempotency(runner: CliRunner, app: typer.Typer, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Verify that sync_hooks handles the Claude settings.json correctly."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents: {available: [claude], lint_on_edit: true}")

    # Run sync
    result = runner.invoke(app, ["agent", "config", "sync", "--sync-hooks"])
    assert result.exit_code == 0

    claude_settings = tmp_path / ".claude" / "settings.json"
    assert claude_settings.exists()

    with open(claude_settings) as f:
        data = json.load(f)
        hooks = data["hooks"]["PostToolUse"]
        assert any(h["matcher"] == "Edit|Write" for h in hooks)
