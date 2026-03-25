"""ATDD acceptance tests for issue #241: --mission → --mission-type rename on type-selection commands.

Covers 5 commands that previously accepted --mission for *type* selection
(lifecycle specify, config, constitution interview/generate/generate-for-agent).

For each command the tests verify:
- --mission-type is the new canonical flag (visible in --help)
- --mission is hidden (not shown in --help)
- Passing --mission raises a hard error (exit code 1) with a clear message
- resolve_mission_type utility raises Exit(1) on the legacy flag
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

import pytest

_WORKTREE_SRC = str(Path(__file__).parents[4] / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run spec-kitty CLI via its module entry-point."""
    env = os.environ.copy()
    env["PYTHONPATH"] = _WORKTREE_SRC + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "specify_cli.__main__", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _help(*subcommand: str) -> subprocess.CompletedProcess[str]:
    return _run_cli(*subcommand, "--help")


# ---------------------------------------------------------------------------
# Unit tests: resolve_mission_type utility
# ---------------------------------------------------------------------------


def test_resolve_mission_type_canonical_flag_wins() -> None:
    """resolve_mission_type returns mission_type when --mission-type given."""
    from specify_cli.cli.commands._flag_utils import resolve_mission_type

    result = resolve_mission_type("software-dev", None)
    assert result == "software-dev"


def test_resolve_mission_type_none_when_neither() -> None:
    """resolve_mission_type returns None when neither flag given."""
    from specify_cli.cli.commands._flag_utils import resolve_mission_type

    result = resolve_mission_type(None, None)
    assert result is None


def test_resolve_mission_type_legacy_raises_exit() -> None:
    """resolve_mission_type raises typer.Exit(1) when the removed --mission alias is used."""
    import click
    from specify_cli.cli.commands._flag_utils import resolve_mission_type

    with pytest.raises((SystemExit, click.exceptions.Exit)) as exc_info:
        resolve_mission_type(None, "research")
    # click.exceptions.Exit uses .exit_code; SystemExit uses .code
    exc = exc_info.value
    exit_code = getattr(exc, "exit_code", None) or getattr(exc, "code", None)
    assert exit_code == 1, f"Expected exit code 1, got {exit_code}"


# ---------------------------------------------------------------------------
# CLI help output: --mission-type must be visible, --mission must be hidden
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subcommand",
    [
        ["specify"],
        ["config"],
        ["constitution", "interview"],
        ["constitution", "generate"],
        ["constitution", "generate-for-agent"],
    ],
    ids=["specify", "config", "constitution-interview", "constitution-generate", "constitution-generate-for-agent"],
)
def test_mission_type_flag_visible_in_help(subcommand: list[str]) -> None:
    """--mission-type must appear in the command's --help output."""
    result = _help(*subcommand)
    assert "--mission-type" in result.stdout, (
        f"--mission-type not found in `spec-kitty {' '.join(subcommand)} --help`.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.parametrize(
    "subcommand",
    [
        ["specify"],
        ["config"],
        ["constitution", "interview"],
        ["constitution", "generate"],
        ["constitution", "generate-for-agent"],
    ],
    ids=["specify", "config", "constitution-interview", "constitution-generate", "constitution-generate-for-agent"],
)
def test_mission_flag_hidden_in_help(subcommand: list[str]) -> None:
    """--mission must NOT appear in the command's --help output (hidden=True)."""
    result = _help(*subcommand)
    # Filter out lines that are sub-command names (e.g. "mission" in "spec-kitty mission")
    # We specifically check for the option flag --mission (with leading dashes).
    assert "--mission " not in result.stdout and "--mission\n" not in result.stdout, (
        f"--mission (as flag) should be hidden but is still visible in `spec-kitty {' '.join(subcommand)} --help`.\nstdout:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# CLI runtime: passing the removed --mission flag must exit 1 with clear error
# ---------------------------------------------------------------------------


def test_config_mission_legacy_flag_errors() -> None:
    """spec-kitty config --mission <type> must exit 1 with a clear error message."""
    result = _run_cli("config", "--mission", "software-dev", "--show-origin")
    assert result.returncode == 1, (
        f"Expected exit code 1 when --mission used on config, got {result.returncode}.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "--mission-type" in combined, f"Error message should mention --mission-type but got:\n{combined}"


def test_constitution_interview_mission_legacy_flag_errors() -> None:
    """spec-kitty constitution interview --mission <type> must exit 1."""
    result = _run_cli("constitution", "interview", "--mission", "software-dev", "--defaults")
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "--mission-type" in combined, f"Error message should mention --mission-type but got:\n{combined}"
