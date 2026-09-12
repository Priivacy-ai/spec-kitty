"""Readiness auth probe (WS2, issue Priivacy-ai/spec-kitty#1094).

Translates the canonical ``TokenManager.session_assessment`` plus the existing
``_auth_recovery.detect_logged_out_with_connected_teamspace`` read-only detector
into one of the authoritative ``AuthStatus`` values consumed by readiness.

Contract:

- **Local signals only.** No network I/O. All heavy imports are lazy.
- **Never raises.** Any internal exception degrades to ``(AuthStatus.UNKNOWN, None)``.
- **Reuses** ``detect_logged_out_with_connected_teamspace`` verbatim — does NOT
  duplicate detection logic.
- Gated by the coordinator behind ``is_saas_sync_enabled()``; this module
  does not check the flag itself (separation of concerns: the coordinator
  owns the gate; this module owns the verdict).

Resolution order:

1. If a completed, usable session is reachable (canonical
   ``TokenManager.session_assessment``), return ``(AUTHENTICATED, None)``.
2. Otherwise — including when the assessment did not complete, or raised —
   consult ``detect_logged_out_with_connected_teamspace(repo_root)``. A
   failed or inconclusive assessment is not authentication and does not by
   itself make the probe give up; it degrades to "not authenticated" the
   same way the historical Boolean contract did, and the Teamspace detector
   still gets to render its own verdict:
   - Returns a non-empty handle → ``(LOGGED_OUT_IN_TEAMSPACE, handle)``.
   - Returns ``None`` → ``(NOT_IN_TEAMSPACE, None)``.
3. Any exception outside that resolution (acquiring a ``TokenManager`` at
   all, or the detector itself raising) → ``(UNKNOWN, None)`` — reserved for
   the catastrophic failure path.

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1094
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.readiness.coordinator import AuthStatus


def probe_auth_status(
    *,
    repo_root: Path | None = None,
) -> tuple[AuthStatus, str | None]:
    """Return ``(status, teamspace_handle_or_None)`` for the current invocation.

    See module docstring for the resolution contract.

    Args:
        repo_root: optional override for the repository root. ``None`` means
            "let the underlying detector decide" (matches the helper's own
            default semantics).

    Returns:
        A 2-tuple ``(AuthStatus, str | None)``. The handle is non-None only
        when ``status == LOGGED_OUT_IN_TEAMSPACE``.
    """
    try:
        # Step 1: are we authenticated?
        try:
            from specify_cli.auth import get_token_manager  # noqa: PLC0415 — lazy
        except Exception:  # noqa: BLE001 — defensive; probe must never raise
            return (AuthStatus.UNKNOWN, None)

        try:
            tm = get_token_manager()
        except Exception:  # noqa: BLE001 — defensive; probe must never raise
            return (AuthStatus.UNKNOWN, None)

        try:
            assessment = tm.session_assessment
            authenticated = assessment.completed and assessment.usable_session is True
        except Exception:  # noqa: BLE001 — defensive; degrades to not-authenticated
            authenticated = False

        if authenticated:
            return (AuthStatus.AUTHENTICATED, None)

        # Step 2: not authenticated (or inconclusive) — does the repo show a
        # connected Teamspace?
        from specify_cli.cli.commands._auth_recovery import (  # noqa: PLC0415 — lazy
            detect_logged_out_with_connected_teamspace,
        )

        handle = detect_logged_out_with_connected_teamspace(repo_root=repo_root)
        if isinstance(handle, str) and handle.strip():
            return (AuthStatus.LOGGED_OUT_IN_TEAMSPACE, handle.strip())

        return (AuthStatus.NOT_IN_TEAMSPACE, None)
    except Exception:  # noqa: BLE001 — outermost safety net
        return (AuthStatus.UNKNOWN, None)


__all__ = ["probe_auth_status"]
