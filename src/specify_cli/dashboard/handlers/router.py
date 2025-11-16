"""Router that dispatches HTTP requests to specialized handlers."""

from __future__ import annotations

import urllib.parse

from .api import APIHandler
from .features import FeatureHandler
from .static import STATIC_URL_PREFIX, StaticHandler

__all__ = ["DashboardRouter"]


class DashboardRouter(APIHandler, FeatureHandler, StaticHandler):
    """Dispatch GET/POST requests to API, feature, or static handlers."""

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler signature)
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/shutdown':
            self.handle_shutdown()
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.handle_root()
            return

        if path == '/api/health':
            self.handle_health()
            return

        if path == '/api/shutdown':
            self.handle_shutdown()
            return

        if path == '/api/features':
            self.handle_features_list()
            return

        if path.startswith('/api/kanban/'):
            self.handle_kanban(path)
            return

        if path.startswith('/api/research/'):
            self.handle_research(path)
            return

        if path.startswith('/api/artifact/'):
            self.handle_artifact(path)
            return

        if path == '/api/diagnostics':
            self.handle_diagnostics()
            return

        if path == '/api/constitution':
            self.handle_constitution()
            return

        if path.startswith(STATIC_URL_PREFIX):
            self.handle_static(path)
            return

        self.send_response(404)
        self.end_headers()
