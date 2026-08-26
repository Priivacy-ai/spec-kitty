"""Z7-C: the official-SDK stdio MCP adapter over ``subscription.py``'s
shared team-scoped surface (program-graph handle Z7-C).

"Official-SDK" per the node criterion means the ``mcp`` PyPI package
(``modelcontextprotocol/python-sdk``, ``pyproject.toml``'s
``mcp>=1.27.1,<2.0.0``) — never a hand-rolled JSON-RPC loop reimplementing
MCP's own framing. ``build_server()`` wires exactly two tools,
``zeitgeist_status``/``zeitgeist_watch``, onto :mod:`subscription`'s
``status()``/``watch()`` — the SAME functions the CLI adapter
(``cli/commands/zeitgeist.py``) calls, so an MCP client and a terminal user
observe identical bounded-read/bounded-watch behavior; neither adapter
re-derives it independently ("share Z1 service").

Tool schemas take only ``repo`` — optional, see below (plus the bounded
``timeout_s``/``max_frames`` knobs ``subscription.py`` itself exposes) —
never a ``relay_url``/``token`` field. An MCP client cannot ask this server
to connect anywhere but an already-stored credential; there is structurally
no parameter here for a "runtime URL/credential" to travel through (mirrors
``subscription.py``'s own reasoning, and ``filtered_stream.TeamStreamConfig``'s
before it).

Like the CLI commands, ``repo`` is optional (#149): omitted, both tools
derive the key from this process's working directory via
:func:`resolution.store_key_for_checkout` — the same default
``cli/commands/zeitgeist.py`` resolves for a terminal user — so a client
session launched inside a checkout reads that checkout's own stored
credential without being told the key. Given, it must parse as
``host/owner/repo`` (:func:`resolution.parse_store_key`): a bare pre-#132
NAME gets a tool error naming the accepted form rather than a confusing
not-checked-out.

``subscription.NotCheckedOut`` (and every other unusable-key fault,
:class:`resolution.StoreKeyError` included) is deliberately left to
propagate out of both tool functions uncaught: FastMCP turns an uncaught
exception into a proper MCP tool-error result
(``CallToolResult.isError=True``) carrying the exception's message, which
already names the repo — swallowing it into a successful-looking
``{"error": ...}`` payload would misreport a fault as ordinary data. A
connection/relay fault (``urllib.error.URLError``/``HTTPError``) propagates
the same way, for the same reason.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import subscription

SERVER_NAME = "spec-kitty-zeitgeist"

_INSTRUCTIONS = (
    "Read-only, bounded access to one Team Kitty repo's live Zeitgeist "
    "presence/focus stream. Both tools take `repo` — the credential-store "
    "key, host/owner/repo (e.g. github.com/acme/widget), under which "
    "`spec-kitty zeitgeist checkout` stored the team context; omit `repo` "
    "to derive that key from the checkout this server process runs in, "
    "exactly as the CLI commands do. Neither tool accepts a relay URL or "
    "credential, and neither writes anything to disk. `timeout_s` is always "
    "clamped to a 90s honest reported-live ceiling."
)


def _resolve_store_key(repo: str | None) -> str:
    """The credential-store key the tools read: the caller-supplied
    ``host/owner/repo``, or the one derived from this process's working
    directory when omitted (#149). Mirrors the CLI adapter's own resolution
    exactly (:func:`cli.commands.zeitgeist._resolve_store_key`) minus its
    exit-code reporting — here every unusable input raises
    :class:`resolution.StoreKeyError`, which propagates uncaught the way
    :class:`subscription.NotCheckedOut` always has (FastMCP turns it into a
    tool-error result carrying the message).

    The resolver import stays function-scoped like the CLI's: resolution
    drags in the SaaS auth-context machinery, which building/listing tools
    for a client that never calls one must not pay for."""
    from specify_cli.zeitgeist_client.resolution import StoreKeyError, parse_store_key, store_key_for_checkout

    if repo is not None:
        return parse_store_key(repo)
    derived = store_key_for_checkout(Path.cwd())
    if derived is None:
        raise StoreKeyError(
            f"could not derive a Zeitgeist credential-store key from {Path.cwd()} — "
            "not a git checkout with a hosted origin remote. Pass host/owner/repo "
            "(e.g. github.com/acme/widget) explicitly."
        )
    return derived


def build_server() -> FastMCP:
    """A fresh :class:`FastMCP` instance exposing exactly the
    ``zeitgeist_status``/``zeitgeist_watch`` tool pair. Called once per
    stdio session by :func:`run_stdio` — no module-level singleton, so tests
    can build independent servers without sharing state."""
    server: FastMCP = FastMCP(SERVER_NAME, instructions=_INSTRUCTIONS)

    @server.tool(
        name="zeitgeist_status",
        description=("One bounded snapshot of repo's live presence/focus state (<=90s wait). Omit repo to read the checkout this server process runs in."),
        structured_output=True,
    )
    def zeitgeist_status(repo: str | None = None, timeout_s: float = subscription.DEFAULT_STATUS_TIMEOUT_S) -> dict[str, Any]:
        return subscription.status(_resolve_store_key(repo), timeout_s=timeout_s)

    @server.tool(
        name="zeitgeist_watch",
        description=("Bounded live presence/focus frames from repo (<=90s wait, capped frame count). Omit repo to read the checkout this server process runs in."),
        structured_output=True,
    )
    def zeitgeist_watch(
        repo: str | None = None,
        timeout_s: float = subscription.DEFAULT_WATCH_TIMEOUT_S,
        max_frames: int = subscription.MAX_WATCH_FRAMES,
    ) -> dict[str, Any]:
        key = _resolve_store_key(repo)
        frames = list(subscription.watch(key, timeout_s=timeout_s, max_frames=max_frames))
        return {"repo": key, "frames": frames}

    return server


async def run_stdio() -> None:
    """Serve the two-tool surface over stdio until the client disconnects.
    The sole entry point ``cli/commands/zeitgeist.py``'s hidden ``mcp-serve``
    command runs."""
    await build_server().run_stdio_async()
