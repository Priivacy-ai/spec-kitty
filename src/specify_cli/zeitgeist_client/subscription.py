"""Z7-C: the composable, team-scoped subscription surface CLI/MCP adapters
share (program-graph handle Z7-C, "Spec Kitty subscription CLI/MCP
adapters").

This is the ONE place bounded-read/bounded-watch logic over Z4-C's
``filtered_stream.FilteredStream`` lives. ``cli/commands/zeitgeist.py`` and
``mcp_stdio.py`` both call the two functions here (:func:`status`,
:func:`watch`) rather than each re-deriving "how long to listen, how to
resolve a credential, how to serialize a snapshot" independently — "share
Z1 service" (this node's own criterion) means exactly this: one shared
adapter-facing surface over the existing typed client, not two competing
half-implementations bolted onto the same ``FilteredStream``.

Explicit team context, not a runtime URL/credential (node criterion:
"no ... runtime URL/credential ... or second auth implementation"):
callers name a ``repo`` — the key ``credentials.py`` already stores an
issued ``{relay_url, token}`` pair under (Z1.md §3.2 item 7; ``token_kind``
``"shared_team"`` is exactly a team-bound bearer capability, the same shape
``filtered_stream.TeamStreamConfig.capability_credential`` wants) — never a
free-form relay URL or bearer value typed at the call site. FIX-M2-15:
:func:`resolve_stream` threads ``credentials.py``'s own optional
``StoredCredential.capability_credential`` field through unchanged —
``relay_token=stored.token`` (``Authorization``), ``capability_credential=
stored.capability_credential or stored.token`` (``X-Zeitgeist-Capability``)
— so a two-credential checkout (SaaS-issued ``relay_token`` +
``capability_credential``) sends each header its own value, while a
single-credential one (every entry stored before this fix)
still sends ``stored.token`` to both, exactly as before. ``repo``,
``relay_url``, ``token``, and ``runtime_url`` are all members of
``sanitizer.FORBIDDEN_CONTROL_KEYS``/observation-adjacent names precisely
because a caller-supplied one is a claim, not a credential; this module
never accepts the latter two as parameters at all, so there is structurally
nothing here for one to leak through as an argument. This is also why there
is no second credential store: :func:`resolve_stream` reads the SAME
``credentials.py`` primitive Z1.md §3.2 item 7 already landed — a second
store would itself be the "second auth implementation" the node criterion
forbids.

No administration, no human approval: this module never calls
``credentials.store()``/``credentials.revoke()`` — provisioning a checkout
is the (separate, not-yet-built, network-canary-offer) ``checkout`` command
(``docs/plans/zeitgeist-client-wp01-remaining.md`` item 5); a caller with no
stored credential for ``repo`` gets :class:`NotCheckedOut`, never an
auto-provisioned one.

No implicit aggregation: :func:`resolve_stream` builds exactly one
``FilteredStream`` per call, for the one ``repo`` named — the same "no
multi-team aggregate" discipline ``filtered_stream`` itself enforces
structurally (see that module's own docstring).

Honest <=90s reported-live, bounded, no payload persistence:
:data:`MAX_TIMEOUT_S` clamps every timeout to Z1's own 90s ceiling
(``filtered_stream``/``live_frame``'s own ``MAX_TTL_S``) — never a
longer-than-honest wait dressed up as "still live". :func:`watch` additionally
bounds the frame COUNT (:data:`MAX_WATCH_FRAMES`) so one adapter call cannot
buffer an unbounded stream in memory. Neither function writes a frame or a
snapshot to disk anywhere — the only state is the in-process
``StreamState`` ``FilteredStream`` already keeps (Z4's own "no payload
persisted" criterion), released when the call returns.

No workflow/scoring from presence: the serializers below are a structural,
lossless field-for-field projection of ``TeamSnapshot``/``LiveFrame`` into
JSON-safe dicts — no derived priority, ranking, or workflow decision is
computed from what a team is presently doing.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator, Mapping
from typing import Any, cast

from . import credentials, filtered_stream
from .live_frame import LiveFrame, MAX_TTL_S, TeamSnapshot

# The same honest reported-live ceiling live_frame/filtered_stream enforce
# client-side regardless of what a relay claims (live_frame.MAX_TTL_S).
# Re-declared, not imported, matching that module's own "read-side module
# stays independent" reasoning for why it re-declares transport's constant
# rather than importing it.
MAX_TIMEOUT_S: int = MAX_TTL_S

DEFAULT_STATUS_TIMEOUT_S: float = 2.0
DEFAULT_WATCH_TIMEOUT_S: float = 5.0

# Bounded collection: one watch() call never buffers an unbounded stream.
MAX_WATCH_FRAMES: int = 500


class NotCheckedOut(Exception):
    """No stored credential for ``repo``. Read-only surface: this module
    never auto-provisions one — see the module docstring."""

    def __init__(self, repo: str) -> None:
        super().__init__(f"no stored Zeitgeist credential for repo {repo!r}; run the checkout flow first")
        self.repo = repo


def _close(gen: Iterator[LiveFrame]) -> None:
    """``FilteredStream.watch()``'s own declared return type is the narrower
    ``Iterator[LiveFrame]`` (its public contract never promises a
    generator specifically), but its concrete implementation is always a
    generator — ``test_filtered_stream.py`` itself relies on
    ``gen.close()`` throughout. This cast documents that gap once instead
    of two identical ``# type: ignore`` comments at each call site."""
    cast(Generator[LiveFrame, None, None], gen).close()


