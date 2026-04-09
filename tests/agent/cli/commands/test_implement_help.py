"""Regression tests for implement command --help output (T014 / FR-503).

Verifies that:
- ``spec-kitty implement --help`` marks the command as internal infrastructure.
- The help text names the canonical user-facing workflow commands.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app

pytestmark = pytest.mark.fast


@pytest.fixture
def runner() -> CliRunner:
    """Typer CLI runner for --help tests."""
    return CliRunner()


class TestImplementHelpContainsInternalMarker:
    """T6.1 (FR-503) — implement --help output must mark the command as internal."""

    def test_implement_help_exit_code_ok(self, runner: CliRunner) -> None:
        """implement --help must exit 0."""
        result = runner.invoke(cli_app, ["implement", "--help"])
        assert result.exit_code == 0, f"implement --help exited {result.exit_code}:\n{result.output}"

    def test_implement_help_contains_internal(self, runner: CliRunner) -> None:
        """Help text must contain 'internal' (case-insensitive)."""
        result = runner.invoke(cli_app, ["implement", "--help"])
        assert result.exit_code == 0
        assert "internal" in result.output.lower(), (
            f"'internal' not found in --help output:\n{result.output}"
        )

    def test_implement_help_contains_spec_kitty_next(self, runner: CliRunner) -> None:
        """Help text must name 'spec-kitty next' as the canonical loop entry."""
        result = runner.invoke(cli_app, ["implement", "--help"])
        assert result.exit_code == 0
        assert "spec-kitty next" in result.output, (
            f"'spec-kitty next' not found in --help output:\n{result.output}"
        )

    def test_implement_help_contains_agent_action_implement(self, runner: CliRunner) -> None:
        """Help text must name 'spec-kitty agent action implement' as canonical verb."""
        result = runner.invoke(cli_app, ["implement", "--help"])
        assert result.exit_code == 0
        assert "spec-kitty agent action implement" in result.output, (
            f"'spec-kitty agent action implement' not found in --help output:\n{result.output}"
        )
