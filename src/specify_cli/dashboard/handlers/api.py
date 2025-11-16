"""API-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
from pathlib import Path

from ..diagnostics import run_diagnostics
from ..scanner import format_path_for_display
from ..templates import get_dashboard_html
from .base import DashboardHandler
from specify_cli.mission import MissionError, get_active_mission

__all__ = ["APIHandler"]


class APIHandler(DashboardHandler):
    """Serve dashboard root, health, diagnostics, and shutdown endpoints."""

    def handle_root(self) -> None:
        """Return the rendered dashboard HTML shell."""
        project_path = Path(self.project_dir).resolve()

        mission_context = {
            'name': 'Unknown mission',
            'domain': 'unknown',
            'version': '',
            'slug': '',
            'description': '',
            'path': '',
        }
        try:
            mission = get_active_mission(project_path)
            mission_context = {
                'name': mission.name,
                'domain': mission.domain,
                'version': mission.version,
                'slug': mission.path.name,
                'description': mission.description or '',
                'path': format_path_for_display(str(mission.path)),
            }
        except MissionError:
            pass

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(get_dashboard_html(mission_context=mission_context).encode())

    def handle_health(self) -> None:
        """Return project health metadata."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        try:
            project_path = str(Path(self.project_dir).resolve())
        except Exception:
            project_path = str(self.project_dir)

        response_data = {
            'status': 'ok',
            'project_path': project_path,
        }

        token = getattr(self, 'project_token', None)
        if token:
            response_data['token'] = token

        self.wfile.write(json.dumps(response_data).encode())

    def handle_shutdown(self) -> None:
        """Delegate to the shared shutdown helper."""
        self._handle_shutdown()

    def handle_diagnostics(self) -> None:
        """Run diagnostics and report JSON payloads (or errors)."""
        try:
            diagnostics = run_diagnostics(Path(self.project_dir))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(diagnostics).encode())
        except Exception as exc:  # pragma: no cover - fallback safety
            import traceback

            error_msg = {
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_msg).encode())

    def handle_constitution(self) -> None:
        """Serve project-level constitution from .kittify/memory/constitution.md"""
        try:
            constitution_path = Path(self.project_dir) / ".kittify" / "memory" / "constitution.md"

            if not constitution_path.exists():
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Constitution not found')
                return

            content = constitution_path.read_text(encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as exc:  # pragma: no cover - fallback safety
            import traceback

            error_msg = f"Error loading constitution: {exc}\n{traceback.format_exc()}"
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(error_msg.encode())
