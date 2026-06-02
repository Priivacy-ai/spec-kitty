"""Tests for doctor skills slash-command audit and --fix repair (WP02/WP05)."""
from __future__ import annotations

from typer.testing import CliRunner

from specify_cli import app


def test_doctor_skills_output_includes_slash_commands_section() -> None:
    """Fails until FR-005/FR-007 is implemented: doctor currently has no Slash Commands section."""
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "skills"])
    # Fails until WP02 adds the slash-command audit section
    assert "Slash Commands" in (result.output or "")
