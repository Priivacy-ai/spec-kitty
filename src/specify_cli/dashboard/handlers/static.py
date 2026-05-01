"""Static asset handler for the dashboard."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from .base import DashboardHandler

STATIC_URL_PREFIX = '/static/'
STATIC_DIR = (Path(__file__).resolve().parents[1] / 'static').resolve()

__all__ = ["STATIC_DIR", "STATIC_URL_PREFIX", "StaticHandler"]


class StaticHandler(DashboardHandler):
    """Serve files from the dashboard/static directory."""

    def handle_static(self, path: str) -> None:
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
