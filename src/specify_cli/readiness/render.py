"""Readiness auth-guidance renderer (WS2, issue Priivacy-ai/spec-kitty#1094).

Surface function ``render_auth_guidance`` translates a probe verdict
(``AuthStatus`` + teamspace handle) into operator-facing guidance that
honors the Wave 1 suppression contract.

Output matrix:

==================================  ==================  =====================================
``output_policy``                   ``auth_status``     Effect
==================================  ==================  =====================================
``INTERACTIVE``                     ``LOGGED_OUT_IN_..`` Multiline Rich panel on stderr.
``NON_INTERACTIVE``                 ``LOGGED_OUT_IN_..`` Single canonical line on stderr via
                                                       ``_auth_recovery.emit_structured_stderr``.
``MACHINE_OUTPUT``                  ``LOGGED_OUT_IN_..`` No output. Probe still records the
                                                       status; rendering is suppressed.
any                                 anything else      No output.
==================================  ==================  =====================================

Contract:

- **Never raises.** All exceptions are swallowed.
- Writes to ``sys.stderr`` only. ``sys.stdout`` is never touched.
- Reuses ``_auth_recovery.emit_structured_stderr`` for the canonical CI line
  rather than duplicating its format (single source of truth).

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1094
"""

from __future__ import annotations

import sys

from specify_cli.readiness.coordinator import AuthStatus, OutputPolicy


_AUTH_LOGIN_REMEDIATION = "spec-kitty auth login"


def _render_interactive_panel(teamspace: str, command_name: str) -> None:
    """Render the multiline Rich panel on stderr for the TTY case.

    Swallows all exceptions; falls back to a plain-text stderr block if Rich
    fails to import or render.
    """
    body = (
        f"This repo is connected to Teamspace [cyan]{teamspace}[/cyan], "
        f"but you are not logged in.\n"
        f"Command: [dim]spec-kitty {command_name}[/dim]\n\n"
        f"Run: [bold]{_AUTH_LOGIN_REMEDIATION}[/bold] to re-authenticate."
    )

    try:
        from rich.console import Console  # noqa: PLC0415 — lazy
        from rich.panel import Panel  # noqa: PLC0415 — lazy

        console = Console(file=sys.stderr, force_terminal=False, highlight=False)
        panel = Panel(
            body,
            title="Logged out on a connected Teamspace",
            border_style="yellow",
            expand=False,
        )
        console.print(panel)
        return
    except Exception:  # noqa: BLE001 — fall through to plain-text path
        pass

    # Plain-text fallback (used when Rich fails). Still multi-line and still
    # contains the remediation string and the teamspace handle so the
    # interactive test assertions hold.
    try:
        sys.stderr.write(
            "Logged out on a connected Teamspace\n"
            f"  Teamspace: {teamspace}\n"
            f"  Command:   spec-kitty {command_name}\n"
            f"  Run: {_AUTH_LOGIN_REMEDIATION} to re-authenticate.\n"
        )
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 — final defensive layer
        pass


def render_auth_guidance(
    *,
    status: AuthStatus,
    teamspace: str | None,
    command_name: str,
    output_policy: OutputPolicy,
) -> None:
    """Emit auth-readiness guidance per the output-policy matrix.

    Never raises. See module docstring for the full matrix.
    """
    try:
        # Only the logged-out-in-teamspace verdict produces visible output.
        if status != AuthStatus.LOGGED_OUT_IN_TEAMSPACE:
            return

        # Suppress entirely in machine-output mode (--json, --quiet).
        if output_policy == OutputPolicy.MACHINE_OUTPUT:
            return

        # We must have a non-empty handle to render meaningful guidance.
        if not isinstance(teamspace, str) or not teamspace.strip():
            return
        handle = teamspace.strip()

        cmd = command_name.strip() if isinstance(command_name, str) and command_name.strip() else "spec-kitty"

        if output_policy == OutputPolicy.INTERACTIVE:
            _render_interactive_panel(handle, cmd)
            return

        if output_policy == OutputPolicy.NON_INTERACTIVE:
            try:
                from specify_cli.cli.commands._auth_recovery import (  # noqa: PLC0415 — lazy
                    emit_structured_stderr,
                )
            except Exception:  # noqa: BLE001 — defensive fallback
                # Minimal inline fallback preserving the canonical format.
                try:
                    sys.stderr.write(
                        "spec-kitty: logged_out_on_connected_teamspace "
                        f"teamspace={handle} "
                        f"command={cmd} "
                        "action=run-spec-kitty-auth-login\n"
                    )
                    sys.stderr.flush()
                except Exception:  # noqa: BLE001
                    pass
                return
            emit_structured_stderr(teamspace=handle, command_name=cmd)
            return

        # Any unknown OutputPolicy member: be conservative — emit nothing.
        return
    except Exception:  # noqa: BLE001 — outermost safety net; renderer must never raise.
        return


__all__ = ["render_auth_guidance"]
