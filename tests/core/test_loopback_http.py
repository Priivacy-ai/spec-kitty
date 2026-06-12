"""Direct coverage for the loopback-only HTTP helpers.

These tests pin the security-relevant invariant of the module: every server
it produces binds the IPv4 loopback interface, with no way for a caller to
widen the bind address.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from specify_cli.core.loopback_http import (
    LOOPBACK_HOST,
    build_loopback_base_url,
    build_loopback_url,
    create_loopback_server,
    serve_loopback_server,
)

pytestmark = [pytest.mark.unit]


class _RecordingServer(HTTPServer):
    """Records the bind address and serve_forever calls without binding a socket."""

    instances: list[_RecordingServer] = []

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        self.bound_address = server_address
        self.handler_class = handler_class
        self.serve_forever_calls: list[float | None] = []
        _RecordingServer.instances.append(self)
        # Intentionally skip HTTPServer.__init__ so no real socket is bound.

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        self.serve_forever_calls.append(poll_interval)


class _Handler(BaseHTTPRequestHandler):
    pass


def setup_function() -> None:
    _RecordingServer.instances.clear()


def test_build_loopback_url_uses_loopback_host_and_given_path() -> None:
    assert build_loopback_url(8123, "/api/health") == "http://127.0.0.1:8123/api/health"


def test_build_loopback_url_normalizes_missing_leading_slash() -> None:
    assert build_loopback_url(8123, "api/health") == "http://127.0.0.1:8123/api/health"


def test_build_loopback_base_url_has_no_trailing_slash() -> None:
    assert build_loopback_base_url(9999) == "http://127.0.0.1:9999"


def test_create_loopback_server_binds_loopback_only() -> None:
    server = create_loopback_server(8123, _Handler, server_factory=_RecordingServer)

    assert isinstance(server, _RecordingServer)
    assert server.bound_address == (LOOPBACK_HOST, 8123)
    assert server.bound_address[0] == "127.0.0.1"
    assert server.handler_class is _Handler
    assert server.serve_forever_calls == []


def test_serve_loopback_server_binds_loopback_and_serves_forever() -> None:
    serve_loopback_server(8124, _Handler, server_factory=_RecordingServer)

    assert len(_RecordingServer.instances) == 1
    server = _RecordingServer.instances[0]
    assert server.bound_address == ("127.0.0.1", 8124)
    assert server.handler_class is _Handler
    assert len(server.serve_forever_calls) == 1
