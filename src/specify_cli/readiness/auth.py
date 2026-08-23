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

1. If canonical session assessment fails, return ``(UNKNOWN, None)`` without
   consulting Teamspace detection.
2. If assessment completes with a usable session,
   return ``(AUTHENTICATED, None)``.
3. Only after a completed no-session assessment, consult
   ``detect_logged_out_with_connected_teamspace(repo_root)``:
   - Returns a non-empty handle → ``(LOGGED_OUT_IN_TEAMSPACE, handle)``.
   - Returns ``None`` → ``(NOT_IN_TEAMSPACE, None)``.
4. Any exception inside the resolution path → ``(UNKNOWN, None)``.

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
        except Exception:  # noqa: BLE001 — defensive
            return (AuthStatus.UNKNOWN, None)

        if not assessment.completed:
            return (AuthStatus.UNKNOWN, None)
        if assessment.usable_session is True:
            return (AuthStatus.AUTHENTICATED, None)

        # Step 3: logged-out — does the repo show a connected Teamspace?
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
