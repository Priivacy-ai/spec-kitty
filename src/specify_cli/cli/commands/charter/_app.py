"""The charter typer app — shared instance for all subcommand modules.

Created by WP06 (MS-1: per-subcommand split of the legacy 3,328-line
``charter.py``). All subcommand modules import ``charter_app`` from here and
register their handler via ``@charter_app.command(...)``. ``app`` is kept as
the canonical legacy alias so historic imports (and the registration of the
``charter_bundle`` sub-app + ``charter_preflight`` command) keep working.
"""
from __future__ import annotations

import logging

import typer
from rich.console import Console

from specify_cli.cli.commands.charter.activate import charter_activate_app
from specify_cli.cli.commands.charter_bundle import app as charter_bundle_app
from specify_cli.cli.commands.charter.mission_type import charter_mission_type_app

logger = logging.getLogger("specify_cli.cli.commands.charter")

#: Filename of the charter bundle metadata sidecar.
METADATA_FILENAME = "metadata.yaml"

#: The typer app exposed under ``spec-kitty charter``.
charter_app = typer.Typer(
    name="charter",
    help="Charter management commands",
    no_args_is_help=True,
)
#: Legacy alias; tests and downstream code import both names.
app = charter_app

# WP01 introduced ``charter_bundle_app`` as a self-contained Typer sub-app.
# WP03 registers it under ``bundle`` so users can invoke
# ``spec-kitty charter bundle validate`` from the unified CLI surface
# (FR-013).
charter_app.add_typer(charter_bundle_app, name="bundle")

# WP14 (FR-016): ``spec-kitty charter mission-type list`` — activated types only.
charter_app.add_typer(charter_mission_type_app, name="mission-type")

# WP15 (FR-008): ``spec-kitty charter activate mission-type <id>`` — in-flight warning.
charter_app.add_typer(charter_activate_app, name="activate")

#: Module-level Rich console for all subcommand handlers.
console = Console()
