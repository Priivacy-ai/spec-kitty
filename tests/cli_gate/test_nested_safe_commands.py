"""FIX 2 regression tests — nested safe agent commands not blocked under schema mismatch.

Before FIX 2, check_schema_version built the Invocation command_path from only
``ctx.invoked_subcommand`` (one token), so ``spec-kitty agent mission branch-context``
reached the planner as ``("agent",)`` which is NOT in SAFETY_REGISTRY, causing
a fail-closed UNSAFE → block even though the full path is explicitly registered.

After FIX 2, _build_command_path() reads sys.argv[1:] to produce the full path
tuple, and the safety registry correctly matches the nested safe commands.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.migration.gate import _build_command_path, check_schema_version


# ---------------------------------------------------------------------------
# Unit tests for _build_command_path()
# ---------------------------------------------------------------------------


class TestBuildCommandPath:
    def test_nested_command_with_flag(self) -> None:
        """Nested command path stops at first flag; argv agrees with invoked_subcommand."""
        with patch.object(sys, "argv", ["spec-kitty", "agent", "mission", "branch-context", "--json"]):
            assert _build_command_path("agent") == ("agent", "mission", "branch-context")

    def test_simple_command(self) -> None:
        with patch.object(sys, "argv", ["spec-kitty", "upgrade"]):
            assert _build_command_path("upgrade") == ("upgrade",)

    def test_flag_only_invocation_falls_back(self) -> None:
        """When argv has only flags, falls back to invoked_subcommand."""
        with patch.object(sys, "argv", ["spec-kitty", "--help"]):
            assert _build_command_path("dashboard") == ("dashboard",)

    def test_no_args_no_subcommand(self) -> None:
        with patch.object(sys, "argv", ["spec-kitty"]):
            assert _build_command_path(None) == ()

    def test_three_level_no_flags(self) -> None:
        with patch.object(sys, "argv", ["spec-kitty", "agent", "context", "resolve"]):
            assert _build_command_path("agent") == ("agent", "context", "resolve")

    def test_stops_before_short_flag(self) -> None:
        with patch.object(sys, "argv", ["spec-kitty", "agent", "tasks", "status", "-q"]):
            assert _build_command_path("agent") == ("agent", "tasks", "status")

    def test_argv_mismatch_falls_back_to_invoked_subcommand(self) -> None:
        """When argv[1] disagrees (pytest context), falls back to invoked_subcommand."""
        with patch.object(sys, "argv", ["/usr/bin/pytest", "tests/cli_gate/foo.py"]):
            assert _build_command_path("dashboard") == ("dashboard",)
            assert _build_command_path("status") == ("status",)

    def test_no_invoked_subcommand_no_argv_subcommand(self) -> None:
        """No subcommand in either sys.argv or invoked_subcommand → empty tuple."""
        with patch.object(sys, "argv", ["spec-kitty", "--version"]):
            assert _build_command_path(None) == ()


# ---------------------------------------------------------------------------
# Integration: nested safe commands must not be blocked under TOO_NEW project
# ---------------------------------------------------------------------------

_NESTED_SAFE_COMMANDS = [
    # (argv_tail, human_label)
    (["agent", "mission", "branch-context"], "agent_mission_branch-context"),
    (["agent", "mission", "check-prerequisites"], "agent_mission_check-prerequisites"),
    (["agent", "mission", "setup-plan"], "agent_mission_setup-plan"),
    (["agent", "context", "resolve"], "agent_context_resolve"),
    (["agent", "tasks", "status"], "agent_tasks_status"),
]


@pytest.mark.parametrize(
    "argv_tail",
    [args for args, _ in _NESTED_SAFE_COMMANDS],
    ids=[label for _, label in _NESTED_SAFE_COMMANDS],
)
def test_nested_safe_command_not_blocked_by_too_new_project(
    argv_tail: list[str],
    fixture_project_too_new: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested safe agent commands must pass gate even when schema is too new.

    Regression: previously the gate sent only the top-level subcommand ('agent')
    to the planner, which is NOT in SAFETY_REGISTRY, causing a block. FIX 2
    sends the full path so registry lookup matches.
    """
    monkeypatch.setattr(sys, "argv", ["spec-kitty"] + argv_tail)
    # Must NOT raise SystemExit.
    check_schema_version(fixture_project_too_new, invoked_subcommand=argv_tail[0])


@pytest.mark.parametrize(
    "argv_tail",
    [args for args, _ in _NESTED_SAFE_COMMANDS],
    ids=[label for _, label in _NESTED_SAFE_COMMANDS],
)
def test_nested_safe_command_not_blocked_by_stale_project(
    argv_tail: list[str],
    fixture_project_stale: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested safe agent commands must pass gate on stale project too."""
    monkeypatch.setattr(sys, "argv", ["spec-kitty"] + argv_tail)
    check_schema_version(fixture_project_stale, invoked_subcommand=argv_tail[0])
