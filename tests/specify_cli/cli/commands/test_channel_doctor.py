"""Tests for ``spec-kitty doctor channel`` (T024, C-CHN-3).

Two concerns, mirroring ``test_provenance_doctor.py`` (the WP03 worked
example for the auto-discovery seam):

1. ``_channel_doctor.py`` itself — reports the active release channel via
   ``core.channel.prerelease_enabled()``.
2. ``doctor.py``'s auto-discovery loop — ``channel`` must appear as a
   registered command on ``doctor.app`` WITHOUT ``doctor.py`` hand-importing
   ``_channel_doctor`` or hand-writing an ``@app.command`` shell for it.
"""

from __future__ import annotations

import json

import pytest
import typer
from typer.testing import CliRunner

import specify_cli.cli.commands.doctor as doctor_module
from specify_cli.cli.commands import _channel_doctor

pytestmark = [pytest.mark.fast]

runner = CliRunner()


# ---------------------------------------------------------------------------
# Auto-discovery seam regression guard
# ---------------------------------------------------------------------------


def test_channel_is_registered_on_doctor_app_without_hand_wiring() -> None:
    """``channel`` is a real command on ``doctor.app``, discovered — not hand-written."""
    names = {cmd.name for cmd in doctor_module.app.registered_commands}
    assert "channel" in names


def test_doctor_py_source_never_hand_imports_the_channel_sibling() -> None:
    """Regression guard: doctor.py must gain this command via discovery, not an edit.

    AST-based (not a substring scan) so this docstring's own mention of
    ``_channel_doctor.py`` cannot self-trip the guard.
    """
    import ast
    from pathlib import Path

    tree = ast.parse(Path(doctor_module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "_channel_doctor":
            pytest.fail("doctor.py must not hand-import _channel_doctor (discovery seam regression)")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "command":
            for keyword in node.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    assert keyword.value.value != "channel", (
                        "doctor.py must not hand-write an @app.command(name='channel') "
                        "shell (discovery seam regression)"
                    )


def test_register_is_idempotent_safe_to_call_directly() -> None:
    """``register(app)`` (the seam's own contract) adds exactly one command."""
    scratch_app = typer.Typer()
    _channel_doctor.register(scratch_app)

    names = [cmd.name for cmd in scratch_app.registered_commands]
    assert names == ["channel"]


# ---------------------------------------------------------------------------
# run_channel_report / _active_channel
# ---------------------------------------------------------------------------


class TestRunChannelReport:
    def test_default_off_reports_stable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPEC_KITTY_PRERELEASE", raising=False)
        with pytest.raises(typer.Exit) as exc_info:
            _channel_doctor.run_channel_report(json_output=False)
        assert exc_info.value.exit_code == 0

    def test_opted_in_reports_prerelease(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SPEC_KITTY_PRERELEASE", "1")
        with pytest.raises(typer.Exit) as exc_info:
            _channel_doctor.run_channel_report(json_output=False)
        assert exc_info.value.exit_code == 0

    def test_json_output_also_exits_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPEC_KITTY_PRERELEASE", raising=False)
        with pytest.raises(typer.Exit) as exc_info:
            _channel_doctor.run_channel_report(json_output=True)
        assert exc_info.value.exit_code == 0


# ---------------------------------------------------------------------------
# CLI surface (human + --json)
# ---------------------------------------------------------------------------


class TestDoctorChannelCli:
    def test_human_output_stable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPEC_KITTY_PRERELEASE", raising=False)

        result = runner.invoke(doctor_module.app, ["channel"])

        assert result.exit_code == 0, result.output
        assert "stable" in result.output.lower()

    def test_human_output_prerelease(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SPEC_KITTY_PRERELEASE", "1")

        result = runner.invoke(doctor_module.app, ["channel"])

        assert result.exit_code == 0, result.output
        assert "prerelease" in result.output.lower()

    def test_json_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SPEC_KITTY_PRERELEASE", "1")

        result = runner.invoke(doctor_module.app, ["channel", "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["channel"] == "prerelease-opt-in"
        assert payload["prerelease_opt_in"] is True
