"""Loopback-only HTTP helpers for local control planes."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlunsplit

__all__ = [
    "build_loopback_base_url",
    "build_loopback_url",
    "create_loopback_server",
    "serve_loopback_server",
]

LOOPBACK_HOST = "127.0.0.1"


def build_loopback_base_url(port: int) -> str:
    """Return the loopback origin (no trailing slash) for path concatenation."""
    return f"http://{LOOPBACK_HOST}:{port}"


def build_loopback_url(port: int, path: str) -> str:
    """Return an HTTP URL scoped to the IPv4 loopback interface."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return urlunsplit(("http", f"{LOOPBACK_HOST}:{port}", normalized_path, "", ""))


def create_loopback_server(
    port: int,
    handler_class: type[BaseHTTPRequestHandler],
    *,
    server_factory: type[HTTPServer] = HTTPServer,
) -> HTTPServer:
    """Create a loopback-bound HTTP server with an explicit binding contract."""
    return server_factory((LOOPBACK_HOST, port), handler_class)


def serve_loopback_server(
    port: int,
    handler_class: type[BaseHTTPRequestHandler],
    *,
    server_factory: type[HTTPServer] = HTTPServer,
) -> None:
    """Create, bind, and serve a loopback-only HTTP server forever."""
    server = create_loopback_server(port, handler_class, server_factory=server_factory)
    server.serve_forever()
