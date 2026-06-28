"""Root command ordering tests."""

from __future__ import annotations

import click
import pytest
from typer.main import get_command

from specify_cli import app as cli_app

pytestmark = [pytest.mark.fast]


def test_root_command_names_are_alphabetical() -> None:
    command = get_command(cli_app)
    ctx = click.Context(command, info_name="spec-kitty")
    visible_names = [
        name
        for name in command.list_commands(ctx)
        if not command.get_command(ctx, name).hidden
    ]

    assert visible_names == sorted(visible_names)


def test_root_command_sorting_preserves_representative_commands() -> None:
    command = get_command(cli_app)
    visible_names = {name for name, subcommand in command.commands.items() if not subcommand.hidden}

    assert {"agent", "doctor", "mission", "sync"}.issubset(visible_names)
