"""Regression for spec-kitty#713: the typer/click exception shim must survive typer 0.27+.

typer 0.27.x vendors click as ``typer._click`` but its ``_click.exceptions`` module
defines only ``UsageError`` — no ``Abort``, no ``Exit`` — and raises typer's own public
``typer.Abort``/``typer.Exit`` instead.  The previous shim evaluated
``_CLICK.exceptions.Abort`` eagerly as a ``getattr`` default, which raised
``AttributeError`` at import time and broke every fresh-venv wheel install.
"""

from __future__ import annotations

import json
import types

import click
import pytest
import typer
from typer.testing import CliRunner

from specify_cli.orchestrator_api import commands as shim
from specify_cli.orchestrator_api.commands import _JSONErrorGroup

pytestmark = [pytest.mark.fast, pytest.mark.unit]


def _typer_027_like_click_module() -> types.SimpleNamespace:
    """A stand-in for ``typer._click`` as shipped in typer 0.27.2."""
    return types.SimpleNamespace(exceptions=types.SimpleNamespace(UsageError=click.UsageError))


def test_vendored_lookup_returns_none_when_typer_027_omits_abort_and_exit(monkeypatch):
    monkeypatch.setattr(shim.typer_core, "_click", _typer_027_like_click_module(), raising=False)

    assert shim._vendored_click_exception("UsageError") is click.UsageError
    assert shim._vendored_click_exception("Abort") is None
    assert shim._vendored_click_exception("Exit") is None


def test_vendored_lookup_returns_none_without_a_vendored_click(monkeypatch):
    monkeypatch.delattr(shim.typer_core, "_click", raising=False)

    assert shim._vendored_click_exception("UsageError") is None


def test_vendored_lookup_ignores_non_exception_attributes(monkeypatch):
    bogus = types.SimpleNamespace(exceptions=types.SimpleNamespace(Abort="not a class"), Abort=42)
    monkeypatch.setattr(shim.typer_core, "_click", bogus, raising=False)

    assert shim._vendored_click_exception("Abort") is None


def test_exception_classes_drops_none_and_duplicates():
    assert shim._exception_classes(None) == ()
    # Two genuinely distinct classes: on typer <= 0.25 ``typer.Abort`` *is* ``click.Abort``.
    assert shim._exception_classes(click.Abort, None, click.Abort, click.UsageError) == (
        click.Abort,
        click.UsageError,
    )


def test_catch_tuples_always_carry_typers_public_surface():
    """Whatever typer version is installed, typer's own classes must be caught."""
    assert typer.Abort in shim._CLICK_ABORTS
    assert typer.Exit in shim._EXIT
    assert click.UsageError in shim._CLICK_USAGE_ERRORS
    assert click.Abort in shim._CLICK_ABORTS
    for group in (shim._CLICK_USAGE_ERRORS, shim._CLICK_ABORTS, shim._EXIT):
        assert all(isinstance(cls, type) and issubclass(cls, BaseException) for cls in group)


def _group_app() -> typer.Typer:
    app = typer.Typer(name="shim-probe", no_args_is_help=False, cls=_JSONErrorGroup)

    @app.command()
    def abort() -> None:
        raise typer.Abort()

    @app.command()
    def leave() -> None:
        raise typer.Exit(code=7)

    return app


def test_public_typer_abort_becomes_json_envelope():
    result = CliRunner().invoke(_group_app(), ["abort"])

    assert result.exit_code == 2
    envelope = json.loads(result.output.strip())
    assert envelope["success"] is False
    assert envelope["data"]["message"] == "Command aborted"


def test_public_typer_exit_code_is_preserved():
    result = CliRunner().invoke(_group_app(), ["leave"])

    assert result.exit_code == 7
