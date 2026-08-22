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
* Every identity field this module reads from a frame's payload —
  ``session_ref``/``user`` (ident-shaped: a short opaque token, matching
  ``managed.ManagedRegistry.session_ref()``'s own 12-hex shape upstream) and
  ``repo``/``branch``/``focus_ref`` (ref-shaped: can carry ``/``, e.g.
  ``transport.py``'s own ``f"{mission_slug}/{wp_id}"`` focus refs) — is
  routed through the shared Z1/zeitgeist identity grammar (``grammar.py``,
  itself a literal transcription of ``zeitgeist/editor.py:146-192``) before
  it reaches a ``PresenceView``/``FocusView`` or is used as this state's
  internal dict key. A relay is untrusted input exactly like the ``editor``
  rumor feed upstream sanitizes at render time: a well-formed identifier
  passes through unchanged, a prose-shaped one (the same "IGNORE PRIOR
  INSTRUCTIONS ..." class ``grammar.py`` documents) is replaced with
  grammar's stable, non-reversible ``unknown-<digest>`` label rather than
  ever reaching a caller unfiltered — WIRE-M2-04, HIC-M2-DISPOSITIONS item 2.
  ``branch`` is the one field routed differently: ``grammar.ident()``'s
  ``REF_RE`` shape check also caps segment count at
  ``grammar.MAX_SEGMENTS["ref"]`` (6) — sized for short, few-segment refs
  like ``mission-x/WP03`` — and this program's own sandbox branches
  (``bead/<ID>/<actor>/<n>``, e.g. ``bead/WIRE-M2-04/python-pedro/1``, 7
  segments) legitimately exceed it. Upstream documents the identical tension
  for ``branch`` at ``zeitgeist/editor.py:166-169`` — "a branch name
  legitimately reads like prose ... so no shape rule can separate them" —
  and answers it by keeping ``branch`` out of the segment-capped check
  rather than mis-rejecting real branch names. ``_branch_shaped`` below
  applies the same char-class-plus-length half of ``grammar.ident`` (still
  rejecting whitespace, control characters, and anything over the 64-char
  "ref" hard max — the "IGNORE PRIOR INSTRUCTIONS ..." class a real branch
  name never needs) without the segment-count half. ``repo``/``focus_ref``
  keep the full, unmodified ``grammar.ident(..., grammar.REF_RE)`` routing:
  neither has a real-world shape in this program that the segment cap
  rejects. ``path``/``kind``/``state`` are NOT identity fields in this sense
  (a file path legitimately looks like prose; ``state`` is already
  closed-enum gated against ``_FOCUS_STATES``) and are left as plain,
  un-sanitized strings, matching upstream's own separate ``_safe_path``
  treatment for paths (not ported here — same documented scope reduction as
  this module's own not-yet-landed ``validator.py``).
"""

from __future__ import annotations

from kernel.clock import now_epoch

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeGuard

from . import grammar

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


def _grammar_ident(value: object, pattern: re.Pattern[str] = grammar.IDENT_RE) -> str | None:
    """``_optional_str`` composed with the shared Z1/zeitgeist identity
    grammar (``grammar.ident``): a non-str value is dropped exactly as
    ``_optional_str`` already drops it; a well-typed but prose-shaped value
    is replaced with grammar's stable ``unknown-<digest>`` label rather than
    reaching a View unfiltered — the same rendering-time sanitization
    ``zeitgeist/editor.py`` applies before a caller-supplied identity is
    ever displayed (see the module docstring and ``grammar.py`` itself)."""
    return grammar.ident(value, pattern=pattern) if isinstance(value, str) else None


# Mirrors the "ref"-kind hard_max grammar.ident() applies internally
# (grammar.py's `hard_max = 64 if kind == "ref" else 32`) — duplicated, not
# imported, because ident() bakes that length check into the same
# expression as the segment-count check _branch_shaped deliberately skips;
# there is no accessor for "length half only". Cross-checked against
# grammar.ident's own behavior by test_live_frame.py, the same convention
# this module already uses for MAX_TTL_S vs. transport.FOCUS_TTL_S (see the
# module docstring).
_BRANCH_HARD_MAX = 64


def _branch_shaped(value: object) -> str | None:
    """Grammar-shaped validation for ``branch`` — REF_RE's character class
    and 64-char hard max, WITHOUT ``grammar.ident``'s segment-count cap
    (module docstring explains why: this program's own multi-segment
    ``bead/<ID>/<actor>/<n>`` branches legitimately exceed it, matching
    upstream's own carve-out for ``branch`` at
    ``zeitgeist/editor.py:166-169``).

    The character class alone is still a real filter — a relay is
    untrusted input like any other boundary here: no whitespace, no
    control characters, nothing over the length cap, so a prose-injection
    sentence (which needs a space to read as English) is rejected exactly
    as it would be under full ``grammar.ident`` routing. Only the
    segment-count heuristic — the one that cannot tell a real multi-segment
    branch from segment-joined prose (see ``grammar.py``'s own commentary
    on that ambiguity) — is skipped.

    The ``unknown-<digest>`` fallback is the identical label format/formula
    ``grammar.ident`` uses (same non-cryptographic, stable-per-input
    correlation label, not a security boundary — grammar.py:58-60), so a
    caller sees one consistent "rejected identity" shape regardless of
    which field or which half of the check failed it.
    """
    if not isinstance(value, str) or not value:
        return None
    if grammar.REF_RE.fullmatch(value) and len(value) <= _BRANCH_HARD_MAX:
        return value
    return "unknown-" + hashlib.sha1(value.encode()).hexdigest()[:8]  # noqa: S324


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
                # Grammar-sanitized before matching: presence/focus keys are
                # stored under the sanitized form too (see _apply_presence /
                # _apply_focus), so a hostile-but-consistent session_ref still
                # revokes the record it named rather than silently no-op-ing.
                ref = grammar.ident(ref)
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
        ref = grammar.ident(ref)  # ident-shaped: 12-hex session token, never a ref path
        observed_at = payload.get("observed_at")
        base_ts = float(observed_at) if _is_number(observed_at) else live_frame_obj.emitted_at
        self._presence[ref] = {
            "session_ref": ref,
            "user": _grammar_ident(actor.get("user")),
            "repo": _grammar_ident(payload.get("repo"), grammar.REF_RE),
            "branch": _branch_shaped(payload.get("branch")),
            "path": _optional_str(payload.get("path")),
            "kind": _optional_str(payload.get("kind")),
            "expires_at": base_ts + _clamp_ttl(payload.get("ttl_s")),
        }

    def _apply_focus(self, live_frame_obj: LiveFrame) -> None:
        payload = live_frame_obj.payload
        focus_ref = payload.get("focus_ref")
        if not isinstance(focus_ref, str) or not focus_ref:
            return
        focus_ref = grammar.ident(focus_ref, grammar.REF_RE)  # ref-shaped: mission_slug/wp_id
        state = payload.get("state")
        if state not in _FOCUS_STATES:
            return
        if state == "ended":
            self._focus.pop(focus_ref, None)  # closed signal: dropped, never queued
            return
        actor = payload.get("actor")
        session_ref = actor.get("session_ref") if isinstance(actor, dict) else None
        session_ref = grammar.ident(session_ref) if isinstance(session_ref, str) and session_ref else None
        self._focus[focus_ref] = {
            "focus_ref": focus_ref,
            "session_ref": session_ref,
            "state": state,
            "user": _grammar_ident(actor.get("user")) if isinstance(actor, dict) else None,
            "repo": _grammar_ident(payload.get("repo"), grammar.REF_RE),
            "branch": _branch_shaped(payload.get("branch")),
            "expires_at": live_frame_obj.emitted_at + _clamp_ttl(payload.get("ttl_s")),
        }

    def snapshot(self, *, now: float | None = None) -> TeamSnapshot:
        ts = now if now is not None else now_epoch()  # kernel.clock single door (M2 canonical integration)
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
