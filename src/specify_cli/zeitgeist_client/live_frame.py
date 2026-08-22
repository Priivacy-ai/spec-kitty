"""Z4-C: parsing and local, honest-reported-live application of F3's managed
``LiveFrame`` wire shape (``m1-contract-drafts/`` ``managed_live.schema.json``
— ``$id: urn:zeitgeist:schema:managed_live:1``).

This module is pure logic: no sockets, no relay knowledge. The network half
(one SSE connection per team-bound subscription) lives in ``filtered_stream``,
which calls ``parse_live_frame`` on every ``data:`` line and feeds the result
into one ``StreamState`` per subscription.

Known, honestly-recorded scope reduction (same category Z1-T1's own
``transport.py`` docstring already recorded for the control-envelope path):
``parse_live_frame`` checks exactly the wire-shape fields this module reads
in order to apply a frame safely — required top-level keys, the
``schema_version`` major (rejecting any wire version this module was not
written against), the ``frame.type`` discriminator, and the handful of typed
fields ``StreamState`` consumes. It is NOT a general JSON-Schema validator
run against the bundled ``managed_live.schema.json`` document with a pinned
digest (that is ``validator.py``, still not landed per
``docs/plans/zeitgeist-client-wp01-remaining.md`` item 1 — F1-T1/F3-T1 landed
as *producer candidates in their own repos*, not yet imported/pinned here).
A frame this module cannot make sense of is dropped, never crashes the watch
loop and never raises — the same "fail closed, stay silent" posture
``sanitizer.assert_clean`` uses on the outbound side.

Reported-live honesty, not reconstruction:

* ``epoch`` changing between two frames (the relay restarted — F3's own
  N16 contract: a fresh process mints a fresh epoch and resets ``seq``) and
  an explicit ``signal.kind in {"gap", "epoch"}`` frame both mean the same
  thing to this module: local state is no longer known to be accurate, so it
  is cleared outright. Z4-C's node criterion is "no missed-event
  reconstruction" — there is no attempt to patch, diff, or partially trust
  what came before; the client is simply, honestly ignorant of the window it
  could not see, until fresh frames rebuild a view.
* ``signal.kind == "revoked"`` is scoped: only the named ``session_ref``'s
  presence/focus entries are removed, matching the relay's own
  ``session_revoke`` scoping (F3 N30).
* A ``focus`` frame with ``state == "ended"`` is dropped immediately, never
  retained — "no durable queue for closed signals" is this module's own
  reading of that criterion: a closed signal is consumed and gone, not kept
  around for a later reader.
* ``ttl_s`` is always clamped to ``MAX_TTL_S`` (90, F1/F3's own ceiling —
  see ``transport.FOCUS_TTL_S``, the same constant, owned there because Z1
  is the write side; re-declared here rather than imported so this read-side
  module stays independent of ``transport``'s network stack, checked against
  it by ``test_live_frame.py``). This clamp is defense in depth: "<=90s
  clear" must hold even if a hostile or buggy relay sends a larger value —
  including a non-finite one: JSON's ``Infinity``/``-Infinity``/``NaN``
  tokens survive ``json.loads`` (the parser ``filtered_stream._accept_line``
  uses) unrejected by default, so ``_clamp_ttl`` treats any non-finite
  ``ttl_s`` the same as an absent one rather than let ``int()`` raise on it.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeGuard

FrameType = Literal["presence", "focus", "signal"]

_FRAME_TYPES: frozenset[str] = frozenset({"presence", "focus", "signal"})
_SIGNAL_KINDS: frozenset[str] = frozenset({"gap", "epoch", "revoked", "heartbeat"})
_FOCUS_STATES: frozenset[str] = frozenset({"active", "paused", "ended"})

# managed_live.schema.json FocusSample.ttl_s / managed_presence.schema.json
# PresenceSample.ttl_s: both declare "maximum": 90. Cross-checked against
# transport.FOCUS_TTL_S by test_live_frame.py rather than imported (see
# module docstring).
MAX_TTL_S = 90


@dataclass(frozen=True)
class LiveFrame:
    """One parsed, shape-valid ``LiveFrame`` envelope. ``payload`` is the
    ``frame[frame_type]`` sub-object, exactly as received — ``StreamState``
    reads individual fields defensively, so this stays a plain mapping
    rather than a second, type-specific dataclass layer."""

    schema_version: str
    epoch: str
    seq: int
    emitted_at: float
    frame_type: FrameType
    payload: Mapping[str, Any]


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_live_frame(raw: object) -> LiveFrame | None:
    """Return a :class:`LiveFrame` for a shape-valid envelope, else ``None``.

    Never raises: this is the read-side "forbidden/malformed input" gate —
    anything this module was not written to understand is refused, exactly
    as ``sanitizer.assert_clean`` refuses an outbound document, except the
    read side cannot signal the sender, so it drops and moves on.
    """
    if not isinstance(raw, dict):
        return None

    schema_version = raw.get("schema_version")
    epoch = raw.get("epoch")
    seq = raw.get("seq")
    emitted_at = raw.get("emitted_at")
    frame = raw.get("frame")

    if not isinstance(schema_version, str) or not schema_version.startswith("1."):
        return None  # version-skew rejection: only the 1.x major is understood
    if not isinstance(epoch, str) or not epoch:
        return None
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        return None
    if not _is_number(emitted_at):
        return None
    if not isinstance(frame, dict):
        return None

    frame_type = frame.get("type")
    if frame_type not in _FRAME_TYPES:
        return None
    payload = frame.get(frame_type)
    if not isinstance(payload, dict):
        return None

    return LiveFrame(
        schema_version=schema_version,
        epoch=epoch,
        seq=seq,
        emitted_at=float(emitted_at),
        frame_type=frame_type,
        payload=payload,
    )


def _clamp_ttl(value: object) -> int:
    if not _is_number(value):
        return MAX_TTL_S
    # A hostile or buggy relay can send JSON's `Infinity`/`NaN`/`-Infinity`
    # tokens — Python's own ``json.loads`` (used by
    # ``filtered_stream._accept_line``) accepts them by default, and
    # ``int()`` on a non-finite float raises (OverflowError for +/-inf,
    # ValueError for nan). Treat any non-finite value the same as "absent":
    # clamp to the ceiling rather than let it propagate out of
    # ``StreamState.apply``/``FilteredStream.watch()`` and end the whole
    # subscription generator over one bad field in one frame.
    if isinstance(value, float) and not math.isfinite(value):
        return MAX_TTL_S
    return max(1, min(int(value), MAX_TTL_S))


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


@dataclass(frozen=True)
class PresenceView:
    session_ref: str
    user: str | None
    repo: str | None
    branch: str | None
    path: str | None
    kind: str | None
    expires_at: float


@dataclass(frozen=True)
class FocusView:
    session_ref: str | None
    focus_ref: str
    state: str
    user: str | None
    repo: str | None
    branch: str | None
    expires_at: float


@dataclass(frozen=True)
class TeamSnapshot:
    """The honest, TTL-clamped, closed-signals-already-dropped view of one
    team-bound subscription's local state at read time. ``reset_count`` /
    ``last_reset_reason`` are the only trace a gap/epoch reset leaves —
    observability without ever retaining what was cleared."""

    epoch: str | None
    presence: tuple[PresenceView, ...]
    focus: tuple[FocusView, ...]
    reset_count: int
    last_reset_reason: str | None


class StreamState:
    """Volatile, in-process, per-subscription state. Nothing here is ever
    written to disk (Z4's own "no payload persisted" criterion) — construct
    a fresh instance per ``FilteredStream`` and let it go when the
    subscription does."""

    def __init__(self) -> None:
        self._epoch: str | None = None
        self._presence: dict[str, dict[str, Any]] = {}
        self._focus: dict[str, dict[str, Any]] = {}
        self._reset_count = 0
        self._last_reset_reason: str | None = None

    def _reset(self, reason: str) -> None:
        self._presence.clear()
        self._focus.clear()
        self._reset_count += 1
        self._last_reset_reason = reason

    def apply(self, live_frame_obj: LiveFrame) -> None:
        if self._epoch is not None and live_frame_obj.epoch != self._epoch:
            self._reset("epoch_change")
        self._epoch = live_frame_obj.epoch

        if live_frame_obj.frame_type == "signal":
            self._apply_signal(live_frame_obj)
        elif live_frame_obj.frame_type == "presence":
            self._apply_presence(live_frame_obj)
        else:
            self._apply_focus(live_frame_obj)

    def _apply_signal(self, live_frame_obj: LiveFrame) -> None:
        kind = live_frame_obj.payload.get("kind")
        if kind not in _SIGNAL_KINDS:
            return  # unknown/future signal kind: ignored, not fatal
        if kind in ("gap", "epoch"):
            self._reset(kind)
            return
        if kind == "revoked":
            ref = live_frame_obj.payload.get("session_ref")
            if isinstance(ref, str) and ref:
                self._presence.pop(ref, None)
                self._focus = {k: v for k, v in self._focus.items() if v.get("session_ref") != ref}
        # "heartbeat": liveness only, no state change.

    def _apply_presence(self, live_frame_obj: LiveFrame) -> None:
        payload = live_frame_obj.payload
        actor = payload.get("actor")
        if not isinstance(actor, dict):
            return
        ref = actor.get("session_ref")
        if not isinstance(ref, str) or not ref:
            return
        observed_at = payload.get("observed_at")
        base_ts = float(observed_at) if _is_number(observed_at) else live_frame_obj.emitted_at
        self._presence[ref] = {
            "session_ref": ref,
            "user": _optional_str(actor.get("user")),
            "repo": _optional_str(payload.get("repo")),
            "branch": _optional_str(payload.get("branch")),
            "path": _optional_str(payload.get("path")),
            "kind": _optional_str(payload.get("kind")),
            "expires_at": base_ts + _clamp_ttl(payload.get("ttl_s")),
        }

    def _apply_focus(self, live_frame_obj: LiveFrame) -> None:
        payload = live_frame_obj.payload
        focus_ref = payload.get("focus_ref")
        if not isinstance(focus_ref, str) or not focus_ref:
            return
        state = payload.get("state")
        if state not in _FOCUS_STATES:
            return
        if state == "ended":
            self._focus.pop(focus_ref, None)  # closed signal: dropped, never queued
            return
        actor = payload.get("actor")
        session_ref = actor.get("session_ref") if isinstance(actor, dict) else None
        self._focus[focus_ref] = {
            "focus_ref": focus_ref,
            "session_ref": session_ref if isinstance(session_ref, str) else None,
            "state": state,
            "user": _optional_str(actor.get("user")) if isinstance(actor, dict) else None,
            "repo": _optional_str(payload.get("repo")),
            "branch": _optional_str(payload.get("branch")),
            "expires_at": live_frame_obj.emitted_at + _clamp_ttl(payload.get("ttl_s")),
        }

    def snapshot(self, *, now: float | None = None) -> TeamSnapshot:
        ts = now if now is not None else time.time()
        # Lazy eviction, purged in place (not merely filtered from the
        # output): an expired entry is not "closed" by any signal the relay
        # sent, so nothing else would ever remove it — <=90s clear must hold
        # on ordinary silence, not only on an explicit end/revoke.
        for ref in [k for k, v in self._presence.items() if v["expires_at"] <= ts]:
            del self._presence[ref]
        for ref in [k for k, v in self._focus.items() if v["expires_at"] <= ts]:
            del self._focus[ref]

        presence = tuple(
            PresenceView(
                session_ref=v["session_ref"], user=v["user"], repo=v["repo"],
                branch=v["branch"], path=v["path"], kind=v["kind"], expires_at=v["expires_at"],
            )
            for v in self._presence.values()
        )
        focus = tuple(
            FocusView(
                session_ref=v["session_ref"], focus_ref=v["focus_ref"], state=v["state"],
                user=v["user"], repo=v["repo"], branch=v["branch"], expires_at=v["expires_at"],
            )
            for v in self._focus.values()
        )
        return TeamSnapshot(
            epoch=self._epoch, presence=presence, focus=focus,
            reset_count=self._reset_count, last_reset_reason=self._last_reset_reason,
        )
