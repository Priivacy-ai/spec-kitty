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


@pytest.mark.parametrize("method", ["do_GET", "do_POST"])
def test_router_404s_for_deleted_sync_trigger_route(method):
    """/api/sync/trigger was deleted; both do_GET and do_POST must 404 at dispatch.

    Guards against a branch rebinding the deleted handler under a different
    method name: only a dispatch-level assertion catches that, unlike the
    method-existence and source-string checks in test_api_handler.py.
    """
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.path = "/api/sync/trigger"
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()

    getattr(DashboardRouter, method)(handler)

    handler.send_response.assert_called_once_with(404)
    handler.end_headers.assert_called_once_with()


@pytest.mark.parametrize("method", ["do_GET", "do_POST"])
def test_router_dispatches_shutdown_route(method):
    """/api/shutdown dispatches to handle_shutdown on both do_GET and do_POST."""
    from specify_cli.dashboard.handlers.router import DashboardRouter

    handler = MagicMock()
    handler.path = "/api/shutdown"
    handler.handle_shutdown = MagicMock()
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()

    getattr(DashboardRouter, method)(handler)

    handler.handle_shutdown.assert_called_once_with()
    handler.send_response.assert_not_called()
    handler.end_headers.assert_not_called()
