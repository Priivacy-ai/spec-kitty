"""Dispatch tests for glossary and lint dashboard routes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.fast

_ROUTE_HANDLERS = (
    "handle_glossary_page",
    "handle_glossary_health",
    "handle_glossary_terms",
    "handle_charter_lint",
)


@pytest.mark.parametrize(
    ("path", "expected_handler"),
    [
        ("/glossary", "handle_glossary_page"),
        ("/api/glossary-health", "handle_glossary_health"),
        ("/api/glossary-terms", "handle_glossary_terms"),
        ("/api/charter-lint", "handle_charter_lint"),
    ],
)
def test_router_dispatches_glossary_and_lint_routes(path, expected_handler):
    """New dashboard routes dispatch to their dedicated handlers."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.path = path
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()

    for handler_name in _ROUTE_HANDLERS:
        setattr(handler, handler_name, MagicMock())

    DashboardRouter.do_GET(handler)

    getattr(handler, expected_handler).assert_called_once_with()
    handler.send_response.assert_not_called()
    handler.end_headers.assert_not_called()

    for handler_name in _ROUTE_HANDLERS:
        if handler_name != expected_handler:
            getattr(handler, handler_name).assert_not_called()


def test_router_dispatches_post_routes():
    """POST routes use exact-match dispatch and avoid 404 handling."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.path = "/api/shutdown"
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()
    handler.handle_shutdown = MagicMock()
    handler.handle_sync_trigger = MagicMock()

    DashboardRouter.do_POST(handler)

    handler.handle_shutdown.assert_called_once_with()
    handler.handle_sync_trigger.assert_not_called()
    handler.send_response.assert_not_called()
    handler.end_headers.assert_not_called()


def test_router_returns_404_for_unknown_post_route():
    """Unknown POST routes must fall through to a 404 response."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.path = "/api/unknown"
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()
    handler.handle_shutdown = MagicMock()
    handler.handle_sync_trigger = MagicMock()

    DashboardRouter.do_POST(handler)

    handler.handle_shutdown.assert_not_called()
    handler.handle_sync_trigger.assert_not_called()
    handler.send_response.assert_called_once_with(404)
    handler.end_headers.assert_called_once_with()


def test_dispatch_exact_returns_false_when_no_route_matches():
    """Exact dispatch reports misses without invoking handlers."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.handle_root = MagicMock()

    matched = DashboardRouter._dispatch_exact(handler, "/missing", DashboardRouter._get_routes())

    assert matched is False
    handler.handle_root.assert_not_called()


def test_dispatch_prefix_routes_path_argument():
    """Prefix dispatch forwards the original path to the matched handler."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.handle_static = MagicMock()

    matched = DashboardRouter._dispatch_prefix(handler, "/static/dashboard/app.js", DashboardRouter._prefix_get_routes())

    assert matched is True
    handler.handle_static.assert_called_once_with("/static/dashboard/app.js")


def test_dispatch_prefix_returns_false_when_no_prefix_matches():
    """Prefix dispatch reports misses without invoking handlers."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.handle_static = MagicMock()

    matched = DashboardRouter._dispatch_prefix(handler, "/not-static", DashboardRouter._prefix_get_routes())

    assert matched is False
    handler.handle_static.assert_not_called()
