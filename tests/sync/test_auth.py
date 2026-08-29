"""User-facing browser-auth command contracts.

The deleted password implementation is covered at its canonical auth
integration boundary.  This module keeps only the consumed CLI surface: the
required browser-auth command names and password-free login help.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


# ---------------------------------------------------------------------------
# T056: Typer app surface regression
# ---------------------------------------------------------------------------


def _registered_command_names(app) -> set[str]:
    """Return the effective command names registered on a Typer app.

    Typer uses the callback function's ``__name__`` as the command name
    when the decorator is invoked without an explicit ``name=``. This
    helper normalises to the same surface the CLI user sees.
    """
    names: set[str] = set()
    for cmd in app.registered_commands:
        if cmd.name:
            names.add(cmd.name)
        elif cmd.callback is not None:
            names.add(cmd.callback.__name__)
    return names


def test_typer_app_exposes_required_commands_without_oauth_aliases() -> None:
    """Browser auth uses canonical commands, not a parallel OAuth namespace."""
    from specify_cli.cli.commands.auth import app

    command_names = _registered_command_names(app)
    assert {"login", "logout", "status"} <= command_names
    assert not command_names & {
        "oauth-login",
        "oauth_login",
        "oauth-logout",
        "oauth_logout",
        "oauth-status",
        "oauth_status",
    }


# ---------------------------------------------------------------------------
# T055: user-facing help text has no password/username leftovers
# ---------------------------------------------------------------------------


def test_login_command_no_password_in_help() -> None:
    """``auth login --help`` must mention neither "password" nor "username"."""
    from specify_cli.cli.commands.auth import app

    runner = CliRunner()
    result = runner.invoke(app, ["login", "--help"])
    assert result.exit_code == 0, result.output
    help_lower = result.output.lower()
    assert "password" not in help_lower, result.output
    assert "username" not in help_lower, result.output
