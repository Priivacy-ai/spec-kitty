"""Final-sync diagnostic emission and classification.

This module is the sole write path for non-fatal final-sync failure diagnostics.
All error signals from daemon.py and batch.py are routed here.
"""

from __future__ import annotations

import enum
import sys
from dataclasses import dataclass
from typing import Literal

SyncSeverity = Literal["info", "warning", "error"]


class SyncDiagnosticCode(enum.StrEnum):
    """Stable, machine-readable codes for final-sync failure classification."""

    LOCK_UNAVAILABLE = "sync.final_sync_lock_unavailable"
    AUTH_REFRESH_IN_PROGRESS = "sync.auth_refresh_in_progress"
    WEBSOCKET_OFFLINE = "sync.websocket_offline"
    EVENT_LOOP_UNAVAILABLE = "sync.event_loop_unavailable"
    SERVER_AUTH_FAILURE = "sync.server_auth_failure"


@dataclass(frozen=True)
class SyncDiagnostic:
    """Backward-compatible diagnostic payload for existing sync call sites."""

    severity: SyncSeverity
    diagnostic_code: str
    message: str
    fatal: bool
    sync_phase: str


# Deduplication: emit at most one final-sync diagnostic per command invocation.
_diagnostic_emitted = False


def emit_sync_diagnostic(
    code: SyncDiagnosticCode | SyncDiagnostic,
    message: str | None = None,
    *,
    json_mode: bool = False,
    envelope: dict[str, object] | None = None,
) -> None:
    """Write one structured non-fatal diagnostic to stderr.

    At most one final-sync diagnostic line is emitted per process invocation,
    even when retries observe multiple failure signals.
    Matches the observed format from smoke evidence for backwards compatibility
    with tools that parse this output.
    """
    del json_mode, envelope
    global _diagnostic_emitted
    if _diagnostic_emitted:
        return
    diagnostic_code, diagnostic_message = _coerce_diagnostic(code, message)
    _diagnostic_emitted = True
    sys.stderr.write(
        f"sync_diagnostic severity=warning diagnostic_code={diagnostic_code.value} "
        f"fatal=false sync_phase=final_sync message={diagnostic_message}\n"
    )
    sys.stderr.flush()


def classify_sync_error(error_text: str) -> SyncDiagnosticCode:
    """Map a raw error string to a SyncDiagnosticCode.

    Fallback to SERVER_AUTH_FAILURE for unrecognized signals.
    """
    lower = error_text.lower()
    if "lock" in lower and (
        "unavailable" in lower or "timeout" in lower or "held" in lower
    ):
        return SyncDiagnosticCode.LOCK_UNAVAILABLE
    if (
        "refreshing" in lower
        or "auth session" in lower
        or ("refresh" in lower and "progress" in lower)
    ):
        return SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS
    if "websocket" in lower or ("ws" in lower and "offline" in lower):
        return SyncDiagnosticCode.WEBSOCKET_OFFLINE
    if "event loop" in lower or "interpreter" in lower or "shutdown" in lower:
        return SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE
    if "401" in lower or "unauthorized" in lower or "auth" in lower or "token" in lower:
        return SyncDiagnosticCode.SERVER_AUTH_FAILURE
    return SyncDiagnosticCode.SERVER_AUTH_FAILURE


def reset_emitted_codes() -> None:
    """Clear deduplication state. For testing only; do not call in production code."""
    global _diagnostic_emitted
    _diagnostic_emitted = False


def _coerce_diagnostic(
    code: SyncDiagnosticCode | SyncDiagnostic,
    message: str | None,
) -> tuple[SyncDiagnosticCode, str]:
    """Coerce legacy SyncDiagnostic payloads onto the canonical enum contract."""
    if isinstance(code, SyncDiagnosticCode):
        return code, message or ""

    diagnostic_message = code.message if message is None else message
    if code.diagnostic_code == SyncDiagnosticCode.LOCK_UNAVAILABLE.value:
        return SyncDiagnosticCode.LOCK_UNAVAILABLE, diagnostic_message
    if code.diagnostic_code == SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS.value:
        return SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS, diagnostic_message
    if code.diagnostic_code == SyncDiagnosticCode.WEBSOCKET_OFFLINE.value:
        return SyncDiagnosticCode.WEBSOCKET_OFFLINE, diagnostic_message
    if code.diagnostic_code in {
        "sync.final_sync_shutdown_unavailable",
        "sync.final_sync_timeout",
    }:
        return SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE, diagnostic_message
    return classify_sync_error(diagnostic_message), diagnostic_message


__all__ = [
    "SyncDiagnostic",
    "SyncDiagnosticCode",
    "classify_sync_error",
    "emit_sync_diagnostic",
    "reset_emitted_codes",
]
