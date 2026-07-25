"""Root CLI completion behavior tests."""

from __future__ import annotations

import click
import pytest
from typer.main import get_command

from specify_cli import app as cli_app

pytestmark = [pytest.mark.fast]


def _completion_values(command: click.Command, info_name: str, incomplete: str = "") -> set[str]:
    ctx = click.Context(command, info_name=info_name)
    return {item.value for item in command.shell_complete(ctx, incomplete)}


def test_root_completion_options_are_exposed() -> None:
    command = get_command(cli_app)

    option_names = {name for param in command.params for name in param.opts}

    assert "--install-completion" in option_names
    assert "--show-completion" in option_names


def test_root_command_completion_includes_user_facing_commands() -> None:
    command = get_command(cli_app)

    completions = _completion_values(command, "spec-kitty")

    assert {"agent", "doctor", "mission"}.issubset(completions)


def test_nested_command_group_completion_is_scoped_to_group() -> None:
    root_command = get_command(cli_app)
    root_ctx = click.Context(root_command, info_name="spec-kitty")
    agent_command = root_command.get_command(root_ctx, "agent")

    assert agent_command is not None

    completions = _completion_values(agent_command, "agent")

    assert {"config", "mission", "tasks"}.issubset(completions)
    assert "doctor" not in completions