def _clamp_timeout(timeout_s: float) -> float:
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")
    return min(float(timeout_s), float(MAX_TIMEOUT_S))


def _require_positive_max_frames(max_frames: int) -> int:
    """Defense in depth: the CLI already enforces ``min=1`` via Typer, but
    the MCP tool schema does not (Renata review, Z7-C attempt-6 handback).
    A caller-supplied ``max_frames <= 0`` must not be able to make
    :func:`watch` yield exactly one frame while looking like a "0 frames"
    request — fail closed instead."""
    if max_frames < 1:
        raise ValueError("max_frames must be >= 1")
    return max_frames


def resolve_stream(repo: str) -> filtered_stream.FilteredStream:
    """Build exactly one ``FilteredStream`` for ``repo``'s already-stored
    credential. Raises :class:`NotCheckedOut` rather than constructing a
    stream against nothing. ``repo`` is the credential-store key — since
    spec-kitty#132 the ``host/owner/repo`` shape
    :func:`resolution.store_key` writes (the CLI derives it from the
    checkout, #137), never a bare repo name: those keys hold nothing
    readable any more."""
    stored = credentials.load(repo=repo)
    if stored is None:
        raise NotCheckedOut(repo)
    config = filtered_stream.TeamStreamConfig(
        relay_url=stored.relay_url,
        relay_token=stored.token,
        capability_credential=stored.capability_credential or stored.token,
    )
    return filtered_stream.FilteredStream(config)


def _serialize_snapshot(snapshot: TeamSnapshot) -> dict[str, Any]:
    return {
        "epoch": snapshot.epoch,
        "presence": [
            {
                "session_ref": p.session_ref,
                "user": p.user,
                "repo": p.repo,
                "branch": p.branch,
                "path": p.path,
                "kind": p.kind,
                "expires_at": p.expires_at,
            }
            for p in snapshot.presence
        ],
        "focus": [
            {
                "session_ref": f.session_ref,
                "focus_ref": f.focus_ref,
                "state": f.state,
                "user": f.user,
                "repo": f.repo,
                "branch": f.branch,
                "expires_at": f.expires_at,
            }
            for f in snapshot.focus
        ],
        "reset_count": snapshot.reset_count,
        "last_reset_reason": snapshot.last_reset_reason,
    }


def _serialize_frame(frame: LiveFrame) -> dict[str, Any]:
    payload: Mapping[str, Any] = frame.payload
    return {
        "schema_version": frame.schema_version,
        "epoch": frame.epoch,
        "seq": frame.seq,
        "emitted_at": frame.emitted_at,
        "frame_type": frame.frame_type,
        "payload": dict(payload),
    }


def status(repo: str, *, timeout_s: float = DEFAULT_STATUS_TIMEOUT_S) -> dict[str, Any]:
    """One explicit team context, one bounded read: open exactly one
    subscription, apply whatever arrives inside ``timeout_s`` (clamped to
    :data:`MAX_TIMEOUT_S`), then report the local snapshot and let the
    subscription go. Never writes anything to disk; never retries.

    Raises :class:`NotCheckedOut` if ``repo`` has no stored credential, and
    propagates ``urllib.error.URLError``/``HTTPError`` unchanged on a
    connection/relay fault — this is a thin adapter over
    ``FilteredStream.watch()``, not a second fault-handling layer over it.
    """
    timeout_s = _clamp_timeout(timeout_s)
    stream = resolve_stream(repo)
    gen = stream.watch(idle_timeout_s=timeout_s)
    try:
        for _ in gen:
            pass  # apply every frame that arrives inside the bounded window
    finally:
        _close(gen)
    result = _serialize_snapshot(stream.check())
    result["repo"] = repo
    return result


def watch(repo: str, *, timeout_s: float = DEFAULT_WATCH_TIMEOUT_S, max_frames: int = MAX_WATCH_FRAMES) -> Iterator[dict[str, Any]]:
    """Yield each accepted frame, serialized, until ``timeout_s`` (clamped
    to :data:`MAX_TIMEOUT_S`) of idleness, ``max_frames`` frames, or the
    relay closes the connection — whichever comes first. Bounded on both
    axes: never an unbounded stream from one call.
    """
    timeout_s = _clamp_timeout(timeout_s)
    max_frames = _require_positive_max_frames(max_frames)
    stream = resolve_stream(repo)
    gen = stream.watch(idle_timeout_s=timeout_s)
    count = 0
    try:
        for frame in gen:
            yield _serialize_frame(frame)
            count += 1
            if count >= max_frames:
                return
    finally:
        _close(gen)
