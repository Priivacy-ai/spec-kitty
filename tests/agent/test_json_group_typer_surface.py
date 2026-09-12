"""Smoke test: _JSONErrorGroup produces a JSON envelope via typer's public surface.

Guards against typer version drift silently breaking _JSONErrorGroup's exception
capture. In typer 0.26+, click is vendored as typer._click; this test must use
typer's public surface (typer.Exit, not click.exceptions.Exit) to remain
version-agnostic.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app

pytestmark = [pytest.mark.fast, pytest.mark.agent]

runner = CliRunner()


def test_no_subcommand_returns_json_envelope_via_typer_surface():
    """Invoking orchestrator-api with no subcommand must emit a JSON error envelope.

    This is the canary for _JSONErrorGroup's exception-capture shim
    (_CLICK_USAGE_ERRORS / _CLICK_ABORTS). The shim exists because typer 0.26+
    vendors click as typer._click, making typer._click.exceptions.UsageError
    completely independent from click.exceptions.UsageError. If the shim regresses,
    this test fails even though all prose-output paths still work.
    """
    result = runner.invoke(app, [])

    # The group must not exit 0 when no subcommand is given.
    assert result.exit_code != 0

    # Output must be valid JSON.
    try:
        envelope = json.loads(result.output.strip())
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Output is not valid JSON.\nOutput:\n{result.output!r}"
        ) from exc

    # Envelope must signal failure.
    assert envelope.get("ok") is False or envelope.get("success") is False, (
        f"Expected ok/success=false in envelope, got: {envelope}"
    )

    # Envelope must carry a non-empty error description.
    error_value = envelope.get("error") or envelope.get("error_code") or envelope.get("data", {}).get("message")
    assert error_value, (
        f"Expected a non-empty error field in envelope, got: {envelope}"
    )
