"""Command registration helpers for Spec Kitty CLI."""

from __future__ import annotations

import typer

from . import accept as accept_module
from . import dashboard as dashboard_module
from . import merge as merge_module
from . import mission as mission_module
from . import research as research_module
from . import validate_encoding as validate_encoding_module
from . import validate_tasks as validate_tasks_module
from . import verify as verify_module


def register_commands(app: typer.Typer) -> None:
    """Attach all extracted commands to the root Typer application."""
    app.command()(accept_module.accept)
    app.command()(dashboard_module.dashboard)
    app.command()(merge_module.merge)
    app.add_typer(mission_module.app, name="mission")
    app.command()(research_module.research)
    app.command(name="validate-encoding")(validate_encoding_module.validate_encoding)
    app.command(name="validate-tasks")(validate_tasks_module.validate_tasks)
    app.command()(verify_module.verify_setup)


__all__ = ["register_commands"]
