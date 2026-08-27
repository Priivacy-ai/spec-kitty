"""Loopback-only HTTP helpers for local control planes.

Design rationale — loopback-only transport (127.0.0.1)
-------------------------------------------------------
All helpers in this module bind strictly to ``127.0.0.1`` (the IPv4 loopback
interface).  HTTPS is intentionally NOT used for this local control-plane
transport.  The relevant policy is the repo charter section "Loopback/local-only
HTTP is a special case":

    Do not "fix" localhost/127.0.0.1 control-plane URLs by forcing HTTPS when
    the transport is intentionally loopback-only.  Keep the safe loopback
    semantics, add/keep regression tests, and record the rationale in the PR if
    Sonar raises a hotspot.

Rationale for not forcing HTTPS:

1. The loopback interface is not accessible from any external network — only
   from processes running on the same host.
2. TLS on loopback requires certificate management (generating, distributing,
   and trusting a self-signed cert) which introduces more complexity and failure
   modes than the security benefit it would provide on localhost.
3. All servers created here bind exclusively to ``127.0.0.1`` (never ``0.0.0.0``
   or a routable address), so no external network hop exists for an adversary to
   intercept.

Sonar hotspot review record (PR #2036)
---------------------------------------
SonarCloud raised security hotspots against this module under the
``encrypt-data`` rule key (rule description: "Make sure that this server-side
HTTP endpoint uses HTTPS"). They are **safe by design** and must be reviewed
as "Safe" in the Sonar UI — they must NOT be "fixed" by forcing HTTPS (see
rationale above and C-001 in the repo charter). The regression test
``tests/core/test_loopback_http.py`` mutation-verifies that the bind address
is strictly ``127.0.0.1`` and that widening to ``0.0.0.0`` is caught; this
lock exists to prevent a future well-meaning edit from regressing the
loopback constraint.

Recorded in PR #2036 per C-005 (cite hotspots by rule key, not fragile
description). ``build_loopback_base_url``/``build_loopback_url`` (the two
URL-literal builders originally reviewed here) were pruned as dead collateral
of the sync-transport deletion (issue #5) — they lost their last src/ caller
with ``cli/commands/sync.py`` and gained none since (issue #116).
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

__all__ = [
    "create_loopback_server",
    "serve_loopback_server",
]

LOOPBACK_HOST = "127.0.0.1"


def create_loopback_server(
    port: int,
    handler_class: type[BaseHTTPRequestHandler],
    *,
    server_factory: type[HTTPServer] = HTTPServer,
) -> HTTPServer:
    """Create a loopback-bound HTTP server with an explicit binding contract.

    The server binds strictly to ``127.0.0.1`` (``LOOPBACK_HOST``).  This is
    a hard requirement — binding to ``0.0.0.0`` or any routable address is a
    security regression.  The regression test in
    ``tests/core/test_loopback_http.py`` mutation-verifies this invariant.
    """
    # Bind strictly to 127.0.0.1 — loopback-only by design; HTTPS not used
    # for this local control-plane transport (repo policy C-001).
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
