"""Release-channel doctor sibling (T024, C-CHN-3).

Self-registering ``doctor channel`` subcommand: reports whether the operator
is on the default **stable** release channel or has opted into the
pre-release (rc) channel via ``SPEC_KITTY_PRERELEASE`` (see
``core/channel.py``). Read-only — never mutates state.

**Auto-discovery seam** (mirrors ``_provenance_doctor.py``, the WP03
worked example): ``doctor.py`` imports every ``cli/commands/_*_doctor.py``
module and calls ``register(app)`` when the module exposes one. This module
never requires an edit to ``doctor.py`` to add its subcommand — the
load-bearing fix for the WP03/WP04/WP05 three-lane collision.
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

from specify_cli.core.channel import prerelease_enabled

from ._doctor_shared import console

__all__ = ["register", "run_channel_report"]

_STABLE = "stable"
_PRERELEASE = "prerelease-opt-in"


def _active_channel() -> str:
    """Return the active channel token: ``"stable"`` or ``"prerelease-opt-in"``."""
    return _PRERELEASE if prerelease_enabled() else _STABLE


def run_channel_report(*, json_output: bool) -> None:
    """Entry point for ``doctor channel``. Read-only; always exits 0."""
    channel = _active_channel()

    if json_output:
        payload = {"channel": channel, "prerelease_opt_in": channel == _PRERELEASE}
        console.print_json(json.dumps(payload, indent=2))
        raise typer.Exit(0)

    if channel == _PRERELEASE:
        console.print(
            "[yellow]Release channel[/yellow]: prerelease-opt-in "
            "(SPEC_KITTY_PRERELEASE is set) — 'latest version' surfaces "
            "include release candidates."
        )
    else:
        console.print(
            "[green]Release channel[/green]: stable (default) — "
            "'latest version' surfaces only stable releases."
        )
    raise typer.Exit(0)


def register(app: typer.Typer) -> None:
    """Register the ``channel`` subcommand onto *app* (doctor.py auto-discovery seam)."""

    @app.command(name="channel")
    def channel(
        json_output: Annotated[
            bool,
            typer.Option("--json", help="Machine-readable JSON output"),
        ] = False,
    ) -> None:
        """Report the active release channel (stable vs. prerelease-opt-in).

        Reads SPEC_KITTY_PRERELEASE (default OFF — stable channel). Never
        mutates state.

        Examples:
            spec-kitty doctor channel
            spec-kitty doctor channel --json
        """
        run_channel_report(json_output=json_output)
