"""API-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
from pathlib import Path

from ..constitution_path import resolve_project_constitution_path
from ..diagnostics import run_diagnostics
from ..scanner import format_path_for_display, resolve_active_mission, scan_all_missions
from specify_cli.core.mission_detection import detect_mission
from ..templates import get_dashboard_html
from .base import DashboardHandler
from specify_cli.mission import MissionError, get_mission_by_name

__all__ = ["APIHandler"]


class APIHandler(DashboardHandler):
    """Serve dashboard root, health, diagnostics, and shutdown endpoints."""

    def handle_root(self) -> None:
        """Return the rendered dashboard HTML shell."""
        project_path = Path(self.project_dir).resolve()

        # Derive active mission from the most active mission (per-mission mission model)
        mission_context = {
            'name': 'No active mission',
            'domain': 'unknown',
            'version': '',
            'slug': '',
            'description': '',
            'path': '',
        }

        try:
            missions = scan_all_missions(project_path)

            active_mission = resolve_active_mission(project_path, missions)

            if active_mission:
                mission_type_key = active_mission.get('meta', {}).get('mission', 'software-dev')
                kittify_dir = project_path / ".kittify"
                mission = get_mission_by_name(mission_type_key, kittify_dir)
                mission_context = {
                    'name': mission.name,
                    'domain': mission.config.domain,
                    'version': mission.config.version,
                    'slug': mission.path.name,
                    'description': mission.config.description or '',
                    'path': format_path_for_display(str(mission.path)),
                }
        except (MissionError, Exception):
            pass  # Keep default "No active mission" context

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
            project_path = Path(self.project_dir).resolve()
            # Detect active mission to resolve per-mission mission context.
            # Use detect_mission() directly — resolve_active_mission() falls
            # back to the first scanned mission when detection fails, which
            # would bind diagnostics to an arbitrary mission on integration branches.
            mission_dir = None
            try:
                context = detect_mission(project_path, cwd=project_path, mode="lenient")
                if context and context.directory and context.directory.is_dir():
                    mission_dir = context.directory
            except Exception:  # noqa: S110 – mission detection is best-effort
                pass  # Diagnostics should still run without mission context
            diagnostics = run_diagnostics(project_path, mission_dir=mission_dir)
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
        """Serve project-level constitution from new path with legacy fallback."""
        try:
            constitution_path = resolve_project_constitution_path(Path(self.project_dir))

            if not constitution_path:
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

    def handle_dossier(self, path: str) -> None:
        """Route dossier API requests to appropriate endpoints.

        Routes:
        - /api/dossier/overview?mission={slug} -> GET overview
        - /api/dossier/artifacts?mission={slug}&class={class}&... -> GET list
        - /api/dossier/artifacts/{artifact_key}?mission={slug} -> GET detail
        - /api/dossier/snapshots/export?mission={slug} -> GET export
        """
        import urllib.parse
        from specify_cli.dossier.api import DossierAPIHandler

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Extract mission_slug from query params
        mission_slug = query.get('mission', [None])[0]
        if not mission_slug:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing mission parameter'}).encode())
            return

        try:
            # Initialize dossier handler
            repo_root = Path(self.project_dir).resolve()
            handler = DossierAPIHandler(repo_root)

            # Route to appropriate endpoint
            if path == '/api/dossier/overview':
                response = handler.handle_dossier_overview(mission_slug)
            elif path == '/api/dossier/artifacts':
                # Extract filters from query
                filters = {}
                if 'class' in query:
                    filters['class'] = query['class'][0]
                if 'wp_id' in query:
                    filters['wp_id'] = query['wp_id'][0]
                if 'step_id' in query:
                    filters['step_id'] = query['step_id'][0]
                if 'required_only' in query:
                    filters['required_only'] = query['required_only'][0]
                response = handler.handle_dossier_artifacts(mission_slug, **filters)
            elif path.startswith('/api/dossier/artifacts/'):
                # Extract artifact_key from path
                artifact_key = path.split('/api/dossier/artifacts/')[-1]
                response = handler.handle_dossier_artifact_detail(mission_slug, artifact_key)
            elif path == '/api/dossier/snapshots/export':
                response = handler.handle_dossier_snapshot_export(mission_slug)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Dossier endpoint not found'}).encode())
                return

            # Check if response is an error dict (has 'error' key and optional 'status_code')
            if isinstance(response, dict) and 'error' in response:
                status_code = response.get('status_code', 500)
                self.send_response(status_code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                # Success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                # Use the model's dict() method if available, otherwise direct JSON
                if hasattr(response, 'dict'):
                    self.wfile.write(json.dumps(response.dict(), default=str).encode())
                else:
                    self.wfile.write(json.dumps(response, default=str).encode())
        except Exception as exc:
            import traceback
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_msg = {
                'error': f'Dossier handler error: {str(exc)}',
                'traceback': traceback.format_exc(),
            }
            self.wfile.write(json.dumps(error_msg).encode())
