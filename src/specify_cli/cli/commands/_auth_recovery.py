"""Logged-out-on-connected-teamspace detection helpers (Mission 7, issue #829).

This module provides the read-only detector and canonical stderr formatter
that ``specify_cli.readiness`` calls when authentication is missing but the
local repo state shows a prior teamspace connection.

Public surface:

- ``detect_logged_out_with_connected_teamspace``: read-only detector.
- ``emit_structured_stderr``: writes the canonical CI-readable line.

The former interactive ``[L]ogin / [S]kip / [Q]uit`` recovery facade
(``handle_unauthenticated_with_teamspace``, ``offer_login_recovery``,
``RecoveryOutcome``, ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE``,
``is_interactive``) was built for the ``spec-kitty sync ...`` commands' own
auth-missing branches. Those commands were deleted with the sync transport
(issue #5); the readiness coordinator's non-blocking guidance renderer
(``specify_cli.readiness.render``) replaced them and deliberately does not
block command startup on a keystroke prompt. The facade was pruned as dead
collateral (issue #116) rather than kept for a caller that will not return.

All third-party / heavy imports (``TokenManager``) are deferred to call-site
to keep import cost low and to keep test isolation tractable.
"""

from __future__ import annotations

import sys
from pathlib import Path


def detect_logged_out_with_connected_teamspace(
    repo_root: Path | None = None,  # noqa: ARG001 - kept for signature stability; readiness/auth.py threads it
) -> str | None:
    """Return a teamspace handle if logged-out on a connected repo, else None.

    Read-only. No network I/O. All heavy imports are lazy.

    Resolution order:
      1. If TokenManager reports an authenticated session, return ``None``
         (caller has no recovery work to do).
      2. Stored session's first private-teamspace ``team.name`` if non-empty.
      3. ``None``.

    (The former sync-routing-derived handle detectors were removed with the
    sync transport, issue #5.)
    """
    # 1) Skip if a valid session exists.
    try:
        from specify_cli.auth import get_token_manager  # lazy
    except Exception:  # pragma: no cover - defensive
        return None

    try:
        tm = get_token_manager()
    except Exception:  # pragma: no cover - defensive
        return None

    try:
        if tm.is_authenticated:
            return None
    except Exception:  # pragma: no cover - defensive
        # If we cannot tell, fall through and try the detectors.
        pass

    # 4) Stored-session private team name. (The former routing-derived
    # handle detectors died with the sync transport, issue #5.)
    try:
        session = tm.get_current_session()
    except Exception:  # pragma: no cover - defensive
        session = None

    if session is not None:
        teams = getattr(session, "teams", None) or ()
        for team in teams:
            if bool(getattr(team, "is_private_teamspace", False)):
                name = getattr(team, "name", None)
                if isinstance(name, str) and name.strip():
                    return name.strip()

    return None


def emit_structured_stderr(*, teamspace: str, command_name: str) -> None:
    """Write the canonical machine-readable line to ``sys.stderr``.

    Single ASCII line, stable for scripts:

        spec-kitty: logged_out_on_connected_teamspace teamspace=<slug>
        command=<name> action=run-spec-kitty-auth-login

    """
    line = (
        "spec-kitty: logged_out_on_connected_teamspace "
        f"teamspace={teamspace} "
        f"command={command_name} "
        "action=run-spec-kitty-auth-login\n"
    )
    try:
        sys.stderr.write(line)
        sys.stderr.flush()
    except Exception:  # pragma: no cover - defensive
        pass


__all__ = [
    "detect_logged_out_with_connected_teamspace",
    "emit_structured_stderr",
]
