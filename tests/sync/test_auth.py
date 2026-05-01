"""Regression tests for the WP10 password-era removal.

Mission 080 (browser-mediated OAuth) deleted the legacy
``specify_cli.sync.auth`` module, which contained the password-based
``AuthClient`` and the TOML-backed ``CredentialStore``. This file replaces
the old unit tests, which exclusively exercised those deleted classes.

Equivalent coverage now lives in:
- ``tests/auth/test_secure_storage_keychain.py`` (WP01)
- ``tests/auth/test_secure_storage_file.py`` (WP01)
- ``tests/auth/test_token_manager.py`` (WP02)
- ``tests/auth/test_refresh_flow.py`` (WP04)
- ``tests/auth/concurrency/test_single_flight_refresh.py`` (WP11)

The remaining tests in this file are user-facing regression gates that
guard the hard cutover (C-001):

1. ``specify_cli.sync.auth`` must not exist.
2. The Typer auth app must expose exactly ``login``, ``logout``, and
   ``status`` commands (no parallel ``oauth-*`` commands).
3. ``auth login --help`` must mention neither "password" nor "username".
4. ``AuthClient`` / ``CredentialStore`` must not be reintroduced anywhere
   under ``src/specify_cli/`` (except, historically, in the deleted
   module itself — which no longer exists, so this check is total).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T052: the legacy module must be gone
# ---------------------------------------------------------------------------


def test_legacy_sync_auth_module_is_gone() -> None:
    """Attempting to import the deleted legacy module must fail."""
    with pytest.raises(ImportError):
        import specify_cli.sync.auth  # noqa: F401


def test_legacy_auth_classes_not_reintroduced_in_src() -> None:
    """Guard against accidental re-introduction of the password-era classes.

    Scans every ``.py`` file under ``src/specify_cli/`` and asserts that
    neither ``class AuthClient`` nor ``class CredentialStore`` is defined
    anywhere. (``TrackerCredentialStore`` in ``tracker/credentials.py`` is
    an unrelated class and is explicitly allowed.)
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "specify_cli"
    assert src_root.is_dir(), f"expected src tree at {src_root}"

    offenders: list[tuple[Path, str]] = []
    for py_file in src_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if "class AuthClient" in text:
            offenders.append((py_file, "class AuthClient"))
        # Match the exact legacy class name (word boundary sensitive):
        # ``TrackerCredentialStore`` is a different, allowed class.
        for line in text.splitlines():
            if "class CredentialStore" in line and "TrackerCredentialStore" not in line:
                offenders.append((py_file, line.strip()))

    assert not offenders, "Legacy password-era classes were reintroduced: " + "; ".join(f"{p}: {snippet}" for p, snippet in offenders)


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


def test_typer_app_has_required_commands() -> None:
    """Regression: the auth Typer app must expose login, logout, and status."""
    from specify_cli.cli.commands.auth import app

    command_names = _registered_command_names(app)
    assert "login" in command_names, command_names
    assert "logout" in command_names, command_names
    assert "status" in command_names, command_names


def test_no_oauth_prefixed_commands() -> None:
    """Regression: no parallel ``oauth-*`` commands.

    Hard cutover (C-001) means the new browser-mediated OAuth flow IS the
    ``auth login`` command, not a sibling set of commands.
    """
    from specify_cli.cli.commands.auth import app

    command_names = _registered_command_names(app)
    for forbidden in (
        "oauth-login",
        "oauth_login",
        "oauth-logout",
        "oauth_logout",
        "oauth-status",
        "oauth_status",
    ):
        assert forbidden not in command_names, f"Unexpected parallel command '{forbidden}' found: {sorted(command_names)}"


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


def test_logout_command_no_password_in_help() -> None:
    """``auth logout --help`` must mention neither "password" nor "username"."""
    from specify_cli.cli.commands.auth import app

    runner = CliRunner()
    result = runner.invoke(app, ["logout", "--help"])
    assert result.exit_code == 0, result.output
    help_lower = result.output.lower()
    assert "password" not in help_lower, result.output
    assert "username" not in help_lower, result.output


def test_status_command_no_password_in_help() -> None:
    """``auth status --help`` must mention neither "password" nor "username"."""
    from specify_cli.cli.commands.auth import app

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0, result.output
    help_lower = result.output.lower()
    assert "password" not in help_lower, result.output
    assert "username" not in help_lower, result.output


# ---------------------------------------------------------------------------
# T052: CLI smoke — the dispatch shell still imports cleanly
# ---------------------------------------------------------------------------


def test_auth_dispatch_module_imports_cleanly() -> None:
    """``specify_cli.cli.commands.auth`` must import without errors.

    This is the CLI smoke test from the WP10 acceptance criteria.
    """
    from specify_cli.cli.commands.auth import app  # noqa: F401


def test_auth_package_exposes_token_manager() -> None:
    """The new canonical surface must still be importable."""
    from specify_cli.auth import get_token_manager  # noqa: F401
