"""API-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

from ..api_types import HealthResponse
from ..charter_path import resolve_project_charter_path
from ..diagnostics import run_diagnostics
from ..templates import get_dashboard_html_bytes
from .base import DashboardHandler
from specify_cli.sync.daemon import ensure_sync_daemon_running, get_sync_daemon_status

__all__ = ["APIHandler"]

logger = logging.getLogger(__name__)


def _build_sync_trigger_request(base_url: str, token: str) -> urllib.request.Request:
    """Build a sync-daemon request for the local loopback daemon only."""
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http":
        raise ValueError("sync daemon must use http")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("sync daemon must bind to loopback")

    trigger_url = urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "/api/sync/trigger",
            "",
            "",
            "",
        )
    )
    return urllib.request.Request(
        trigger_url,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )


class APIHandler(DashboardHandler):
    """Serve dashboard root, health, diagnostics, and shutdown endpoints."""

    def handle_root(self) -> None:
        """Return the rendered dashboard HTML shell."""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(get_dashboard_html_bytes())

    def handle_health(self) -> None:
        """Return project health metadata."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            project_path = str(Path(self.project_dir).resolve())
        except Exception:
            project_path = str(self.project_dir)

        response_data: HealthResponse = {
            "status": "ok",
            "project_path": project_path,
        }

        try:
            status = get_sync_daemon_status(timeout=0.2)
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

        token = getattr(self, "project_token", None)
        if token:
            response_data["token"] = token

        self.wfile.write(json.dumps(response_data).encode())

    def handle_shutdown(self) -> None:
        """Delegate to the shared shutdown helper."""
        self._handle_shutdown()

    def handle_sync_trigger(self) -> None:
        """Ask the machine-global sync daemon to flush soon."""
        expected_token = getattr(self, "project_token", None)
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        token_values = params.get("token")
        token = token_values[0] if token_values else None

        if expected_token and token != expected_token:
            self._send_json(403, {"error": "invalid_token"})
            return

        try:
            ensure_sync_daemon_running()
            status = get_sync_daemon_status(timeout=0.2)
            if not status.healthy or not status.url or not status.token:
                self._send_json(503, {"error": "sync_daemon_unavailable"})
                return
            request = _build_sync_trigger_request(status.url, status.token)
            with urllib.request.urlopen(request, timeout=0.5) as response:
                if response.status not in {200, 202}:
                    self._send_json(500, {"error": "sync_trigger_failed", "status": response.status})
                    return
            self._send_json(202, {"status": "scheduled"})
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("Dashboard sync trigger failed")
            self._send_json(500, {"error": "sync_trigger_failed"})

    def handle_diagnostics(self) -> None:
        """Run diagnostics and report JSON payloads (or errors)."""
        try:
            project_path = Path(self.project_dir).resolve()
            # Detect active feature to resolve per-feature mission context.
            # Use detect_feature() directly — resolve_active_feature() falls
            # back to the first scanned feature when detection fails, which
            # would bind diagnostics to an arbitrary feature on integration branches.
            # feature_dir is None without an explicit feature slug; diagnostics run without it
            feature_dir: Path | None = None
            diagnostics = run_diagnostics(project_path, feature_dir=feature_dir)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(diagnostics).encode())
        except Exception:  # pragma: no cover - fallback safety
            logger.exception("Dashboard diagnostics failed")
            self._send_json(500, {"error": "diagnostics_failed"})

    def handle_charter(self) -> None:
        """Serve project-level charter from new path with legacy fallback."""
        try:
            charter_path = resolve_project_charter_path(Path(self.project_dir))

            if not charter_path:
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Charter not found")
                return

            content = charter_path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception:  # pragma: no cover - fallback safety
            logger.exception("Dashboard charter load failed")
            self.send_response(500)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Error loading charter")

    def handle_dossier(self, _path: str) -> None:
        """Route dossier API requests to appropriate endpoints.

        Routes:
        - /api/dossier/overview?feature={mission_slug} -> GET overview
        - /api/dossier/artifacts?feature={mission_slug}&class={class}&... -> GET list
        - /api/dossier/artifacts/{artifact_key}?feature={mission_slug} -> GET detail
        - /api/dossier/snapshots/export?feature={mission_slug} -> GET export
        """
        import urllib.parse
        from specify_cli.dossier.api import DossierAPIHandler

        parsed = urllib.parse.urlparse(self.path)
        resolved_path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Extract mission_slug from query params
        mission_slug = query.get("feature", [None])[0]
        if not mission_slug:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing feature parameter"}).encode())
            return

        try:
            # Initialize dossier handler
            repo_root = Path(self.project_dir).resolve()
            handler = DossierAPIHandler(repo_root)

            # Route to appropriate endpoint
            if resolved_path == "/api/dossier/overview":
                response = handler.handle_dossier_overview(mission_slug)
            elif resolved_path == "/api/dossier/artifacts":
                # Extract filters from query
                filters = {}
                if "class" in query:
                    filters["class"] = query["class"][0]
                if "wp_id" in query:
                    filters["wp_id"] = query["wp_id"][0]
                if "step_id" in query:
                    filters["step_id"] = query["step_id"][0]
                if "required_only" in query:
                    filters["required_only"] = query["required_only"][0]
                response = handler.handle_dossier_artifacts(mission_slug, **filters)
            elif resolved_path.startswith("/api/dossier/artifacts/"):
                # Extract artifact_key from resolved_path
                artifact_key = resolved_path.split("/api/dossier/artifacts/")[-1]
                response = handler.handle_dossier_artifact_detail(mission_slug, artifact_key)
            elif resolved_path == "/api/dossier/snapshots/export":
                response = handler.handle_dossier_snapshot_export(mission_slug)
            else:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Dossier endpoint not found"}).encode())
                return

            # Check if response is an error dict (has 'error' key and optional 'status_code')
            if isinstance(response, dict) and "error" in response:
                status_code = response.get("status_code", 500)
                self.send_response(status_code)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                # Success response
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                # Use the model's dict() method if available, otherwise direct JSON
                if hasattr(response, "dict"):
                    self.wfile.write(json.dumps(response.dict(), default=str).encode())
                else:
                    self.wfile.write(json.dumps(response, default=str).encode())
        except Exception:
            logger.exception("Dashboard dossier handler failed")
            self._send_json(500, {"error": "dossier_handler_failed"})
