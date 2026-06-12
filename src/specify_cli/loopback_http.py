"""Loopback-only HTTP helpers for local control planes."""

from __future__ import annotations

from collections.abc import Callable
from http.server import HTTPServer
from typing import Any
from urllib.parse import urlunsplit

LOOPBACK_HOST = "127.0.0.1"


def build_loopback_url(port: int, path: str) -> str:
    """Return an HTTP URL scoped to the IPv4 loopback interface."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return urlunsplit(("http", f"{LOOPBACK_HOST}:{port}", normalized_path, "", ""))


def create_loopback_server(
    port: int,
    handler_class: type[Any],
    *,
    server_factory: type[HTTPServer] = HTTPServer,
) -> HTTPServer:
    """Create a loopback-bound HTTP server with an explicit binding contract."""
    return server_factory((LOOPBACK_HOST, port), handler_class)


def serve_loopback_server(
    port: int,
    handler_class: type[Any],
    *,
    on_bound: Callable[[HTTPServer], None] | None = None,
    poll_interval: float | None = None,
    server_factory: type[HTTPServer] = HTTPServer,
) -> None:
    """Create, bind, and serve a loopback-only HTTP server forever."""
    server = create_loopback_server(port, handler_class, server_factory=server_factory)
    if on_bound is not None:
        on_bound(server)
    if poll_interval is None:
        server.serve_forever()
        return
    server.serve_forever(poll_interval=poll_interval)
