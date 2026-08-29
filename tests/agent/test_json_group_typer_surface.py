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


def test_resolve_click_exc_returns_exception_classes():
    """``_resolve_click_exc`` resolves each shim symbol to a real exception class.

    Regression guard for typer 0.27.2 (2026-08-28), which dropped ``Abort`` and
    ``Exit`` from ``typer._click.exceptions``. The pre-fix
    ``getattr(_CLICK, name, _CLICK.exceptions.<name>)`` form evaluated the
    default eagerly and crashed the whole module at import with ``AttributeError``.
    """
    from specify_cli.orchestrator_api import commands as cmds

    for name in ("UsageError", "Abort", "Exit"):
        resolved = cmds._resolve_click_exc(name)
        assert isinstance(resolved, type), f"{name} did not resolve to a class"
        assert issubclass(resolved, BaseException), f"{name} is not an exception type"


def test_module_exception_aliases_are_exception_types():
    """The module-level shim aliases are all populated exception types/tuples."""
    from specify_cli.orchestrator_api import commands as cmds

    for alias in (cmds._USAGE_ERROR, cmds._ABORT, cmds._EXIT):
        assert isinstance(alias, type) and issubclass(alias, BaseException)
    for group in (cmds._CLICK_USAGE_ERRORS, cmds._CLICK_ABORTS):
        assert group and all(issubclass(exc, BaseException) for exc in group)


def test_resolve_click_exc_falls_back_when_vendored_module_lacks_symbol(monkeypatch):
    """Simulates typer 0.27.2: the vendored ``_click`` module lacks ``Abort``.

    The resolver must fall through to ``typer`` / ``click`` rather than raise.
    """
    from specify_cli.orchestrator_api import commands as cmds

    class _EmptyExceptions:
        pass

    class _StubVendoredClick:
        exceptions = _EmptyExceptions()  # no Abort / Exit / UsageError attributes

    monkeypatch.setattr(cmds, "_CLICK", _StubVendoredClick)

    for name in ("Abort", "Exit", "UsageError"):
        resolved = cmds._resolve_click_exc(name)
        assert isinstance(resolved, type) and issubclass(resolved, BaseException)


def test_resolve_click_exc_unknown_symbol_raises():
    """An unresolvable symbol name fails loud rather than returning None."""
    from specify_cli.orchestrator_api import commands as cmds

    with pytest.raises(AttributeError):
        cmds._resolve_click_exc("DefinitelyNotAClickException")
