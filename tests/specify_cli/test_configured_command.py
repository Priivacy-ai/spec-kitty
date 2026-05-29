"""Tests for user-configured command execution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.configured_command import (
    ConfiguredCommandUnsupported,
    run_configured_command,
    run_configured_command_template,
)

pytestmark = pytest.mark.fast


def _completed() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def test_simple_posix_command_uses_explicit_sh_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    command = 'runner --flag "two words"'

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command(command, cwd=tmp_path)
    args, kwargs = run.call_args

    assert args[0] == ["sh", "-c", command]
    assert "shell" not in kwargs


def test_posix_shell_syntax_uses_explicit_sh_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    command = "echo start && echo done"

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command(command, cwd=tmp_path)

    args, kwargs = run.call_args
    assert args[0] == ["sh", "-c", command]
    assert "shell" not in kwargs


def test_quoted_command_substitution_uses_explicit_sh_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    command = 'test -z "$(printf \'\')"'

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command(command, cwd=tmp_path)

    args, kwargs = run.call_args
    assert args[0] == ["sh", "-c", command]
    assert "shell" not in kwargs


@pytest.mark.parametrize("command", ["! grep forbidden file.txt", "test -e *.py"])
def test_other_posix_shell_forms_use_explicit_sh_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: str,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command(command, cwd=tmp_path)

    args, kwargs = run.call_args
    assert args[0] == ["sh", "-c", command]
    assert "shell" not in kwargs


def test_simple_windows_command_uses_native_string_without_shell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    command = 'python -m pytest --junitxml="C:\\tmp\\junit.xml"'

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command(command, cwd=tmp_path)

    args, kwargs = run.call_args
    assert args[0] == command
    assert "shell" not in kwargs


def test_windows_posix_shell_syntax_fails_before_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    with (
        patch("specify_cli.configured_command.subprocess.run") as run,
        pytest.raises(ConfiguredCommandUnsupported, match="POSIX shell syntax"),
    ):
        run_configured_command("echo start && echo done", cwd=tmp_path)

    run.assert_not_called()


def test_template_substitution_is_shell_quoted_on_posix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    output_file = tmp_path / "tmp;touch proof #" / "junit.xml"

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command_template(
            "runner --junitxml={output_file}",
            {"output_file": output_file},
            cwd=tmp_path,
        )

    args, kwargs = run.call_args
    assert args[0] == ["sh", "-c", 'runner --junitxml="${SPEC_KITTY_CMD_OUTPUT_FILE}"']
    assert "shell" not in kwargs
    assert kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"] == str(output_file)


def test_quoted_template_placeholder_uses_env_without_double_quoting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    output_file = tmp_path / "parent with space" / "junit.xml"

    with patch("specify_cli.configured_command.subprocess.run", return_value=_completed()) as run:
        run_configured_command_template(
            'runner --junitxml="{output_file}"',
            {"output_file": output_file},
            cwd=tmp_path,
        )

    args, kwargs = run.call_args
    assert args[0] == ["sh", "-c", 'runner --junitxml="${SPEC_KITTY_CMD_OUTPUT_FILE}"']
    assert kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"] == str(output_file)
