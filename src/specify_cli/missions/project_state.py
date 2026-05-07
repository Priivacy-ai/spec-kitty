"""Project health state service (canonical home).

Canonical location: ``specify_cli.missions.project_state``.

This module owns the ``ProjectStateService`` that assembles the project health
payload exposed by the dashboard HTTP surface. It belongs to the mission
domain layer because it interprets project-level sync daemon state
independently of any HTTP / dashboard wiring.

A backward-compatibility shim remains at ``dashboard.services.project_state``
re-exporting ``ProjectStateService``; that shim is scheduled for removal in
release ``3.2.0``. Do not add business logic to the shim — edit this module
instead.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from kernel.api_types import HealthResponse


class ProjectStateService:
    """Assembles the project health payload."""

    def __init__(
        self,
        project_dir: Path,
        *,
        _get_daemon_status: Callable[..., Any] | None = None,
    ) -> None:
        from specify_cli.sync.daemon import get_sync_daemon_status

        self._project_dir = project_dir.resolve()
        self._get_daemon_status = (
            _get_daemon_status if _get_daemon_status is not None else get_sync_daemon_status
        )

    def get_health(self, token: str | None = None) -> HealthResponse:
        """Return project health payload.

        Args:
            token: Per-project auth token; included in response only when non-None.
        """
        response_data: HealthResponse = {
            "status": "ok",
            "project_path": str(self._project_dir),
        }

        try:
            status = self._get_daemon_status(timeout=0.2)
            response_data["sync"] = {
                "running": status.sync_running,
                "last_sync": status.last_sync,
                "consecutive_failures": status.consecutive_failures,
            }
            response_data["websocket_status"] = status.websocket_status
        except Exception as exc:  # pragma: no cover - diagnostic fallback
            response_data["sync"] = {
                "running": False,
                "error": str(exc),
            }
            response_data["websocket_status"] = "Offline"

        if token is not None:
            response_data["token"] = token

        return response_data
