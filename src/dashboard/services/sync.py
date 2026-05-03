"""Sync daemon orchestration service."""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _build_trigger_request(base_url: str, token: str) -> urllib.request.Request:
    """Build a sync-daemon request for the local loopback daemon only."""
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http":
        raise ValueError("sync daemon must use http")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("sync daemon must bind to loopback")
    trigger_url = urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/api/sync/trigger", "", "", "")
    )
    return urllib.request.Request(
        trigger_url,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )


@dataclass
class SyncTriggerResult:
    """Result of a sync trigger attempt.

    Carries everything the adapter needs to write the HTTP response: the
    status code and the JSON body. Handlers should call ``body()`` rather
    than re-interpreting ``status``/``reason``/``error`` themselves so the
    adapter stays a single-call thin adapter (FR-007 of the parent
    dashboard-service-extraction mission, completed by the follow-up).
    """

    status: str
    http_status: int
    manual_mode: bool = field(default=False)
    reason: str | None = field(default=None)
    error: str | None = field(default=None)

    def body(self) -> dict[str, Any]:
        """Return the JSON body the adapter should send for this result."""
        if self.status == "scheduled":
            return {"status": "scheduled"}
        if self.status == "skipped":
            return {
                "status": "skipped",
                "manual_mode": self.manual_mode,
                "reason": self.reason,
            }
        if self.status == "unavailable":
            payload: dict[str, Any] = {"error": self.error or "sync_daemon_unavailable"}
            if self.reason is not None:
                payload["reason"] = self.reason
            return payload
        return {"error": self.error or "sync_trigger_failed"}


class SyncService:
    """Orchestrates sync daemon startup and trigger."""

    def __init__(
        self,
        *,
        _ensure_running: Callable[..., Any] | None = None,
        _get_daemon_status: Callable[..., Any] | None = None,
    ) -> None:
        from specify_cli.sync.daemon import ensure_sync_daemon_running, get_sync_daemon_status

        self._ensure_running = (
            _ensure_running if _ensure_running is not None else ensure_sync_daemon_running
        )
        self._get_daemon_status = (
            _get_daemon_status if _get_daemon_status is not None else get_sync_daemon_status
        )

    def trigger_sync(self, token: str | None = None) -> SyncTriggerResult:
        """Ensure the daemon is running and ask it to flush soon."""
        from specify_cli.sync.daemon import DaemonIntent

        try:
            outcome = self._ensure_running(intent=DaemonIntent.REMOTE_REQUIRED)
            if not outcome.started:
                reason = outcome.skipped_reason or "unknown"
                if reason in {"rollout_disabled", "policy_manual"}:
                    return SyncTriggerResult(
                        status="skipped", http_status=202, manual_mode=True, reason=reason
                    )
                return SyncTriggerResult(
                    status="unavailable",
                    http_status=503,
                    error="sync_daemon_unavailable",
                    reason=reason,
                )

            status = self._get_daemon_status(timeout=0.2)
            if not status.healthy or not status.url or not status.token:
                return SyncTriggerResult(
                    status="unavailable", http_status=503, error="sync_daemon_unavailable"
                )

            request = _build_trigger_request(status.url, status.token)
            with urllib.request.urlopen(request, timeout=0.5) as resp:  # nosec B310 — URL is localhost daemon endpoint
                if resp.status not in {200, 202}:
                    return SyncTriggerResult(
                        status="failed", http_status=500, error="sync_trigger_failed"
                    )

            return SyncTriggerResult(status="scheduled", http_status=202)

        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("SyncService trigger failed")
            return SyncTriggerResult(status="failed", http_status=500, error="sync_trigger_failed")
