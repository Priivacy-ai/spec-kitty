"""Command registration helpers for Spec Kitty CLI."""

from __future__ import annotations

import typer

from . import accept as accept_module
from . import agent as agent_module
from . import context as context_module
from . import dashboard as dashboard_module
from . import implement as implement_module
from . import merge as merge_module
from . import mission as mission_module
from . import ops as ops_module
from . import orchestrate as orchestrate_module
from . import repair as repair_module
from . import research as research_module
from . import sync as sync_module
from . import upgrade as upgrade_module
from . import validate_encoding as validate_encoding_module
from . import validate_tasks as validate_tasks_module
from . import verify as verify_module


def register_commands(app: typer.Typer) -> None:
    """Attach all extracted commands to the root Typer application."""
    app.command()(accept_module.accept)
    app.add_typer(agent_module.app, name="agent")
    app.add_typer(context_module.app, name="context")
    app.command()(dashboard_module.dashboard)
    app.command()(implement_module.implement)
    app.command()(merge_module.merge)
    app.add_typer(mission_module.app, name="mission")
    app.add_typer(ops_module.app, name="ops")
    app.add_typer(orchestrate_module.app, name="orchestrate")
    app.add_typer(repair_module.app, name="repair", help="Repair broken templates")
    app.command()(research_module.research)
    app.add_typer(sync_module.app, name="sync", help="Synchronization commands")
    app.command()(upgrade_module.upgrade)
    app.command(name="list-legacy-features")(upgrade_module.list_legacy_features)
    app.command(name="validate-encoding")(validate_encoding_module.validate_encoding)
    app.command(name="validate-tasks")(validate_tasks_module.validate_tasks)
    app.command()(verify_module.verify_setup)


__all__ = ["register_commands"]
