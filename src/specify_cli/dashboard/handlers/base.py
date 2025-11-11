"""Base HTTP handler for the Spec Kitty dashboard."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional

from ..diagnostics import run_diagnostics
from ..scanner import (
    format_path_for_display,
    resolve_feature_dir,
    scan_all_features,
    scan_feature_kanban,
)
from ..templates import get_dashboard_html

STATIC_URL_PREFIX = '/static/'
STATIC_DIR = (Path(__file__).resolve().parents[1] / 'static').resolve()


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    project_dir: Optional[str] = None
    project_token: Optional[str] = None

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - signature from BaseHTTPRequestHandler
        """Suppress request logging."""
        del format, args

    # Core helpers ---------------------------------------------------------

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        """Return JSON response with standard headers."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _handle_shutdown(self) -> None:
        """Handle shutdown requests."""
        expected_token = getattr(self, 'project_token', None)

        token = None
        if self.command == 'POST':
            content_length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(content_length) if content_length else b''
            if body:
                try:
                    payload = json.loads(body.decode('utf-8'))
                    token = payload.get('token')
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_json(400, {'error': 'invalid_payload'})
                    return
        else:
            parsed_path = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_path.query)
            token_values = params.get('token')
            if token_values:
                token = token_values[0]

        if expected_token and token != expected_token:
            self._send_json(403, {'error': 'invalid_token'})
            return

        self._send_json(200, {'status': 'stopping'})

        def shutdown_server(server):
            time.sleep(0.05)  # allow response to flush
            server.shutdown()

        threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()

    # HTTP methods ---------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802 (standard library name)
        """Handle POST requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/shutdown':
            self._handle_shutdown()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(get_dashboard_html().encode())
            return

        if path == '/api/health':
            self._handle_health()
            return

        if path == '/api/shutdown':
            self._handle_shutdown()
            return

        if path == '/api/features':
            self._handle_features()
            return

        if path.startswith('/api/kanban/'):
            self._handle_kanban(path)
            return

        if path.startswith('/api/research/'):
            self._handle_research(path)
            return

        if path.startswith('/api/artifact/'):
            self._handle_artifact(path)
            return

        if path == '/api/diagnostics':
            self._handle_diagnostics()
            return

        if path.startswith(STATIC_URL_PREFIX):
            self._handle_static(path)
            return

        self.send_response(404)
        self.end_headers()

    # Route handlers -------------------------------------------------------

    def _handle_health(self) -> None:
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

    def _handle_features(self) -> None:
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        project_path = Path(self.project_dir).resolve()
        features = scan_all_features(project_path)

        worktrees_root_path = project_path / '.worktrees'
        try:
            worktrees_root_resolved = worktrees_root_path.resolve()
        except Exception:
            worktrees_root_resolved = worktrees_root_path

        try:
            current_path = Path.cwd().resolve()
        except Exception:
            current_path = Path.cwd()

        worktrees_root_exists = worktrees_root_path.exists()
        worktrees_root_display = (
            format_path_for_display(str(worktrees_root_resolved))
            if worktrees_root_exists
            else None
        )

        active_worktree_display: Optional[str] = None
        if worktrees_root_exists:
            try:
                current_path.relative_to(worktrees_root_resolved)
                active_worktree_display = format_path_for_display(str(current_path))
            except ValueError:
                active_worktree_display = None

        if not active_worktree_display and current_path != project_path:
            active_worktree_display = format_path_for_display(str(current_path))

        response = {
            'features': features,
            'project_path': format_path_for_display(str(project_path)),
            'worktrees_root': worktrees_root_display,
            'active_worktree': active_worktree_display,
        }
        self.wfile.write(json.dumps(response).encode())

    def _handle_kanban(self, path: str) -> None:
        parts = path.split('/')
        if len(parts) >= 4:
            feature_id = parts[3]
            project_path = Path(self.project_dir).resolve()
            kanban_data = scan_feature_kanban(project_path, feature_id)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(kanban_data).encode())
            return

        self.send_response(404)
        self.end_headers()

    def _handle_research(self, path: str) -> None:
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        feature_id = parts[3]
        project_path = Path(self.project_dir)
        feature_dir = resolve_feature_dir(project_path, feature_id)

        if len(parts) == 4:
            response = {'main_file': None, 'artifacts': []}

            if feature_dir:
                research_md = feature_dir / 'research.md'
                if research_md.exists():
                    try:
                        response['main_file'] = research_md.read_text(encoding='utf-8')
                    except UnicodeDecodeError as err:
                        error_msg = (
                            f'⚠️ **Encoding Error in research.md**\\n\\n'
                            f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                            'Please convert the file to UTF-8 encoding.\\n\\n'
                            'Attempting to read with error recovery...\\n\\n---\\n\\n'
                        )
                        response['main_file'] = error_msg + research_md.read_text(
                            encoding='utf-8', errors='replace'
                        )

                research_dir = feature_dir / 'research'
                if research_dir.exists() and research_dir.is_dir():
                    for file_path in sorted(research_dir.rglob('*')):
                        if file_path.is_file():
                            relative_path = str(file_path.relative_to(feature_dir))
                            icon = '📄'
                            if file_path.suffix == '.csv':
                                icon = '📊'
                            elif file_path.suffix == '.md':
                                icon = '📝'
                            elif file_path.suffix in ['.xlsx', '.xls']:
                                icon = '📈'
                            elif file_path.suffix == '.json':
                                icon = '📋'
                            response['artifacts'].append({
                                'name': file_path.name,
                                'path': relative_path,
                                'icon': icon,
                            })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        if len(parts) >= 5 and feature_dir:
            file_path_encoded = parts[4]
            file_path_str = urllib.parse.unquote(file_path_encoded)
            artifact_file = (feature_dir / file_path_str).resolve()

            try:
                artifact_file.relative_to(feature_dir.resolve())
            except ValueError:
                self.send_response(404)
                self.end_headers()
                return

            if artifact_file.exists() and artifact_file.is_file():
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                try:
                    content = artifact_file.read_text(encoding='utf-8')
                    self.wfile.write(content.encode('utf-8'))
                except UnicodeDecodeError as err:
                    error_msg = (
                        f'⚠️ Encoding Error in {artifact_file.name}\\n\\n'
                        f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                        'Please convert the file to UTF-8 encoding.\\n\\n'
                        'Attempting to read with error recovery...\\n\\n'
                    )
                    content = artifact_file.read_text(encoding='utf-8', errors='replace')
                    self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                except Exception as exc:
                    self.wfile.write(f'Error reading file: {exc}'.encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()

    def _handle_artifact(self, path: str) -> None:
        parts = path.split('/')
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return

        feature_id = parts[3]
        artifact_name = parts[4] if len(parts) > 4 else ''

        project_path = Path(self.project_dir)
        feature_dir = resolve_feature_dir(project_path, feature_id)

        artifact_map = {
            'spec': 'spec.md',
            'plan': 'plan.md',
            'tasks': 'tasks.md',
            'research': 'research.md',
            'quickstart': 'quickstart.md',
            'data-model': 'data-model.md',
        }

        filename = artifact_map.get(artifact_name)
        if feature_dir and filename:
            artifact_file = feature_dir / filename
            if artifact_file.exists():
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                try:
                    content = artifact_file.read_text(encoding='utf-8')
                    self.wfile.write(content.encode('utf-8'))
                except UnicodeDecodeError as err:
                    error_msg = (
                        f'⚠️ **Encoding Error in {filename}**\\n\\n'
                        f'This file contains non-UTF-8 characters at position {err.start}.\\n'
                        'Please convert the file to UTF-8 encoding.\\n\\n'
                        'Attempting to read with error recovery...\\n\\n---\\n\\n'
                    )
                    content = artifact_file.read_text(encoding='utf-8', errors='replace')
                    self.wfile.write(error_msg.encode('utf-8') + content.encode('utf-8'))
                except Exception as exc:
                    self.wfile.write(f'Error reading {filename}: {exc}'.encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()

    def _handle_diagnostics(self) -> None:
        try:
            diagnostics = run_diagnostics(Path(self.project_dir))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(diagnostics).encode())
        except Exception as exc:
            import traceback

            error_msg = {
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_msg).encode())

    def _handle_static(self, path: str) -> None:
        relative_path = path[len(STATIC_URL_PREFIX):]
        static_root = STATIC_DIR
        try:
            safe_path = (STATIC_DIR / relative_path).resolve()
        except (RuntimeError, ValueError):
            safe_path = None

        if not relative_path or not safe_path:
            self.send_response(404)
            self.end_headers()
            return

        try:
            safe_path.relative_to(static_root)
        except ValueError:
            self.send_response(404)
            self.end_headers()
            return

        if not safe_path.is_file():
            self.send_response(404)
            self.end_headers()
            return

        mime_type, _ = mimetypes.guess_type(safe_path.name)
        self.send_response(200)
        self.send_header('Content-type', mime_type or 'application/octet-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        with safe_path.open('rb') as static_file:
            self.wfile.write(static_file.read())
