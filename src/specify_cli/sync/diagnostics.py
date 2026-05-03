"""Structured sync diagnostics with per-invocation dedupe."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from specify_cli.diagnostics import report_once

from .diagnose import emit_diagnostic

SyncSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class SyncDiagnostic:
    """Diagnostic emitted by sync side effects without changing command result."""

    severity: SyncSeverity
    diagnostic_code: str
    message: str
    fatal: bool
    sync_phase: str

    @property
    def dedupe_key(self) -> str:
        """Return the contract key for one-render-per-invocation behavior."""
        return "|".join(
            (
                self.diagnostic_code,
                self.sync_phase,
                _normalize_message(self.message),
            )
        )


def emit_sync_diagnostic(
    diagnostic: SyncDiagnostic,
    *,
    json_mode: bool = False,
    envelope: dict[str, object] | None = None,
) -> bool:
    """Render a sync diagnostic once for the current invocation.

    The rendered line includes the required contract fields and routes
    through the sync diagnostic helper, which keeps stdout parseable by
    sending non-envelope diagnostics to stderr.
    """
    if not report_once(f"sync-diagnostic:{diagnostic.dedupe_key}"):
        return False

    emit_diagnostic(
        _render_sync_diagnostic(diagnostic),
        category="sync",
        json_mode=json_mode,
        envelope=envelope,
    )
    return True


def _render_sync_diagnostic(diagnostic: SyncDiagnostic) -> str:
    """Render a compact, grep-friendly diagnostic line."""
    fatal = "true" if diagnostic.fatal else "false"
    return (
        "sync_diagnostic "
        f"severity={diagnostic.severity} "
        f"diagnostic_code={diagnostic.diagnostic_code} "
        f"fatal={fatal} "
        f"sync_phase={diagnostic.sync_phase} "
        f"message={diagnostic.message}"
    )


def _normalize_message(message: str) -> str:
    """Normalize whitespace and volatile repr quoting for dedupe keys."""
    return re.sub(r"\s+", " ", message).strip().lower()
