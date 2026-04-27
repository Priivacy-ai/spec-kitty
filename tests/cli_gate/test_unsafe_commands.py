"""Unsafe-command matrix tests (WP08 / T033).

Verifies that the gate blocks unsafe commands against incompatible project
states with the correct exit codes:

  Exit 4 — BLOCK_PROJECT_MIGRATION  (stale project, unsafe command)
  Exit 5 — BLOCK_CLI_UPGRADE        (too-new project, unsafe command)
  Exit 6 — BLOCK_PROJECT_CORRUPT    (corrupt metadata, any command)

Tests invoke ``check_schema_version`` directly (not the full Typer app) to
keep the suite fast and focused on gate semantics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.migration.gate import check_schema_version

# ---------------------------------------------------------------------------
# Representative unsafe-command list
# Commands that are NOT in the SAFETY_REGISTRY → classified as UNSAFE.
# ---------------------------------------------------------------------------

_UNSAFE_COMMANDS: list[str] = [
    "next",
    "merge",
    "accept",
    "review",
    "tasks",
    "specify",
    "plan",
]

# ---------------------------------------------------------------------------
# Exit-code constants (mirrors _EXIT_CODE_MAP in compat.planner)
# ---------------------------------------------------------------------------

_EXIT_STALE = 4  # BLOCK_PROJECT_MIGRATION
_EXIT_TOO_NEW = 5  # BLOCK_CLI_UPGRADE
_EXIT_CORRUPT = 6  # BLOCK_PROJECT_CORRUPT


# ---------------------------------------------------------------------------
# Tests — stale project (BLOCK_PROJECT_MIGRATION, exit 4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", _UNSAFE_COMMANDS)
def test_unsafe_command_stale_project_exits_4(
    subcommand: str,
    fixture_project_stale: Path,
) -> None:
    """Unsafe command on a stale project must exit 4 (BLOCK_PROJECT_MIGRATION).

    The gate renders the human message to stderr before raising SystemExit.
    """
    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(fixture_project_stale, invoked_subcommand=subcommand)

    assert exc_info.value.code == _EXIT_STALE, (
        f"Expected exit code {_EXIT_STALE} (BLOCK_PROJECT_MIGRATION), got {exc_info.value.code!r} for subcommand={subcommand!r}"
    )


# ---------------------------------------------------------------------------
# Tests — too-new project (BLOCK_CLI_UPGRADE, exit 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", _UNSAFE_COMMANDS)
def test_unsafe_command_too_new_project_exits_5(
    subcommand: str,
    fixture_project_too_new: Path,
) -> None:
    """Unsafe command on a too-new project must exit 5 (BLOCK_CLI_UPGRADE)."""
    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(fixture_project_too_new, invoked_subcommand=subcommand)

    assert exc_info.value.code == _EXIT_TOO_NEW, (
        f"Expected exit code {_EXIT_TOO_NEW} (BLOCK_CLI_UPGRADE), got {exc_info.value.code!r} for subcommand={subcommand!r}"
    )


# ---------------------------------------------------------------------------
# Tests — corrupt project (BLOCK_PROJECT_CORRUPT, exit 6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", _UNSAFE_COMMANDS)
def test_unsafe_command_corrupt_project_exits_6(
    subcommand: str,
    fixture_project_corrupt: Path,
) -> None:
    """Unsafe command on a corrupt project must exit 6 (BLOCK_PROJECT_CORRUPT)."""
    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(fixture_project_corrupt, invoked_subcommand=subcommand)

    assert exc_info.value.code == _EXIT_CORRUPT, (
        f"Expected exit code {_EXIT_CORRUPT} (BLOCK_PROJECT_CORRUPT), got {exc_info.value.code!r} for subcommand={subcommand!r}"
    )


# ---------------------------------------------------------------------------
# Tests — message content assertions
# ---------------------------------------------------------------------------


def test_stale_block_message_contains_upgrade_hint(
    fixture_project_stale: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Block message for stale project must mention the upgrade command."""
    with pytest.raises(SystemExit):
        check_schema_version(fixture_project_stale, invoked_subcommand="next")

    # Gate writes to stderr via typer.echo(err=True)
    captured = capsys.readouterr()
    stderr = captured.err
    assert "spec-kitty upgrade" in stderr, f"Expected 'spec-kitty upgrade' in stderr, got: {stderr!r}"


def test_too_new_block_message_contains_upgrade_cli_hint(
    fixture_project_too_new: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Block message for too-new project must mention upgrading the CLI."""
    with pytest.raises(SystemExit):
        check_schema_version(fixture_project_too_new, invoked_subcommand="next")

    captured = capsys.readouterr()
    stderr = captured.err
    assert "Upgrade the CLI" in stderr or "Upgrade" in stderr, f"Expected upgrade-CLI hint in stderr, got: {stderr!r}"
