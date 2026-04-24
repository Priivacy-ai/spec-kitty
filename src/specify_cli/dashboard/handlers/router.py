"""Router that dispatches HTTP requests to specialized handlers."""

from __future__ import annotations

import urllib.parse

from .api import APIHandler
from .features import FeatureHandler
from .glossary import GlossaryHandler
from .lint import LintTileHandler
from .static import STATIC_URL_PREFIX, StaticHandler

__all__ = ["DashboardRouter"]


class DashboardRouter(APIHandler, FeatureHandler, GlossaryHandler, LintTileHandler, StaticHandler):
    """Dispatch GET/POST requests to API, feature, or static handlers."""

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler signature)
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if DashboardRouter._dispatch_exact(self, path, DashboardRouter._post_routes()):
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802, C901
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if DashboardRouter._dispatch_exact(self, path, DashboardRouter._get_routes()) or DashboardRouter._dispatch_prefix(
            self, path, DashboardRouter._prefix_get_routes()
        ):
            return

        self.send_response(404)
        self.end_headers()

    def _dispatch_exact(self, path: str, routes: tuple[tuple[str, str], ...]) -> bool:
        for route, handler_name in routes:
            if path == route:
                getattr(self, handler_name)()
                return True
        return False

    def _dispatch_prefix(self, path: str, routes: tuple[tuple[str, str], ...]) -> bool:
        for prefix, handler_name in routes:
            if path.startswith(prefix):
                getattr(self, handler_name)(path)
                return True
        return False

    @staticmethod
    def _post_routes() -> tuple[tuple[str, str], ...]:
        return (
            ('/api/shutdown', 'handle_shutdown'),
            ('/api/sync/trigger', 'handle_sync_trigger'),
        )

    @staticmethod
    def _get_routes() -> tuple[tuple[str, str], ...]:
        return (
            ('/', 'handle_root'),
            ('/api/health', 'handle_health'),
            ('/api/shutdown', 'handle_shutdown'),
            ('/api/sync/trigger', 'handle_sync_trigger'),
            ('/api/features', 'handle_features_list'),
            ('/api/diagnostics', 'handle_diagnostics'),
            ('/api/charter', 'handle_charter'),
            ('/glossary', 'handle_glossary_page'),
            ('/api/glossary-health', 'handle_glossary_health'),
            ('/api/glossary-terms', 'handle_glossary_terms'),
            ('/api/charter-lint', 'handle_charter_lint'),
        )

    @staticmethod
    def _prefix_get_routes() -> tuple[tuple[str, str], ...]:
        return (
            ('/api/kanban/', 'handle_kanban'),
            ('/api/research/', 'handle_research'),
            ('/api/contracts/', 'handle_contracts'),
            ('/api/checklists/', 'handle_checklists'),
            ('/api/artifact/', 'handle_artifact'),
            ('/api/dossier/', 'handle_dossier'),
            (STATIC_URL_PREFIX, 'handle_static'),
        )
