"""Implementation of ``spec-kitty auth whoami``.

Prints the authenticated user's email on stdout and exits 0.
Prints nothing and exits 1 if not authenticated or session is expired.

Designed for machine consumption — canary preflight scripts read the first
non-empty output line as the identity token.
"""

from __future__ import annotations

import typer

from specify_cli.auth import get_token_manager


def whoami_impl() -> None:
    """Print the current user's email and exit 0, or exit 1 if not authenticated."""
    tm = get_token_manager()
    session = tm.get_current_session()

    if session is None or session.is_refresh_token_expired():
        raise typer.Exit(1)

    print(session.email)


__all__ = ["whoami_impl"]
