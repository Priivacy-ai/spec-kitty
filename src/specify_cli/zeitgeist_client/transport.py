"""The one typed client service (Z1.md §3.2 item 8).

``ZeitgeistClient.offer()`` implements "one-offer-after-append,
750ms/drop-no-retry, forbidden-field zero-attempt" exactly: (1) build the
request_id; (2) ``sanitizer.assert_clean(args)`` — any forbidden key raises
before any network attempt, yielding ``REFUSED_LOCAL``, ``elapsed_s=0.0``;
(3) exactly one HTTP POST under a 750ms TOTAL wall-clock deadline
(``budget.run_with_deadline``); (4) whatever happens — 2xx, non-2xx, timeout,
connection refused — ``offer()`` returns; it never retries and never queues.

Known scope reduction vs. the full Z1.md §3.2 item 8 contract (recorded
honestly, not silently): step 3 of the draft ("validator.validate
('managed_control', envelope)") is NOT implemented in this pass —
``validator.py`` and the bundled F1/F3 schema copies do not exist yet (F1-T1/
F3-T1 have not landed as producer candidates in their own repos to pin
digests against, per Z1.md §3.5's "cannot freeze before both exist"). offer()
currently performs only the sanitizer gate before its one network attempt.
``watch()``/``status()`` are not implemented (``NotImplementedError``) — see
the WP01 handoff for the full remaining list.

``focus_start``/``_heartbeat``/`_pause``/`_end`` build ``focus_ref``
themselves (Z1.md §3.2 item 8, F1's normative derivation clause):
``focus_ref = mission_slug if wp_id is None else f"{mission_slug}/{wp_id}"``.
``focus_end``'s ``reason`` is deliberately restricted to ``user``/``timeout``
at both the type boundary and a runtime guard — ``revoked`` is a
server-originated ``LiveFrame.signal`` outcome the client can only observe,
never claim (Z1.md decision 6, N12).
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from . import budget, sanitizer

# ≤90s current-focus bound (O1-C's operability drills exercise this
# denominator; Z1 owns the constant, Z1.md §1 "downstream criteria").
FOCUS_TTL_S = 90

_FocusPauseReason = Literal["user", "dnd"]
_FocusEndReason = Literal["user", "timeout"]
_PresenceActivity = Literal["file_edit", "command"]

_VALID_PAUSE_REASONS = frozenset({"user", "dnd"})
_VALID_END_REASONS = frozenset({"user", "timeout"})
_VALID_PRESENCE_ACTIVITIES = frozenset({"file_edit", "command"})


@dataclass(frozen=True)
class ClientConfig:
    relay_url: str  # local/Docker-hosted only; never written by anything but checkout()
    token: str
    harness: str
    session_id: str
    agent_id: str | None
    repo: str
    branch: str


class OfferOutcome(StrEnum):
    SENT = "sent"  # relay accepted (2xx)
    REJECTED = "rejected"  # relay returned 4xx/5xx
    DROPPED_BUDGET = "dropped_budget"  # 750ms elapsed before a response
    DROPPED_UNREACHABLE = "dropped_unreachable"  # connect/DNS failure
    REFUSED_LOCAL = "refused_local"  # sanitizer rejected before any socket call


@dataclass(frozen=True)
class OfferResult:
    outcome: OfferOutcome
    request_id: str  # ControlEnvelope.request_id (idempotency key)
    elapsed_s: float  # 0.0 for REFUSED_LOCAL — no network attempt was made


def _classify_network_error(exc: BaseException) -> OfferOutcome:
    reason: BaseException = exc
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason if isinstance(exc.reason, BaseException) else exc
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return OfferOutcome.DROPPED_BUDGET
    return OfferOutcome.DROPPED_UNREACHABLE


class ZeitgeistClient:
    """The single typed client. Owns no team/identity/permission logic — see
    module docstring and Z1.md decision 7: caller fields are claims only."""

    def __init__(self, config: ClientConfig):
        self._config = config
        self._focus_ref: str | None = None
        self._lock = threading.Lock()

    # -- the primitive ------------------------------------------------

    def offer(self, op: str, args: Mapping[str, Any]) -> OfferResult:
        request_id = str(uuid.uuid4())

        try:
            sanitizer.assert_clean(args)
        except sanitizer.ForbiddenFieldError:
            return OfferResult(
                outcome=OfferOutcome.REFUSED_LOCAL, request_id=request_id, elapsed_s=0.0
            )

        envelope = {"op": op, "request_id": request_id, "args": dict(args)}
        body = json.dumps(envelope).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.token}",
        }
        url = self._config.relay_url.rstrip("/") + "/events"

        def _post() -> tuple[int, bytes]:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with budget.open_bounded(req, timeout=budget.OFFER_BUDGET_S) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as exc:
                return exc.code, exc.read()

        deadline_outcome = budget.run_with_deadline(_post, deadline_s=budget.OFFER_BUDGET_S)

        if not deadline_outcome.completed:
            return OfferResult(
                outcome=OfferOutcome.DROPPED_BUDGET,
                request_id=request_id,
                elapsed_s=deadline_outcome.elapsed_s,
            )
        if deadline_outcome.error is not None:
            return OfferResult(
                outcome=_classify_network_error(deadline_outcome.error),
                request_id=request_id,
                elapsed_s=deadline_outcome.elapsed_s,
            )

        status, _body = deadline_outcome.result  # type: ignore[misc]
        result_outcome = (
            OfferOutcome.SENT if 200 <= status < 300 else OfferOutcome.REJECTED
        )
        return OfferResult(
            outcome=result_outcome, request_id=request_id, elapsed_s=deadline_outcome.elapsed_s
        )

    # -- current-focus lifecycle (opt-in) ------------------------------

    def _claim_args(self, **extra: Any) -> dict[str, Any]:
        args: dict[str, Any] = {
            "session_id": self._config.session_id,
            "repo": self._config.repo,
            "branch": self._config.branch,
        }
        args.update(extra)
        return args

    def focus_start(self, mission_slug: str, wp_id: str | None = None) -> OfferResult:
        with self._lock:
            if self._focus_ref is not None:
                return OfferResult(
                    outcome=OfferOutcome.REFUSED_LOCAL,
                    request_id=str(uuid.uuid4()),
                    elapsed_s=0.0,
                )
            focus_ref = mission_slug if wp_id is None else f"{mission_slug}/{wp_id}"
            self._focus_ref = focus_ref
        return self.offer(
            "focus.start", self._claim_args(focus_ref=focus_ref, ttl_s=FOCUS_TTL_S)
        )

    def focus_heartbeat(self) -> OfferResult:
        focus_ref = self._focus_ref
        if focus_ref is None:
            return OfferResult(
                outcome=OfferOutcome.REFUSED_LOCAL, request_id=str(uuid.uuid4()), elapsed_s=0.0
            )
        return self.offer("focus.heartbeat", self._claim_args(focus_ref=focus_ref))

    def focus_pause(self, reason: _FocusPauseReason = "user") -> OfferResult:
        if reason not in _VALID_PAUSE_REASONS:
            raise ValueError(
                f"focus_pause reason must be one of {sorted(_VALID_PAUSE_REASONS)!r}, got {reason!r}"
            )
        focus_ref = self._focus_ref
        if focus_ref is None:
            return OfferResult(
                outcome=OfferOutcome.REFUSED_LOCAL, request_id=str(uuid.uuid4()), elapsed_s=0.0
            )
        return self.offer(
            "focus.pause", self._claim_args(focus_ref=focus_ref, pause_reason=reason)
        )

    def focus_end(self, reason: _FocusEndReason = "user") -> OfferResult:
        # Runtime guard, not just a type hint: "revoked" is a server-originated
        # LiveFrame.signal outcome (F1's rev-2 fix) — the client must be
        # structurally incapable of claiming it, including via an MCP/JSON
        # caller that bypasses static typing (Z1.md decision 6, N12).
        if reason not in _VALID_END_REASONS:
            raise ValueError(
                f"focus_end reason must be one of {sorted(_VALID_END_REASONS)!r}, got {reason!r} "
                "— 'revoked' is a server-originated outcome the client can only observe "
                "via watch(), never claim"
            )
        with self._lock:
            focus_ref = self._focus_ref
            self._focus_ref = None
        if focus_ref is None:
            return OfferResult(
                outcome=OfferOutcome.REFUSED_LOCAL, request_id=str(uuid.uuid4()), elapsed_s=0.0
            )
        return self.offer(
            "focus.end", self._claim_args(focus_ref=focus_ref, ended_reason=reason)
        )

    # -- presence (independent of focus/DND state, Z1.md decision 9) ---

    def presence(self, activity: _PresenceActivity, path: str | None = None) -> OfferResult:
        if activity not in _VALID_PRESENCE_ACTIVITIES:
            raise ValueError(
                f"presence activity must be one of {sorted(_VALID_PRESENCE_ACTIVITIES)!r}, "
                f"got {activity!r}"
            )
        args = self._claim_args(activity=activity)
        if path is not None:
            args["path"] = path
        return self.offer("presence.publish", args)

    # -- not yet implemented in this pass -------------------------------

    def status(self) -> None:
        raise NotImplementedError(
            "ZeitgeistClient.status() is not implemented in this pass — see the "
            "WP01 handoff 'remaining' list"
        )

    def watch(self, *, idle_timeout_s: float | None = None) -> None:
        raise NotImplementedError(
            "ZeitgeistClient.watch() is not implemented in this pass — see the "
            "WP01 handoff 'remaining' list"
        )
