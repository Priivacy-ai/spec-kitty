"""The local Team Kitty double (Z1.md §4 preamble).

An in-process ``http.server.ThreadingHTTPServer``-based fixture that speaks
just enough of the F3 ``ControlEnvelope``/``LiveFrame`` transport surface for
Z1's own test suite: it accepts any POST/GET, records every request it
receives (method, path, headers, parsed JSON body), can be configured to
delay or fail its response, and counts connections/requests separately from
whether they were *acted on* by the client under test.

Precedent: ``tests/saas/conftest.py:159-172`` (``local_http_stub`` /
``_HeadOkHandler``) — same ``127.0.0.1:0`` OS-assigned-port pattern, extended
here to record request bodies and support configurable delay/status, per the
cross-repo ``provider_double`` convention (m1-contract-drafts/E1-L.md).

Never a real Docker Zeitgeist container — that is DKR-M1-02-ZEITGEIST/E1-L
territory (Z1.md §4 preamble); this double never leaves ``127.0.0.1``.
"""

from __future__ import annotations

import contextlib
import http.server
import json
import socket
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: Any


@dataclass
class TeamKittyDouble:
    """A minimal, in-process, loopback-only relay double."""

    requests: list[RecordedRequest] = field(default_factory=list)
    connection_count: int = 0
    response_status: int = 200
    response_body: dict[str, Any] = field(default_factory=dict)
    response_delay_s: float = 0.0

    _server: http.server.ThreadingHTTPServer | None = None
    _thread: threading.Thread | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def start(self) -> None:
        handler_cls = self._make_handler()
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address[:2]
        return f"http://127.0.0.1:{port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def configure(
        self,
        *,
        status: int | None = None,
        body: dict[str, Any] | None = None,
        delay_s: float | None = None,
    ) -> None:
        if status is not None:
            self.response_status = status
        if body is not None:
            self.response_body = body
        if delay_s is not None:
            self.response_delay_s = delay_s

    def _make_handler(self) -> type[http.server.BaseHTTPRequestHandler]:
        double = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _handle(self) -> None:
                with double._lock:
                    double.connection_count += 1
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b""
                parsed: Any = None
                if raw:
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        parsed = None
                with double._lock:
                    double.requests.append(
                        RecordedRequest(self.command, self.path, dict(self.headers), parsed)
                    )
                if double.response_delay_s:
                    time.sleep(double.response_delay_s)
                payload = json.dumps(double.response_body).encode("utf-8")
                self.send_response(double.response_status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(payload)

            def do_POST(self) -> None:  # noqa: N802
                self._handle()

            def do_GET(self) -> None:  # noqa: N802
                self._handle()

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        return _Handler


@pytest.fixture()
def team_kitty_double() -> Generator[TeamKittyDouble, None, None]:
    double = TeamKittyDouble()
    double.start()
    try:
        yield double
    finally:
        double.stop()


def closed_port_url() -> str:
    """A ``127.0.0.1`` URL with nothing listening — a real connection-refused
    target (N5), without depending on the OS refusing an entirely unused
    high port (which some sandboxes intercept)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"
