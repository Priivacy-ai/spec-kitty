"""API-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
from pathlib import Path

from ..diagnostics import run_diagnostics
from ..scanner import format_path_for_display, resolve_active_feature, scan_all_features
from ..templates import get_dashboard_html
from .base import DashboardHandler
from specify_cli.mission_system import MissionError, get_mission_by_name

__all__ = ["APIHandler"]


class APIHandler(DashboardHandler):
    """Serve dashboard root, health, diagnostics, and shutdown endpoints."""

    def handle_root(self) -> None:
        """Return the rendered dashboard HTML shell."""
        project_path = Path(self.project_dir).resolve()

        # Derive active mission from the most active feature (per-feature mission model)
        mission_context = {
            'name': 'No active feature',
            'domain': 'unknown',
            'version': '',
            'slug': '',
            'description': '',
            'path': '',
        }

        try:
            features = scan_all_features(project_path)

            active_feature = resolve_active_feature(project_path, features)

            if active_feature:
                feature_mission_key = active_feature.get('meta', {}).get('mission', 'software-dev')
                kittify_dir = project_path / ".kittify"
                mission = get_mission_by_name(feature_mission_key, kittify_dir)
                mission_context = {
                    'name': mission.name,
                    'domain': mission.config.domain,
                    'version': mission.config.version,
                    'slug': mission.path.name,
                    'description': mission.config.description or '',
                    'path': format_path_for_display(str(mission.path)),
                }
        except (MissionError, Exception):
            pass  # Keep default "No active feature" context

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
