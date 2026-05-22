"""Readiness auth probe (WS2, issue Priivacy-ai/spec-kitty#1094).

Translates the existing ``_auth_recovery.detect_logged_out_with_connected_teamspace``
read-only detector plus ``TokenManager.is_authenticated`` into one of the
authoritative ``AuthStatus`` values consumed by the readiness coordinator.

Contract:

- **Local signals only.** No network I/O. All heavy imports are lazy.
- **Never raises.** Any internal exception degrades to ``(AuthStatus.UNKNOWN, None)``.
- **Reuses** ``detect_logged_out_with_connected_teamspace`` verbatim — does NOT
  duplicate detection logic.
- Gated by the coordinator behind ``is_saas_sync_enabled()``; this module
  does not check the flag itself (separation of concerns: the coordinator
  owns the gate; this module owns the verdict).

Resolution order:

1. If a valid session is reachable (``TokenManager.is_authenticated`` is true),
   return ``(AUTHENTICATED, None)``.
2. Otherwise consult ``detect_logged_out_with_connected_teamspace(repo_root)``:
   - Returns a non-empty handle → ``(LOGGED_OUT_IN_TEAMSPACE, handle)``.
   - Returns ``None`` → ``(NOT_IN_TEAMSPACE, None)``.
3. Any exception inside the resolution path → ``(UNKNOWN, None)``.

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
            authenticated = bool(tm.is_authenticated)
        except Exception:  # noqa: BLE001 — defensive
            authenticated = False

        if authenticated:
            return (AuthStatus.AUTHENTICATED, None)

        # Step 2: logged-out — does the repo show a connected Teamspace?
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
