"""Regression tests for implement command --help output (T014 / FR-503).

Verifies that:
- ``spec-kitty implement --help`` marks the command as internal infrastructure.
- The help text names the canonical user-facing workflow commands.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

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

    def test_implement_help_contains_internal_workflow_guidance(self, runner: CliRunner) -> None:
        """implement --help marks the command internal and names user workflows."""
        with patch.object(sys, "argv", ["spec-kitty", "implement", "--help"]):
            result = runner.invoke(cli_app, ["implement", "--help"])
        assert result.exit_code == 0, f"implement --help exited {result.exit_code}:\n{result.output}"
        assert "internal" in result.output.lower(), (
            f"'internal' not found in --help output:\n{result.output}"
        )
        assert "spec-kitty next" in result.output, (
            f"'spec-kitty next' not found in --help output:\n{result.output}"
        )
        assert "spec-kitty agent action implement" in result.output, (
            f"'spec-kitty agent action implement' not found in --help output:\n{result.output}"
        )
