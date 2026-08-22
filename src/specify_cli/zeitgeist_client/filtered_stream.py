"""Z4-C: the network half of the filtered live-stream client — one SSE
connection per team-bound subscription against F3's
``GET /managed/stream`` (``zeitgeist/managed.py``, Z3's managed-runtime
routes; requires the ``managed.live`` capability enabled on the relay).

``live_frame`` (pure logic: parsing + ``StreamState``) does the actual
gap/epoch/revoke/<=90s-clear work; this module is the thin loop that reads
SSE ``data:`` lines off the wire, hands each one to
``live_frame.parse_live_frame``, and applies the result.

Team-bound selector, structurally: a subscription names exactly one team by
holding exactly one ``capability_credential`` — the opaque
``X-Zeitgeist-Capability`` token F3's ``managed_auth.py`` verifies and scopes
every reply to (``identity.team``/``deployment``/``repo``, derived from the
token's own signed claims, never from anything this client sends).
``TeamStreamConfig`` deliberately carries no ``team``/``deployment``/``repo``
field of its own — those names are members of
``sanitizer.FORBIDDEN_CONTROL_KEYS``, and a client-supplied filter would be
theatre anyway: the relay does not look at one. "No implicit multi-team
aggregate" follows the same way — this module offers no function that reads
from more than one ``FilteredStream``'s state; covering several teams means
holding several instances side by side in caller code, never widening this
one's shape (see ``test_two_subscriptions_never_share_state``).

Known, honestly-recorded scope reduction: no CLI or MCP surface. Z4-C's own
node criterion is the client *library* surfaces ("watch/check/current-focus
surfaces over Z1 service"); wiring a ``spec-kitty zeitgeist watch`` command
or an MCP tool onto them remains item 4 of
``docs/plans/zeitgeist-client-wp01-remaining.md``, untouched by this pass —
exactly the same "landed the primitive, not yet the adapter" split Z1-T1
itself recorded for ``offer()``/``credentials.py``.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass

from . import budget
from .live_frame import FocusView, LiveFrame, StreamState, TeamSnapshot, parse_live_frame

_STREAM_PATH = "/managed/stream"


@dataclass(frozen=True)
class TeamStreamConfig:
    """One subscription's connection facts. See the module docstring for
    why there is no team/deployment/repo field here — the credential alone
    is the selector."""

    relay_url: str
    capability_credential: str


class FilteredStream:
    """A single team-bound live-stream subscription.

    ``watch()`` opens exactly one SSE connection, applies every accepted
    frame to local state, and yields it. ``check()``/``current_focus()``
    read that local state back with **no network call of their own** — Z4-C's
    "no missed-event reconstruction" criterion means there is structurally
    no request this class can make to ask the relay what a caller missed; a
    ``signal.kind in {"gap","epoch"}`` frame (or an ``epoch`` value change
    between frames) instead clears local state outright, so a caller who
    only ever calls ``check()`` sees an honestly empty view rather than a
    silently stale one.

    One instance is one team; state is never shared across instances (no
    module-level registry of any kind).
    """

    def __init__(self, config: TeamStreamConfig) -> None:
        self._config = config
        self._state = StreamState()
        self._lock = threading.Lock()

    def watch(self, *, idle_timeout_s: float | None = None) -> Iterator[LiveFrame]:
        """Yield each accepted ``LiveFrame`` as it arrives.

        Returns (does not raise) when the relay closes the connection, or
        when ``idle_timeout_s`` elapses with nothing received — both are
        ordinary end-of-watch, not errors; ``idle_timeout_s=None`` (the
        default) waits indefinitely, matching a long-running foreground
        watch loop.

        Connection failure (refused, DNS, a non-2xx response — e.g. an
        expired credential, or 503 when the relay's stream slots are
        saturated) raises ``urllib.error.URLError``/``HTTPError`` on the
        first ``next()``. This is a long-lived subscription, not a
        drop-no-retry offer — Z1's 750ms ``OFFER_BUDGET_S`` model does not
        apply here; whether/when to reconnect is the caller's decision, not
        this generator's.
        """
        url = self._config.relay_url.rstrip("/") + _STREAM_PATH
        headers = {"X-Zeitgeist-Capability": self._config.capability_credential}
        req = urllib.request.Request(url, headers=headers, method="GET")
        opener = budget.NoRedirects.build()
        with opener.open(req, timeout=idle_timeout_s) as resp:
            while True:
                try:
                    raw_line = resp.readline()
                except TimeoutError:
                    return  # idle timeout: an ordinary end of watch, not an error
                if not raw_line:
                    return  # relay closed the connection
                live_frame_obj = self._accept_line(raw_line)
                if live_frame_obj is None:
                    continue
                with self._lock:
                    self._state.apply(live_frame_obj)
                yield live_frame_obj

    @staticmethod
    def _accept_line(raw_line: bytes) -> LiveFrame | None:
        """Decode one SSE wire line into a :class:`LiveFrame`, or ``None``
        for anything that is not a well-formed ``data:`` line carrying a
        shape-valid frame — never raises, so one hostile/malformed line
        cannot end the watch loop for every frame after it."""
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line.startswith("data:"):
            return None
        text = line[len("data:") :].strip()
        if not text:
            return None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parse_live_frame(raw)

    def check(self, *, now: float | None = None) -> TeamSnapshot:
        """The current, honestly-known, TTL-clamped view — whatever
        ``watch()`` has accumulated so far. No network call."""
        with self._lock:
            return self._state.snapshot(now=now)

    def current_focus(self, *, now: float | None = None) -> tuple[FocusView, ...]:
        """Convenience accessor for the opt-in current-focus view alone."""
        return self.check(now=now).focus
