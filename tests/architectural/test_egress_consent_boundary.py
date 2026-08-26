"""Architectural gate: no project data leaves the machine from an unlisted file.

Issue Priivacy-ai/spec-kitty#3030 (P0 confidentiality). On 2026-07-27, 1,322
events belonging to five never-opted-in projects were delivered alongside 7,811
from the intended one. This mission then found and closed egress paths **one at
a time, five separate times**, each by a different review; a dedicated sink-first
enumeration (``kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md``,
E1-E19) found three more. The operator's decision was to stop enumerating and
build a boundary.

Why a *sink* scan and not a name scan
-------------------------------------
The prior guard, ``tests/sync/test_no_queue_drain_constructed_3030.py``, keys on
two literal function names (``RETIRED_DRAIN_NAMES``). It was probed and **missed**
a new queue-backed sender of the shape ``queue.drain_queue(...)`` followed by
``urllib.request.urlopen(...)`` — the names differ, so the guard is blind. This
gate keys on the **sink**, which such a path cannot avoid having, and is
allowlisted **by file**, so a *new* sender in a file nobody has reasoned about is
a red build rather than a discovery six reviews later.

The inventory's structural finding is the reason a file-keyed allowlist works
here: two independent universes feed the *same* HTTP sink
(``delivery/dispatcher.py`` gated in SQL, ``sync/history_import/upload.py``
ungated), so ``DeliveryReceiver.deliver`` is itself treated as a sink. That makes
the two callers distinguishable even though the ``requests.post`` they share is
one line in one file.

Shape (modelled on ``tests/architectural/test_auth_transport_singleton.py``)
---------------------------------------------------------------------------
1. AST-scan every ``.py`` under ``src/`` for the sink vocabulary below.
2. Permit a sink only in a file carrying an explicit :data:`_EGRESS_ALLOWLIST`
   entry, each annotated with the **consent seam** that covers it (or a
   member of a closed vocabulary of non-consent reasons).
3. Permit, separately and loudly, the files on :data:`_KNOWN_UNGATED` — the
   currently-open work-list. See "The work-list, and why it is red" below.
4. Meta-tests: no stale allowlist entry; the annotated seam must still exist;
   and a negative control proving the scanner and the whole collection path
   actually bite.

The sink vocabulary
-------------------
* ``requests.post`` / ``.patch`` / ``.request`` and the same verbs on any HTTP
  client object (``httpx``, ``AuthenticatedClient``, ...). Matched on the
  *method name*, not the receiver's type, because the receiver is usually a
  parameter whose type is invisible to AST. ``.put`` is matched only when the
  call also carries a URL or a request-body keyword — see limit 6 below.
* ``urllib.request.urlopen(...)`` / a bare ``urlopen(...)``. **Every** call
  counts, loopback or not: whether a URL is loopback is a runtime property of a
  variable, so deciding it statically would hand a new sender the exact evasion
  (build the URL in a local) that this gate exists to remove. Loopback control
  endpoints are therefore allowlisted explicitly, with ``LOOPBACK_CONTROL``.
* ``.send_event(...)`` and ``<ws-ish>.send(...)`` — the WebSocket senders.
* ``.deliver(...)`` — ``DeliveryReceiver.deliver``, the shared transmit facade
  one call above ``requests.post`` (the "no chokepoint" finding above).
* **Any call carrying both ``headers=`` and a body** (``data``/``json``/
  ``content``/``files``), whatever the callee is named. This is the
  callee-agnostic rule, and it is the one that sees a transport **injected as a
  parameter** — ``poster(url, data=..., headers=...)`` is a bare ``Name`` call
  that no method-name rule can match. Request/response *value* constructors
  (``urllib.request.Request``) are excluded: they build a value, they do not
  transmit, and the ``urlopen`` that follows is already matched.

The work-list, and why it is empty
----------------------------------
:data:`_KNOWN_UNGATED` is how an egress path with **no** consent answer is
recorded while it is being fixed. It is deliberately not a ``skip`` and not a
strict-xfail: ``test_known_ungated_egress_paths_are_closed`` asserts the set is
**empty**, so a recorded path is a **red build** naming the file, its
requirement and the seam it must call. This mission's single worst documented
failure shape is a mechanism that reports success for having done nothing, and a
suppression that prints like a pass is exactly that shape.

It is empty today. It was authored holding E1
(``sync/history_import/upload.py``, FR-028), E2 (``tracker/saas_client.py``,
FR-029) and E3 (``saas_client/client.py``, FR-030) — the three ungated
sink-bearing files the enumeration found — and all three were closed by their
own work packages while this gate was being written. Each is now allowlisted
against the seam that closed it, and each seam is re-checked on every run by
``test_seam_allowances_name_a_live_seam``: if a fix is reverted, the allowance
stops being true and this module reds rather than staying quietly exempt.

Both sets are size-ratcheted in ``tests/architectural/_baselines.yaml``, where
growth **fails** ``test_ratchet_baselines.py`` — a different test in a different
file — and shrinkage only warns. ``known_ungated_files`` is pinned at **0**, so
recording a new open path costs a visible YAML diff with a written
justification; the intended response to a new finding is to close the path, not
to register it.

What this gate does not judge
-----------------------------
An allowance asserts that a named seam **exists**, not that it is *correct*. The
gate can tell you a consent call was deleted; it cannot tell you the call
resolves the right project or fails closed. That is a reviewer's job, and on this
mission it is where the real defects lived — FR-025's ``is False``, FR-031's
undetermined-reads-as-consent, FR-027's field-level shape faults. This gate
closes the *structural* hole (a sender nobody reasoned about) and nothing more.

Completeness limits — inherited from the enumeration, stated rather than implied
--------------------------------------------------------------------------------
A claim that names its gaps is the only defensible kind. This gate sees a sink
that is written as a call to one of the names above, in a file under ``src/``.
It does **not** see:

1. **``getattr``-by-string reaching a sender.** ``src/`` contains 433
   string-literal ``getattr`` calls; a string literal is not a reference, so an
   attribute reached by name is invisible to AST scanning. The same blind spot
   already made two egress paths look live that are dead (FR-032,
   ``token_manager._ws_client``), and it cuts both ways.
2. **Empty callback registries — and one exists.** E17,
   ``status/adapters.py::fire_resolved_binding_fanout``, has a firing site and
   **zero registered handlers**. *A sink that does not exist yet cannot be found
   by scanning for sinks.* This is the hard limit of sink-first enumeration and
   the strongest argument for this gate over any one-off audit: the gate is what
   reds on the day the handler is written.
3. **Dynamic import, entry-point plugins, ``exec``.** Not audited; a sender
   reached that way is still a sink *in some file*, so it reds only if that file
   is unlisted — which is the point, but reachability is not what is checked.
4. **``subprocess`` invoked through a variable command name.** E19
   (``git push origin <branch>``, ``merge/executor.py`` /
   ``orchestrator_api/commands.py``) is out of boundary by design — the project's
   own commits to the project's own ``origin``, opt-in, not the spec-kitty SaaS —
   and is deliberately not modelled here. A transmitting subprocess built from a
   variable command name would also be missed.
5. **At-rest pooling.** Writes into ``~/.spec-kitty/`` are not egress and are not
   scanned; the inventory scopes that to C-006.
6. **A bare ``.put(x)``.** ``put`` collides with ``queue.put`` / ``mailbox.put``,
   which are not egress — found by this module's own no-false-positive control,
   not reasoned about in advance. It is therefore matched only when the call
   carries an HTTP signal (a ``json``/``data``/``content``/``headers``/
   ``params``/``files``/``auth``/``cookies`` keyword, or a first argument that is
   a URL literal, an f-string, or a variable named ``url``/``uri``/
   ``endpoint``/...). ``client.put(some_var)`` with no keywords is consequently
   **missed**. ``timeout`` is excluded from the keyword set on purpose —
   ``queue.put(item, timeout=1)`` has one. ``post``/``patch``/``request`` carry
   no such collision in ``src/`` and are matched unconditionally.
7. **A file may hold more than one sink, and an allowance covers them all.** E20
   is the recorded case: the egress inventory traced the import path *backwards*
   from ``requests.post`` and named one sink, but ``run_server_preflight`` POSTs
   the same envelope stream earlier in the same function, so a gate placed where
   the inventory pointed would have leaked every envelope while looking closed.
   Tracing a sink backwards to its callers is not the same as tracing a path
   forwards through every request it makes. This gate keys on files, so it
   cannot tell you a *second* sink in an already-allowlisted file is ungated —
   the seam annotation is per file, not per call. Adding a sink to a listed file
   is therefore the cheapest way to evade this gate, and only review catches it.
8. **The all-positional / no-``headers=`` transport call.** ``poster(url, body,
   hdrs)`` — every argument positional, no ``headers=`` or body keyword present
   at all — evades both the method-name rules (the callee is a bare ``Name``,
   not ``.post``/``.patch``/``.request``) and ``_transmits_a_body`` (`:295-306`),
   which requires ``headers`` **and** a body keyword to be present before it
   will call a bare-``Name`` callee a sink. `#3113`: the guard's own bite-test
   (`test_scanner_detects_each_sink_shape`) exercised only the kwargs form of
   the injected-transport shape, so it would have certified a scanner that was
   blind to this one — a negative control that only tests the shape you
   thought of is not a negative control (see ``TestGuardBites`` below for the
   generalisation this produced). A structural tightening was measured before
   being ruled out: the callee is a bare ``ast.Name`` whose ``id`` resolves to
   a parameter of the *enclosing* ``FunctionDef`` — transport injected as a
   parameter, decidable with no author-chosen word (C-006 forbids any
   tightening that needs one, including ``_URL_ARG_NAMES``). Measured across
   the whole of ``src/`` **before** any matcher edit
   (``TestFR015StructuralTighteningMeasurement`` below is the reproducible,
   re-runnable form of that measurement), it produces a **non-zero**
   false-positive count: reproducible false hits include calls to
   ``resolve_workspace_for_wp``, ``locate_work_package``,
   ``behind_commits_touch_only_planning_artifacts`` and ``get_wp_lane`` —
   each a dependency-injected work-package/lane lookup function called through
   a same-named ``Callable``-typed parameter, not a transport. Per FR-015's
   acceptance criteria a non-zero count is itself the outcome: **the matcher is
   left alone.** What catches this shape is review, and the file-keyed
   allowlist if the sink lands in a file nobody has reasoned about.
   ``test_scanner_detects_each_sink_shape`` carries both of `#3113`'s
   positional cases pinned as ``pytest.xfail(..., strict=True)``, naming this
   limit.

Spec: FR-002, FR-003, FR-019, FR-025-FR-032, C-003. `#3113` (FR-013, FR-014,
FR-015) adds limit 8 above; cross-referenced one-directionally against
``kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md``,
which belongs to a closed mission and is not edited by this change (C-010).
"""

from __future__ import annotations

import ast
import re
import warnings
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# Sink vocabulary
# ---------------------------------------------------------------------------


class SinkKind(StrEnum):
    """The transmit primitives this gate recognises."""

    HTTP_VERB = "http-verb"
    URLOPEN = "urlopen"
    SEND_EVENT = "send-event"
    WEBSOCKET_SEND = "websocket-send"
    RECEIVER_DELIVER = "receiver-deliver"
    TRANSPORT_CALL = "transport-call"


#: HTTP methods that transmit a body or an arbitrary request. Measured against
#: ``src/``: ``post``/``patch``/``request`` produce zero non-transport matches,
#: so they are matched unconditionally.
_HTTP_VERBS: frozenset[str] = frozenset({"post", "patch", "request"})

#: ``put`` is the one verb that collides with a common non-network API
#: (``queue.put``, ``mailbox.put``), so it is matched only when the call also
#: carries an HTTP signal. See ``_looks_like_http_call`` and limit 6 in the
#: module docstring for the residual hole this leaves.
_AMBIGUOUS_HTTP_VERBS: frozenset[str] = frozenset({"put"})

#: Keyword arguments that mean "this call carries a request body/headers".
#: ``timeout`` is deliberately absent — ``queue.put(item, timeout=1)`` has one.
_HTTP_KWARGS: frozenset[str] = frozenset({"json", "data", "content", "headers", "params", "files", "auth", "cookies"})

#: Argument names that mean the first positional is a URL.
_URL_ARG_NAMES: frozenset[str] = frozenset({"url", "uri", "endpoint", "href", "base_url", "full_url", "request_url", "target_url"})

#: Body-carrying keywords. A call taking one of these **and** ``headers`` is an
#: HTTP request whatever its callee is named — which is how an *injected*
#: transport is caught. ``sync/history_import/upload.py::run_server_preflight``
#: POSTs the full envelope stream through a ``poster(...)`` parameter, a bare
#: ``Name`` call that no method-name rule can see; it was found only because
#: FR-028's implementer traced the path *forwards*. See limit 7.
_REQUEST_BODY_KWARGS: frozenset[str] = frozenset({"json", "data", "content", "files"})

#: Callees that build a request/response *value* rather than transmitting one.
#: ``urllib.request.Request(url, data=..., headers=...)`` is HTTP-shaped but sends
#: nothing — the ``urlopen`` that follows is the sink, and it is already matched.
_VALUE_CONSTRUCTORS: frozenset[str] = frozenset({"Request", "Response"})

#: Receiver names that make a bare ``.send(...)`` a websocket frame rather than
#: a queue put. Kept narrow on purpose: ``.send`` is too common a name to match
#: unconditionally, and every live websocket sender in ``src/`` binds one of
#: these (``self.ws.send`` in ``sync/client.py``).
_WEBSOCKET_RECEIVERS: frozenset[str] = frozenset({"ws", "_ws", "websocket", "_websocket", "ws_client", "_ws_client", "conn", "socket"})

#: What an unlisted file must do, per sink kind. This is the actionable half of
#: the failure message: "route it through X" beats "you are not allowed".
_SEAM_GUIDANCE: dict[SinkKind, str] = {
    SinkKind.RECEIVER_DELIVER: (
        "resolve consent from the batch's own project_uuid before calling "
        "DeliveryReceiver.deliver — delivery/selection.py::select_consented "
        "already computes exactly that value (E9)"
    ),
    SinkKind.SEND_EVENT: (
        "gate on the event's own project_uuid via "
        "sync/consent.py::event_project_consents_to_publish (E7/E8) or "
        "invocation/adapters.py::resolve_egress_consent (E6) — both fail closed"
    ),
    SinkKind.WEBSOCKET_SEND: (
        "gate on the frame's own project_uuid via the emitter's "
        "_project_consents_to_capture / local_commit's _frame_project_consents "
        "(E11/E12) before the frame crosses the socket"
    ),
    SinkKind.HTTP_VERB: (
        "resolve the payload's own project_uuid and consult specify_cli.sync.consent "
        "before the request — never a checkout/cwd/repo-slug proxy (FR-019), and "
        "never read 'could not determine' as consent (FR-003)"
    ),
    SinkKind.URLOPEN: (
        "if this is a loopback control endpoint, allowlist it as LOOPBACK_CONTROL; "
        "otherwise gate on the payload's own project_uuid via specify_cli.sync.consent "
        "before the call (E8 does this before crossing the loopback socket)"
    ),
    SinkKind.TRANSPORT_CALL: (
        "this transmits a body through an injected/aliased transport, so the "
        "method name hides nothing — gate on the payload's own project_uuid via "
        "specify_cli.sync.consent BEFORE the call. E20 is the precedent: the "
        "import path had two sinks and gating only the visible one would have "
        "leaked every envelope while looking closed"
    ),
}


@dataclass(frozen=True)
class SinkSite:
    """One transmit call, located by file + line + kind (never by line alone)."""

    relpath: str
    lineno: int
    kind: SinkKind
    snippet: str


def _attr_tail(node: ast.expr) -> str | None:
    """Last name segment of ``a``/``a.b``/``self.a.b``; ``None`` for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _looks_like_http_call(node: ast.Call) -> bool:
    """True when *node* carries a URL or a request-body keyword.

    Used to disambiguate ``client.put(url, json=...)`` from ``queue.put(item)``
    without keying on the receiver's *name* — name-keying is the failure mode
    this whole gate exists to replace.
    """
    if any(kw.arg in _HTTP_KWARGS for kw in node.keywords if kw.arg is not None):
        return True
    if not node.args:
        return False
    first = node.args[0]
    if isinstance(first, ast.JoinedStr):  # f"{base}/api/..."
        return True
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return "://" in first.value or first.value.startswith("/")
    tail = _attr_tail(first)
    return tail is not None and tail.lower().lstrip("_") in _URL_ARG_NAMES


def _transmits_a_body(node: ast.Call) -> bool:
    """True when *node* carries both headers and a request body.

    Callee-agnostic on purpose. This is the rule that sees a transport passed in
    as a parameter (``poster(url, data=..., headers=...)``) or reached through an
    alias, neither of which any method-name rule can match.
    """
    tail = _attr_tail(node.func)
    if tail in _VALUE_CONSTRUCTORS:
        return False
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    return "headers" in kwargs and bool(kwargs & _REQUEST_BODY_KWARGS)


def _classify(node: ast.Call) -> SinkKind | None:
    """Return the :class:`SinkKind` of *node*, or ``None`` when it is not a sink."""
    func = node.func
    if isinstance(func, ast.Name):
        # A bare ``urlopen(...)`` after ``from urllib.request import urlopen``.
        if func.id == "urlopen":
            return SinkKind.URLOPEN
        return SinkKind.TRANSPORT_CALL if _transmits_a_body(node) else None
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr in _HTTP_VERBS:
        return SinkKind.HTTP_VERB
    if func.attr in _AMBIGUOUS_HTTP_VERBS and _looks_like_http_call(node):
        return SinkKind.HTTP_VERB
    if func.attr == "urlopen":
        return SinkKind.URLOPEN
    if func.attr == "send_event":
        return SinkKind.SEND_EVENT
    if func.attr == "deliver":
        return SinkKind.RECEIVER_DELIVER
    if func.attr == "send" and _attr_tail(func.value) in _WEBSOCKET_RECEIVERS:
        return SinkKind.WEBSOCKET_SEND
    return SinkKind.TRANSPORT_CALL if _transmits_a_body(node) else None


def _find_sinks(path: Path, root: Path) -> list[SinkSite]:
    """Every sink call in *path*, with ``relpath`` taken relative to *root*."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - defensive
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - a louder problem than this rule
        return []

    relpath = path.relative_to(root).as_posix()
    sites: list[SinkSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _classify(node)
        if kind is None:
            continue
        try:
            snippet = ast.unparse(node.func)
        except Exception:  # pragma: no cover - older interpreters
            snippet = "<unparse-unavailable>"
        sites.append(SinkSite(relpath=relpath, lineno=node.lineno, kind=kind, snippet=snippet))
    return sites


def _scan(root: Path) -> list[SinkSite]:
    """Every sink call under *root*, excluding ``__pycache__``."""
    sites: list[SinkSite] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sites.extend(_find_sinks(path, root))
    return sites


# ---------------------------------------------------------------------------
# The allowlist
# ---------------------------------------------------------------------------


class AllowanceKind(StrEnum):
    """Closed vocabulary of reasons a file may hold a sink.

    Closed on purpose: without it, "no seam needed" becomes the escape hatch
    that turns the allowlist back into a name list.
    """

    #: A named consent seam resolves the data's **own** project_uuid.
    SEAM = "seam"
    #: The payload carries no project data at all (auth, doctrine fetch, probes).
    NOT_PROJECT_DATA = "not-project-data"
    #: A localhost control/health endpoint; nothing crosses the machine boundary.
    LOOPBACK_CONTROL = "loopback-control"
    #: A per-project transport whose every caller is separately allowlisted.
    TRANSPORT_ONLY = "transport-only"
    #: No production caller; non-reachability pinned by a named companion guard.
    UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class Allowance:
    """Why one file is permitted to hold a sink."""

    kind: AllowanceKind
    inventory_id: str
    note: str
    #: For ``SEAM``: the symbol that must still exist, and the module holding it
    #: (relative to ``src/``). The seam frequently lives in the *caller*, not the
    #: sink file — E9's selection is in ``delivery/selection.py`` while the
    #: ``requests.post`` is in ``delivery/receivers.py``.
    seam_symbol: str | None = None
    seam_module: str | None = None
    #: For ``UNREACHABLE``: the test that pins the absence of a caller.
    pinned_by: str | None = None


#: Files permitted to hold a transmit primitive, keyed by path relative to
#: ``src/``. Inventory ids refer to
#: ``kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md``.
_EGRESS_ALLOWLIST: dict[str, Allowance] = {
    # -- Gated by a named consent seam on the data's own project_uuid ---------
    "specify_cli/delivery/receivers.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E9",
        note=(
            "The shared POST transport. Consent is selected one layer above "
            "(dispatcher), and _cross_project_refusal is the second fence, at "
            "exactly the position a GateKind would have occupied (FR-001's "
            "retirement rationale)."
        ),
        seam_symbol="_cross_project_refusal",
        seam_module="specify_cli/delivery/receivers.py",
    ),
    "specify_cli/delivery/dispatcher.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E9",
        note=(
            "Consent is pushed into SQL by delivery/selection.py::select_consented so "
            "refused rows cannot starve the window (NFR-002), and the answer is then "
            "*carried* into a ConsentedBatch rather than re-asked — re-asking would be "
            "the second consent chain C-003 forbids. Anchored on consented_batch, the "
            "construction the receiver will not accept a batch without, because that is "
            "the gate; select_consented is upstream of it and can be renamed."
        ),
        seam_symbol="consented_batch",
        seam_module="specify_cli/delivery/dispatcher.py",
    ),
    "specify_cli/sync/body_transport.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E10",
        note="Per task; the exclusion is pushed into the read that builds the window.",
        seam_symbol="_consenting_body_project_uuids",
        seam_module="specify_cli/sync/background.py",
    ),
    "specify_cli/sync/runtime.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E7",
        note="Resolves the event's own uuid, fails closed, gates before every side effect.",
        seam_symbol="event_project_consents_to_publish",
        seam_module="specify_cli/sync/runtime.py",
    ),
    "specify_cli/sync/events.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E8",
        note="Same seam as E7, applied before the envelope crosses the loopback socket.",
        seam_symbol="event_project_consents_to_publish",
        seam_module="specify_cli/sync/events.py",
    ),
    "specify_cli/invocation/propagator.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E6",
        note=("FR-025. A 4-member enum where NO_RESOLVER / UNANSWERABLE / non-bool all refuse, so 'could not determine' is no longer read as consent (FR-003)."),
        seam_symbol="resolve_egress_consent",
        seam_module="specify_cli/invocation/propagator.py",
    ),
    "specify_cli/sync/sharing_client.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E13",
        note="Every endpoint takes an explicit source_project_uuid; own uuid by signature.",
        seam_symbol="source_project_uuid",
        seam_module="specify_cli/sync/sharing_client.py",
    ),
    # -- Closed by this mission after the 2026-07-30 enumeration found them ----
    # These three were authored into _KNOWN_UNGATED and moved here when their
    # work packages landed. The seam is anchored in the sink file itself, so the
    # allowance depends on nothing but the file it exempts: revert the fix and
    # test_seam_allowances_name_a_live_seam reds.
    "specify_cli/sync/history_import/upload.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E1",
        note=(
            "FR-028. Closed in the strong form the inventory recommended rather than "
            "with an `if`: _consented_batches mints ConsentedBatch values and "
            "DeliveryReceiver.deliver accepts nothing else, so a future caller that "
            "skips the gate has nothing to hand the receiver. This is the path that "
            "inherited FR-001's retirement without inheriting its replacement."
        ),
        seam_symbol="_consented_batches",
        seam_module="specify_cli/sync/history_import/upload.py",
    ),
    "specify_cli/tracker/saas_client.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E2",
        note=(
            "FR-029. _request refuses via tracker_egress_verdict before the call. "
            "This is the path reached non-interactively during mission creation "
            "(core/mission_creation.py -> tracker/origin_consumer.py -> "
            "bind_mission_origin), which needed no operator action to fire. "
            "#3108 swapped the seam from project_egress_refusal to "
            "tracker_egress_verdict(root, destination=HOSTED_SERVICE), which joins "
            "the same hosted-sync consent chain (Channel 1) with the project's own "
            "committed tracker.egress key (Channel 2) as a narrowing conjunct. The "
            "exemption is strictly safer than before: Channel 1 still decides, and a "
            "tracker.egress grant is a no-op here because this transport reaches "
            "spec-kitty's own hosted service. Per FR-016 the Channel-1 refusal text "
            "stays byte-identical to what #3030 shipped."
        ),
        seam_symbol="tracker_egress_verdict",
        seam_module="specify_cli/tracker/saas_client.py",
    ),
    "specify_cli/saas_client/client.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="E3",
        note=(
            "FR-030. _refuse_unless_project_consents runs in both _get and _post "
            "*before the URL is built* — four of five endpoints put mission_id "
            "('ULID or slug', and a slug is a client engagement name) in the request "
            "path, so a body-only gate would have missed every one."
        ),
        seam_symbol="_refuse_unless_project_consents",
        seam_module="specify_cli/saas_client/client.py",
    ),
    # -- Transport whose callers each carry their own seam --------------------
    "specify_cli/sync/client.py": Allowance(
        kind=AllowanceKind.TRANSPORT_ONLY,
        inventory_id="E14",
        note=(
            "The websocket itself, constructed per project. The pong carries only a "
            "build_id; every caller that sends project data (emitter E11, "
            "local_commit E12, runtime E7) is separately allowlisted with a seam."
        ),
    ),
    # NOTE: E15 (specify_cli/sync/batch.py, kind=UNREACHABLE) was REMOVED by #3167.
    # The allowance existed because the queue-backed drain was ungated but had no
    # production caller. #3167 deleted the drain instead of gating it, so the module
    # now holds zero transmit primitives and no allowance is owed -- an inert row
    # here is exactly the quiet drift that mission was opened to close. Do not
    # re-add it: `sync/batch.py` must not regain a `requests.*` or
    # `request_with_stdlib_fallback_sync` call, which
    # `tests/architectural/test_batch_drain_retired_3167.py` now enforces.
    # -- Not project egress (E18), verified individually rather than assumed --
    "specify_cli/auth/transport.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="The centralized auth transport (FR-030 of the auth-boundary ADR); token traffic.",
    ),
    "specify_cli/auth/http/transport.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="Auth-internal transport with the stdlib fallback; token traffic.",
    ),
    "specify_cli/auth/flows/authorization_code.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="OAuth authorization-code exchange; carries no project data.",
    ),
    "specify_cli/auth/flows/device_code.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="OAuth device-code flow; carries no project data.",
    ),
    "specify_cli/auth/flows/refresh.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="OAuth token refresh; carries no project data.",
    ),
    "specify_cli/auth/flows/revoke.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="OAuth token revocation; carries no project data.",
    ),
    "specify_cli/auth/websocket/token_provisioning.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="Provisions a websocket token; carries no project data.",
    ),
    "specify_cli/saas/readiness.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="Server reachability probe; sends no payload.",
    ),
    "specify_cli/cli/commands/sync.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note=(
            "`sync doctor`'s connectivity probe: a GET to /sync/health/ and, on "
            "404/405, a POST of the literal empty body b'{\"events\": []}' to the "
            "legacy batch endpoint to distinguish a reachable old server from an "
            "unreachable one. No journal row, no envelope, no identity. Surfaced "
            "by the injected-transport rule (it calls request_with_fallback_sync, "
            "not requests.post) — a file nobody had reasoned about until then."
        ),
    ),
    "specify_cli/doctrine/sources/api_source.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note="Fetches doctrine content inbound; the request carries no project data.",
    ),
    "specify_cli/doctrine/sources/https_source.py": Allowance(
        kind=AllowanceKind.NOT_PROJECT_DATA,
        inventory_id="E18",
        note=(
            "Fetches doctrine content inbound. The JFrog AQL POST carries only "
            "the operator-configured repository, path, and item name; it sends "
            "no project identity, mission data, or local doctrine content."
        ),
    ),
    "specify_cli/dashboard/handlers/api.py": Allowance(
        kind=AllowanceKind.LOOPBACK_CONTROL,
        inventory_id="E18",
        note="127.0.0.1 daemon endpoint read by the local dashboard.",
    ),
    "specify_cli/dashboard/lifecycle.py": Allowance(
        kind=AllowanceKind.LOOPBACK_CONTROL,
        inventory_id="E18",
        note="Localhost dashboard shutdown/control endpoints.",
    ),
    "specify_cli/sync/daemon.py": Allowance(
        kind=AllowanceKind.LOOPBACK_CONTROL,
        inventory_id="E18",
        note="Localhost health probe and daemon control endpoint.",
    ),
    "specify_cli/sync/daemon_protocol.py": Allowance(
        kind=AllowanceKind.LOOPBACK_CONTROL,
        inventory_id="WP10-T047",
        note=(
            "Authenticated migration quiesce/restart handshake. The constructor "
            "parses and requires an exact http://127.0.0.1:<port> or "
            "http://localhost:<port> authority before urllib can be reached."
        ),
    ),
    "specify_cli/sync/orphan_sweep.py": Allowance(
        kind=AllowanceKind.LOOPBACK_CONTROL,
        inventory_id="E18",
        note="127.0.0.1 in the reserved daemon port range; orphan classification.",
    ),
    "specify_cli/spec_review/runner.py": Allowance(
        kind=AllowanceKind.SEAM,
        inventory_id="ox-alpha-spec-reviewer-FR-003",
        note=(
            "The transport is fixed to an explicit http://127.0.0.1:<port> OpenCode "
            "server. SpecReviewService calls confirm_and_load_spec with the exact "
            "previewed manifest digest before it builds the prompt or invokes this "
            "runner; a missing or mismatched consent digest stops before this sink."
        ),
        seam_symbol="confirm_and_load_spec",
        seam_module="specify_cli/spec_review/service.py",
    ),
}

#: Ratcheted in ``_baselines.yaml`` as
#: ``test_egress_consent_boundary.egress_allowlist_files``. Growth fails
#: ``test_ratchet_baselines.py``, so silencing this gate by adding a file
#: requires an edit in a second file with a justification comment.
_EGRESS_ALLOWLIST_FILES: frozenset[str] = frozenset(_EGRESS_ALLOWLIST)


# ---------------------------------------------------------------------------
# The work-list: how an egress path with no consent answer gets recorded
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UngatedPath:
    """A sink-bearing file with no consent gate, and the requirement closing it."""

    inventory_id: str
    requirement: str
    seam_required: str
    note: str


#: Egress paths with no consent answer at all, recorded while they are fixed.
#:
#: **This set is asserted EMPTY** by ``test_known_ungated_egress_paths_are_closed``,
#: so an entry here is a red build naming the file, the requirement that closes it
#: and the seam it must call — never a skip, never a strict-xfail, because a
#: suppression that prints like a pass is this mission's worst documented failure
#: shape. Its size is pinned at 0 in ``_baselines.yaml``
#: (``test_egress_consent_boundary.known_ungated_files``), so recording a new one
#: also reds ``test_ratchet_baselines.py`` until a written justification is added
#: there. The intended response to a new finding is to close the path.
#:
#: Authored holding E1/E2/E3 (FR-028/029/030); all three landed while this gate was
#: being written and are now allowlisted above against the seam that closed each.
#:
#: NOT recorded here, deliberately: FR-031, the fail-open enqueue gate in
#: ``sync/body_upload.py``. That file holds no transmit primitive — it enqueues, and
#: E10's per-task seam gates the actual send — so this gate has nothing to red on
#: there, and an entry it could never clear by its own evidence would be a standing
#: false accusation rather than a work-list. FR-031 is a gate defect with its own pins.
_KNOWN_UNGATED: dict[str, UngatedPath] = {}

#: See :data:`_EGRESS_ALLOWLIST_FILES` — same ratchet, different key.
_KNOWN_UNGATED_FILES: frozenset[str] = frozenset(_KNOWN_UNGATED)


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _collect_offenders(
    root: Path,
    allowed: frozenset[str],
    known_ungated: frozenset[str],
) -> list[SinkSite]:
    """Sink sites under *root* in a file that is neither allowlisted nor known-ungated.

    Parameterised over *root* and both permission sets so the negative control
    exercises **this** function — the one the boundary test calls — rather than
    only the leaf matcher. A guard whose collection path has never been observed
    to fail is decoration.
    """
    permitted = allowed | known_ungated
    return [site for site in _scan(root) if site.relpath not in permitted]


def _worklist_schema_violations(entries: dict[str, UngatedPath]) -> list[str]:
    """Ways a work-list entry stops being actionable, and so becomes an exemption."""
    problems: list[str] = []
    for relpath, entry in sorted(entries.items()):
        if not entry.requirement.startswith("FR-"):
            problems.append(f"{relpath}: requirement {entry.requirement!r} does not name an FR — nobody can tell when it clears")
        if not entry.seam_required.strip():
            problems.append(f"{relpath}: names no seam it has to call, so nobody can clear it")
        if not entry.note.strip():
            problems.append(f"{relpath}: carries no description of the path")
    return problems


def _worklist_failure_text(entries: dict[str, UngatedPath]) -> str:
    """The red-build report for an open egress path."""
    listed = "\n".join(
        f"  {relpath}  [{entry.inventory_id}] closed by {entry.requirement}\n      seam required: {entry.seam_required}\n      {entry.note}"
        for relpath, entry in sorted(entries.items())
    )
    return (
        f"#3030: {len(entries)} egress path(s) still ship project data with no "
        f"per-project consent answer:\n{listed}\n\n"
        "This failure is the work-list. Close each path at its sink, then move the "
        "file to _EGRESS_ALLOWLIST with the seam that now covers it and shrink "
        "test_egress_consent_boundary.known_ungated_files in "
        "tests/architectural/_baselines.yaml."
    )


def _format(sites: list[SinkSite]) -> str:
    return "\n".join(f"  {site.relpath}:{site.lineno}  [{site.kind.value}] {site.snippet}(...)\n      -> {_SEAM_GUIDANCE[site.kind]}" for site in sites)


# ---------------------------------------------------------------------------
# The boundary
# ---------------------------------------------------------------------------


class TestEgressConsentBoundary:
    """#3030: project data may only leave the machine from a reasoned-about file."""

    def test_no_unlisted_file_holds_an_egress_sink(self) -> None:
        """A new sender in an unlisted file fails the build."""
        offenders = _collect_offenders(_SRC, _EGRESS_ALLOWLIST_FILES, _KNOWN_UNGATED_FILES)
        if offenders:
            files = sorted({site.relpath for site in offenders})
            pytest.fail(
                "#3030 egress boundary violation: transmit primitive(s) in "
                f"{len(files)} file(s) with no recorded consent seam "
                f"({len(offenders)} site(s)):\n"
                f"{_format(offenders)}\n\n"
                "Every path that causes project data to leave the machine must reach "
                "its consent answer through the data's OWN project_uuid — never through "
                "cwd, a checkout, a repo slug or a machine-global arming flag (FR-019), "
                "and an inability to determine consent is never consent (FR-003).\n"
                "If this sink genuinely carries no project data, add an entry to "
                "_EGRESS_ALLOWLIST in this file naming the reason, and record the "
                "growth in tests/architectural/_baselines.yaml with a justification.\n"
                "Inventory: kitty-specs/journal-project-consent-3030-01KYKWQS/"
                "egress-inventory.md"
            )

    def test_known_ungated_egress_paths_are_closed(self) -> None:
        """The work-list must be empty. An entry here is a red build, not a skip.

        Empty today. It held E1/E2/E3 (FR-028/029/030) while this gate was being
        authored; those landed and moved to ``_EGRESS_ALLOWLIST``. The failure
        text this would print is exercised by
        ``TestGuardBites::test_recording_an_open_path_reds_with_its_requirement``,
        so the reporting path stays proven while the set is empty — an assertion
        over an empty collection is a pass for having done nothing, which is the
        shape this whole module exists to avoid.
        """
        if _KNOWN_UNGATED:
            pytest.fail(_worklist_failure_text(_KNOWN_UNGATED))


class TestAllowlistIntegrity:
    """Meta-tests: the allowlist must not rot into a second RETIRED_DRAIN_NAMES."""

    def test_allowlisted_files_exist(self) -> None:
        """No stale entry may silently permit a path that has moved or been deleted."""
        missing = sorted(relpath for relpath in _EGRESS_ALLOWLIST_FILES | _KNOWN_UNGATED_FILES if not (_SRC / relpath).is_file())
        assert not missing, (
            "Stale egress-boundary entries — these files no longer exist, so their "
            f"allowance permits nothing and hides nothing: {missing}. Remove them and "
            "shrink the matching baseline in tests/architectural/_baselines.yaml."
        )

    def test_every_listed_file_still_holds_a_sink(self) -> None:
        """An entry that no longer guards anything must be deleted, not kept.

        This is the half that stops the allowlist rotting: an entry whose sink was
        refactored away keeps a file permanently exempt, which is how a name-shaped
        guard becomes blind without anyone editing it.
        """
        sink_files = {site.relpath for site in _scan(_SRC)}
        inert = sorted((_EGRESS_ALLOWLIST_FILES | _KNOWN_UNGATED_FILES) - sink_files)
        assert not inert, (
            "Egress-boundary entries that no longer hold any transmit primitive: "
            f"{inert}. The exemption now covers nothing while still exempting the "
            "file from every future sink added to it — delete the entry."
        )

    def test_seam_allowances_name_a_live_seam(self) -> None:
        """A ``SEAM`` allowance is only as good as the symbol it names.

        The annotation is load-bearing, not a comment: if the consent call is
        refactored out of the seam module, the allowance stops being true and this
        reds — rather than the file staying quietly exempt.
        """
        broken: list[str] = []
        for relpath, allowance in sorted(_EGRESS_ALLOWLIST.items()):
            if allowance.kind is not AllowanceKind.SEAM:
                continue
            assert allowance.seam_symbol and allowance.seam_module, f"{relpath}: a SEAM allowance must name both seam_symbol and seam_module."
            seam_path = _SRC / allowance.seam_module
            if not seam_path.is_file():
                broken.append(f"{relpath}: seam module {allowance.seam_module} is missing")
                continue
            if allowance.seam_symbol not in seam_path.read_text(encoding="utf-8"):
                broken.append(f"{relpath}: seam {allowance.seam_symbol} is gone from {allowance.seam_module} ({allowance.inventory_id})")
        assert not broken, (
            "Egress allowances whose named consent seam no longer exists:\n  "
            + "\n  ".join(broken)
            + "\nThe file is still permitted to transmit while the thing that made "
            "that safe has been removed. Restore the seam or re-classify the entry."
        )

    def test_non_seam_allowances_declare_a_closed_reason(self) -> None:
        """Every non-``SEAM`` allowance must carry a real reason and its evidence."""
        for relpath, allowance in sorted(_EGRESS_ALLOWLIST.items()):
            assert allowance.note.strip(), f"{relpath}: allowance carries no rationale."
            assert allowance.inventory_id.strip(), f"{relpath}: allowance names no inventory id."
            if allowance.kind is AllowanceKind.UNREACHABLE:
                assert allowance.pinned_by, (
                    f"{relpath}: an UNREACHABLE allowance rests on 'no caller exists', "
                    "which is a claim about the whole tree — it must name the test that "
                    "pins it, or it is an assertion nothing re-checks."
                )
                assert (_REPO_ROOT / allowance.pinned_by).is_file(), f"{relpath}: pinned_by {allowance.pinned_by} does not exist."

    def test_allowlist_and_worklist_are_disjoint(self) -> None:
        """A file cannot be both gated and known-ungated."""
        overlap = sorted(_EGRESS_ALLOWLIST_FILES & _KNOWN_UNGATED_FILES)
        assert not overlap, (
            f"{overlap} appear in both _EGRESS_ALLOWLIST and _KNOWN_UNGATED. The "
            "work-list entry would then be unfalsifiable — clearing it would change "
            "nothing, because the allowlist already permits the file."
        )

    def test_every_worklist_entry_names_its_requirement_and_seam(self) -> None:
        """The work-list must stay actionable, or it becomes a permanent exemption.

        Vacuous while the set is empty, which is why
        ``TestGuardBites::test_worklist_schema_check_rejects_an_unclearable_entry``
        exercises the same validator against a malformed entry.
        """
        problems = _worklist_schema_violations(_KNOWN_UNGATED)
        assert not problems, "Work-list entries that cannot be cleared:\n  " + "\n  ".join(problems)


class TestCompletenessLimitsDocstring:
    """Meta-test: FR-013 (`#3113`). The docstring's numbered gap list must stay honest."""

    def test_limit_8_positional_transport_call_is_documented(self) -> None:
        """A future trim of limit 8 must red here, not go unnoticed.

        Before this change the list ran 1-7 (getattr-by-string; empty callback
        registries; dynamic import/``exec``; variable-command ``subprocess``;
        at-rest pooling; bare ``.put(x)``; multi-sink-per-file). `#3113` adds
        exactly one entry: the all-positional / no-``headers=`` transport call.
        """
        doc = __doc__ or ""
        assert "8. **The all-positional / no-``headers=`` transport call.**" in doc, (
            "Module docstring's 'Completeness limits' list no longer states limit 8 "
            "(the all-positional / no-headers= transport call, #3113/FR-013). This "
            "entry documents a real blind spot in _transmits_a_body: update this "
            "assertion to match new wording, do not delete it."
        )
        assert "resolve_workspace_for_wp" in doc and "get_wp_lane" in doc, (
            "Limit 8 must keep naming the reproducible FR-015 false-positive "
            "functions, or the recorded reason the matcher was left alone silently "
            "disappears from the one place a future reader would look."
        )


class TestGuardBites:
    """Negative controls. A guard never observed to fail is decoration.

    Three plugins on this mission rotted into exactly that and reported false
    confidence in both directions, so these controls exercise the real collection
    path and assert the failure text, not just a boolean.

    `#3113`'s generalisation: a negative control that only tests the shape you
    thought of is not a negative control. ``test_scanner_detects_each_sink_shape``
    exercised the injected-transport shape only in its kwargs form
    (``poster(url, data=body, headers=hdrs, ...)``); an all-positional call of
    the identical shape (``poster(url, body, hdrs)``) evaded both the
    method-name rule and ``_transmits_a_body`` while the bite-test reported
    "not blind." Every rule in the sink vocabulary should carry a bite-test
    case per **shape** it claims to cover, not one per rule.
    """

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            pytest.param(
                "import requests\ndef go(p):\n    requests.post('https://x', json=p)\n",
                SinkKind.HTTP_VERB,
                id="requests-post",
            ),
            pytest.param(
                "def go(client, p):\n    return client.put('https://x', json=p)\n",
                SinkKind.HTTP_VERB,
                id="client-put-literal-url",
            ),
            pytest.param(
                "def go(client, url, p):\n    return client.put(url, data=p)\n",
                SinkKind.HTTP_VERB,
                id="client-put-url-variable",
            ),
            pytest.param(
                "def go(client, m, u):\n    return client.request(m, u)\n",
                SinkKind.HTTP_VERB,
                id="client-request",
            ),
            pytest.param(
                "import urllib.request\ndef go(r):\n    urllib.request.urlopen(r)\n",
                SinkKind.URLOPEN,
                id="urllib-urlopen",
            ),
            pytest.param(
                "from urllib.request import urlopen\ndef go(r):\n    urlopen(r)\n",
                SinkKind.URLOPEN,
                id="bare-urlopen",
            ),
            pytest.param(
                "async def go(c, e):\n    await c.send_event(e)\n",
                SinkKind.SEND_EVENT,
                id="send-event",
            ),
            pytest.param(
                "async def go(self, e):\n    await self.ws.send(e)\n",
                SinkKind.WEBSOCKET_SEND,
                id="ws-send",
            ),
            pytest.param(
                "def go(receiver, batch):\n    return receiver.deliver(batch)\n",
                SinkKind.RECEIVER_DELIVER,
                id="receiver-deliver",
            ),
            pytest.param(
                "def go(poster, url, body, hdrs):\n    return poster(url, data=body, headers=hdrs, timeout=5.0)\n",
                SinkKind.TRANSPORT_CALL,
                id="injected-transport-parameter",
            ),
            pytest.param(
                "def go(self, url, body, hdrs):\n    return self._send(url, json=body, headers=hdrs)\n",
                SinkKind.TRANSPORT_CALL,
                id="aliased-transport-method",
            ),
            pytest.param(
                "def go(poster, url, body, hdrs):\n    return poster(url, body, hdrs)\n",
                SinkKind.TRANSPORT_CALL,
                id="injected-transport-positional-url-name",
                marks=pytest.mark.xfail(
                    reason=(
                        "#3113 case (A): all-positional injected transport whose first "
                        "argument name IS in _URL_ARG_NAMES. _transmits_a_body requires "
                        "headers= AND a body keyword (:295-306), so an all-positional call "
                        "is invisible regardless of argument names. This is limit 8 in the "
                        "module docstring's completeness-limits list. FR-015 measured the "
                        "structural tightening (bare-Name callee resolving to an enclosing "
                        "FunctionDef parameter) BEFORE any matcher edit and found a "
                        "non-zero false-positive count over src/ (resolve_workspace_for_wp, "
                        "locate_work_package, behind_commits_touch_only_planning_artifacts, "
                        "get_wp_lane), so per FR-015's acceptance criteria the matcher is "
                        "left alone and this case is pinned red rather than fixed. Red-first "
                        "quoted: 'AssertionError: scanner went blind to transport-call / "
                        "assert []'."
                    ),
                    strict=True,
                ),
            ),
            pytest.param(
                "def relay(post, u, payload, meta):\n    return post(u, payload, meta)\n",
                SinkKind.TRANSPORT_CALL,
                id="injected-transport-positional-non-url-name",
                marks=pytest.mark.xfail(
                    reason=(
                        "#3113 case (B) -- THE ADOPTION GATE: all-positional injected "
                        "transport whose argument names (post, u, payload, meta) are "
                        "OUTSIDE _URL_ARG_NAMES. A matcher that passed (A) above but failed "
                        "this case would still be blind in exactly the way #3113 is about, "
                        "because _attr_tail returns node.id verbatim for a bare Name "
                        "(:266-272) -- (A) alone would certify a blind matcher. Same "
                        "limit-8 gap as (A); same FR-015 non-adoption decision (non-zero "
                        "false positives over src/, measured before any matcher edit). "
                        "Red-first quoted: 'AssertionError: scanner went blind to "
                        "transport-call / assert []'."
                    ),
                    strict=True,
                ),
            ),
        ],
    )
    def test_scanner_detects_each_sink_shape(self, tmp_path: Path, source: str, expected: SinkKind) -> None:
        """Every shape in the vocabulary is detected, so none can go blind unnoticed."""
        module = tmp_path / "sender.py"
        module.write_text(source, encoding="utf-8")
        sites = _find_sinks(module, tmp_path)
        assert sites, f"scanner went blind to {expected.value}"
        assert sites[0].kind is expected

    def test_unlisted_sender_is_reported_with_its_seam(self, tmp_path: Path) -> None:
        """The whole collection path reds on a synthetic un-allowlisted sender."""
        pkg = tmp_path / "specify_cli" / "widen"
        pkg.mkdir(parents=True)
        (pkg / "exfil.py").write_text(
            "import requests\ndef ship(rows):\n    requests.post('https://saas.example/api/ingest', json=rows)\n",
            encoding="utf-8",
        )
        offenders = _collect_offenders(tmp_path, _EGRESS_ALLOWLIST_FILES, _KNOWN_UNGATED_FILES)
        assert [site.relpath for site in offenders] == ["specify_cli/widen/exfil.py"]
        assert offenders[0].lineno == 3
        assert "project_uuid" in _format(offenders)

    def test_the_shape_the_name_keyed_guard_missed_is_caught(self, tmp_path: Path) -> None:
        """``drain_queue(...)`` then ``urlopen(...)`` — probed to evade RETIRED_DRAIN_NAMES.

        ``tests/sync/test_no_queue_drain_constructed_3030.py`` keys on two literal
        names, so a queue-backed sender under any third name is invisible to it.
        Keying on the sink catches this because the shape cannot avoid having one.
        """
        pkg = tmp_path / "specify_cli" / "sync"
        pkg.mkdir(parents=True)
        (pkg / "resend.py").write_text(
            "import urllib.request\n"
            "def flush(queue, url):\n"
            "    for row in queue.drain_queue(limit=100):\n"
            "        req = urllib.request.Request(url, data=row)\n"
            "        urllib.request.urlopen(req)\n",
            encoding="utf-8",
        )
        offenders = _collect_offenders(tmp_path, _EGRESS_ALLOWLIST_FILES, _KNOWN_UNGATED_FILES)
        assert [(s.relpath, s.kind) for s in offenders] == [("specify_cli/sync/resend.py", SinkKind.URLOPEN)]

    def test_allowlisting_the_same_sender_clears_it(self, tmp_path: Path) -> None:
        """Positive control: the guard is discriminating, not unconditionally red.

        Without this, an always-red collector would satisfy every control above
        while telling us nothing about the allowlist mechanism.
        """
        pkg = tmp_path / "specify_cli" / "widen"
        pkg.mkdir(parents=True)
        (pkg / "exfil.py").write_text(
            "import requests\ndef ship(rows):\n    requests.post('https://x', json=rows)\n",
            encoding="utf-8",
        )
        cleared = _collect_offenders(
            tmp_path,
            _EGRESS_ALLOWLIST_FILES | {"specify_cli/widen/exfil.py"},
            _KNOWN_UNGATED_FILES,
        )
        assert cleared == []

    def test_the_e20_preflight_shape_is_caught(self, tmp_path: Path) -> None:
        """A second sink reached through an injected transport is not invisible.

        E20: ``run_server_preflight`` POSTs the full envelope stream through a
        ``poster(...)`` parameter, earlier in the same function as the delivery
        call the inventory named. A method-name rule cannot see a bare ``Name``
        call, so gating where the inventory pointed would have left the leak.
        """
        pkg = tmp_path / "specify_cli" / "sync" / "history_import"
        pkg.mkdir(parents=True)
        (pkg / "preflight.py").write_text(
            "import gzip, json\n"
            "def preflight(envelopes, *, url, token, poster):\n"
            "    body = gzip.compress(json.dumps({'events': list(envelopes)}).encode())\n"
            "    return poster(url, data=body, headers={'Authorization': token}, timeout=30)\n",
            encoding="utf-8",
        )
        offenders = _collect_offenders(tmp_path, _EGRESS_ALLOWLIST_FILES, _KNOWN_UNGATED_FILES)
        assert [(s.relpath, s.kind) for s in offenders] == [("specify_cli/sync/history_import/preflight.py", SinkKind.TRANSPORT_CALL)]
        assert "project_uuid" in _format(offenders)

    def test_request_value_constructors_are_not_sinks(self, tmp_path: Path) -> None:
        """``Request(url, data=..., headers=...)`` builds a value; it transmits nothing.

        Without this the callee-agnostic rule would flag every stdlib request
        construction, and the noise is what gets a gate weakened.
        """
        module = tmp_path / "build.py"
        module.write_text(
            "import urllib.request\ndef build(url, body, hdrs):\n    return urllib.request.Request(url, data=body, headers=hdrs)\n",
            encoding="utf-8",
        )
        assert _find_sinks(module, tmp_path) == []

    def test_recording_an_open_path_reds_with_its_requirement(self) -> None:
        """The work-list's reporting path stays proven while the set is empty.

        ``test_known_ungated_egress_paths_are_closed`` currently asserts over an
        empty dict, which passes for having done nothing. This exercises the text
        it would print, so a future entry cannot fail silently or unhelpfully.
        """
        entry = UngatedPath(
            inventory_id="E-synthetic",
            requirement="FR-999",
            seam_required="specify_cli.sync.consent, on the data's own project_uuid",
            note="Synthetic control; not a real path.",
        )
        text = _worklist_failure_text({"specify_cli/widen/exfil.py": entry})
        assert "specify_cli/widen/exfil.py" in text
        assert "FR-999" in text
        assert "seam required:" in text

    def test_worklist_schema_check_rejects_an_unclearable_entry(self) -> None:
        """An entry with no requirement or no seam is an exemption, not a work-list.

        Named, not counted. ``bad`` is defective in all three ways at once, so a
        count of three passes just as happily when one check fires three times and
        the other two are dead — which is how a schema guard quietly stops guarding
        two of the three ways an entry becomes unclearable.
        """
        bad = UngatedPath(inventory_id="E-x", requirement="soon", seam_required="  ", note="")
        problems = _worklist_schema_violations({"specify_cli/widen/exfil.py": bad})
        assert problems == [
            "specify_cli/widen/exfil.py: requirement 'soon' does not name an FR — nobody can tell when it clears",
            "specify_cli/widen/exfil.py: names no seam it has to call, so nobody can clear it",
            "specify_cli/widen/exfil.py: carries no description of the path",
        ]
        assert _worklist_schema_violations({}) == []

    def test_non_sink_code_is_not_flagged(self, tmp_path: Path) -> None:
        """No false positives on ordinary code, or the gate gets weakened to shut it up.

        This control earned its place: on its first run it caught ``mailbox.put``
        matching the ``.put`` verb, which would have made an unrelated queue write
        red the boundary — and the natural remedy for a spurious red is to weaken
        the gate. The scanner was narrowed instead (limit 6).
        """
        module = tmp_path / "quiet.py"
        module.write_text(
            "def go(mailbox, queue, parser, item):\n"
            "    mailbox.put(item)\n"
            "    queue.put(item, block=False, timeout=1)\n"
            "    parser.parse(item)\n"
            "    parser.send(item)\n"
            "    return item.post_id\n",
            encoding="utf-8",
        )
        assert _find_sinks(module, tmp_path) == []


# ---------------------------------------------------------------------------
# FR-015 (`#3113`): the src/-wide false-positive measurement for the candidate
# tightening, taken BEFORE any matcher edit (binding order, WP10 T031/T032).
# ---------------------------------------------------------------------------
#
# The candidate predicate: the callee is a bare ``ast.Name`` whose ``id``
# resolves to a parameter of the *enclosing* ``FunctionDef``/``AsyncFunctionDef``
# (nearest enclosing only) — transport injected as a parameter, decidable with
# no author-chosen word. This is deliberately NOT wired into ``_classify`` /
# ``_find_sinks`` above: ``_classify(node: ast.Call)`` is reached from a flat
# ``ast.walk(tree)`` at ``_find_sinks`` and carries no enclosing-scope
# information, so adopting the predicate for real would be a scanner
# restructure (threading the enclosing function's parameter set through the
# walk), not a branch edit. That cost is paid only if this measurement returns
# zero false positives. It does not — see below — so the real matcher (above)
# is untouched, and this section exists solely to make the false-positive
# count reproducible rather than a recollection.


def _fr015_candidate_param_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """Every positional/positional-only/keyword-only parameter name of *fn*.

    ``*args``/``**kwargs`` are deliberately excluded: neither resolves to a
    single named parameter holding one callable value.
    """
    args = fn.args
    names = {a.arg for a in args.posonlyargs} | {a.arg for a in args.args} | {a.arg for a in args.kwonlyargs}
    return frozenset(names)


def _find_fr015_candidates(path: Path, root: Path) -> list[SinkSite]:
    """Every call in *path* whose callee is a bare Name resolving to a
    parameter of its nearest-enclosing function (FR-015's candidate predicate).

    Measurement-only, as above: this walks with enclosing-function parameter
    tracking that ``_find_sinks`` does not do, specifically so the FR-015
    false-positive count is measurable without restructuring the real gate.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - defensive
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - a louder problem than this rule
        return []

    relpath = path.relative_to(root).as_posix()
    sites: list[SinkSite] = []
    param_stack: list[frozenset[str]] = []

    class _EnclosingParamVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            param_stack.append(_fr015_candidate_param_names(node))
            self.generic_visit(node)
            param_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            param_stack.append(_fr015_candidate_param_names(node))
            self.generic_visit(node)
            param_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            if param_stack and isinstance(node.func, ast.Name) and node.func.id in param_stack[-1]:
                sites.append(SinkSite(relpath=relpath, lineno=node.lineno, kind=SinkKind.TRANSPORT_CALL, snippet=node.func.id))
            self.generic_visit(node)

    _EnclosingParamVisitor().visit(tree)
    return sites


def _scan_fr015_candidates(root: Path) -> list[SinkSite]:
    """Every FR-015 candidate site under *root*, excluding ``__pycache__``."""
    sites: list[SinkSite] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sites.extend(_find_fr015_candidates(path, root))
    return sites


class TestFR015StructuralTighteningMeasurement:
    """`#3113` / FR-015: measured BEFORE any matcher edit, per the WP's binding order.

    Reproducible command::

        PYTHONPATH=<worktree>/src pytest \\
            tests/architectural/test_egress_consent_boundary.py::TestFR015StructuralTighteningMeasurement -v

    Measured at this commit: 1198 ``.py`` files under ``src/`` scanned; the
    candidate predicate (see the module-level comment above) finds 203
    candidate call sites in 112 files. Of those, 195 sites in 106 files are
    "new offenders" — in a file neither in ``_EGRESS_ALLOWLIST_FILES`` nor
    ``_KNOWN_UNGATED_FILES`` — and among the new offenders at least 5 are
    confirmed, reproducible false positives: calls to
    ``resolve_workspace_for_wp`` (twice, in two different files),
    ``locate_work_package``, ``behind_commits_touch_only_planning_artifacts``
    and ``get_wp_lane``, each a dependency-injected work-package/lane lookup
    function reached through a same-named ``Callable``-typed parameter — not a
    transport. (This aggregate site/file total differs from an earlier
    planning-time figure of 211 sites / 13 files; the 5 named false positives
    reproduce identically under either count, so the FR-015 decision — decline
    — does not depend on reconciling the totals. See WP10's transition note
    for the fuller reconciliation.)

    Per FR-015's acceptance criteria a non-zero false-positive count is itself
    the outcome: **the matcher is left alone.** This test pins that
    measurement rather than only asserting it once: it fails loudly if the
    four named false positives stop reproducing (the measurement rotted) or if
    the false-positive count ever drops to zero (the signal that FR-015's
    scanner restructure is now funded and this decision should be revisited).
    """

    #: The four functions FR-015's planning-time measurement named. Each is a
    #: real function elsewhere in the tree, reached here through a same-named
    #: ``Callable``-typed parameter (a dependency-injection pattern) — not a
    #: transport of any kind.
    _KNOWN_FALSE_POSITIVE_CALLEES: frozenset[str] = frozenset(
        {
            "resolve_workspace_for_wp",
            "locate_work_package",
            "behind_commits_touch_only_planning_artifacts",
            "get_wp_lane",
        }
    )

    def test_candidate_tightening_yields_nonzero_false_positives_over_src(self) -> None:
        files_scanned = [p for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts]
        candidates = _scan_fr015_candidates(_SRC)
        candidate_files = {c.relpath for c in candidates}

        permitted = _EGRESS_ALLOWLIST_FILES | _KNOWN_UNGATED_FILES
        new_offenders = [c for c in candidates if c.relpath not in permitted]
        new_offender_files = {c.relpath for c in new_offenders}

        reproduced = {c.snippet for c in new_offenders if c.snippet in self._KNOWN_FALSE_POSITIVE_CALLEES}
        assert reproduced == self._KNOWN_FALSE_POSITIVE_CALLEES, (
            f"Expected all four named FR-015 false positives to reproduce; got {sorted(reproduced)} "
            f"of {sorted(self._KNOWN_FALSE_POSITIVE_CALLEES)}. Input: {len(files_scanned)} .py files "
            f"scanned, {len(candidates)} candidate sites in {len(candidate_files)} files, "
            f"{len(new_offenders)} new-offender sites in {len(new_offender_files)} files. If this set "
            "has changed, the FR-015 measurement needs re-running before the non-adoption decision "
            "can be trusted."
        )
        assert len(new_offenders) > 0, (
            f"FR-015 candidate tightening measured 0 new-offender sites over src/ "
            f"({len(files_scanned)} .py files scanned, {len(candidates)} candidate sites in "
            f"{len(candidate_files)} files). Per FR-015's acceptance criteria this is the ADOPT "
            "branch: the scanner restructure (threading enclosing-FunctionDef parameter sets "
            "through _find_sinks) is now funded, and this module's 'matcher left alone' decision "
            "(limit 8, TestGuardBites' two xfail cases) is stale — revisit WP10 T031/T032."
        )


# ---------------------------------------------------------------------------
# Per-project store mission: named sender and local-writer hand-off (WP01)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class _SymbolRef:
    relpath: str
    qualname: str


class _ResultState(StrEnum):
    DURABLE = "durable-result-write"
    DURABLE_FALLBACK = "durable-fallback-not-success"
    DURABLE_FILE = "durable-file-result"
    IN_MEMORY = "in-memory-result-only"
    MISSING = "no-durable-result-write"


@dataclass(frozen=True)
class _ProjectSyncSender:
    surface: str
    request_start: _SymbolRef
    result_write: _SymbolRef | None
    result_state: _ResultState
    final_owner: str
    channel_2_narrowing_only: bool = False


_PROJECT_SYNC_SENDER_MATRIX = (
    _ProjectSyncSender(
        "direct dispatcher",
        _SymbolRef("specify_cli/delivery/receivers.py", "_HttpReceiver._attempt_batch_send"),
        _SymbolRef("specify_cli/sync/transport_attempts.py", "_record_delivery_result"),
        _ResultState.DURABLE,
        "WP07",
    ),
    _ProjectSyncSender(
        "emitter websocket",
        _SymbolRef("specify_cli/sync/client.py", "WebSocketClient._flush_pending_project_events"),
        _SymbolRef("specify_cli/sync/queue.py", "OfflineQueue.queue_event"),
        _ResultState.DURABLE_FALLBACK,
        "WP07",
    ),
    _ProjectSyncSender(
        "daemon publish",
        _SymbolRef("specify_cli/sync/runtime.py", "SyncRuntime._send_websocket_event"),
        _SymbolRef("specify_cli/sync/transport_attempts.py", "_record_delivery_result"),
        _ResultState.DURABLE,
        "WP08",
    ),
    _ProjectSyncSender(
        "event relay",
        _SymbolRef("specify_cli/sync/events.py", "_publish_event_via_sync_daemon"),
        None,
        _ResultState.MISSING,
        "WP07",
    ),
    _ProjectSyncSender(
        "body drain",
        _SymbolRef("specify_cli/sync/body_transport.py", "_send_content_request"),
        _SymbolRef("specify_cli/sync/body_queue.py", "OfflineBodyUploadQueue._update"),
        _ResultState.DURABLE,
        "WP07",
    ),
    _ProjectSyncSender(
        "final and exit sync",
        _SymbolRef("specify_cli/delivery/receivers.py", "_HttpReceiver._attempt_batch_send"),
        _SymbolRef("specify_cli/sync/transport_attempts.py", "_record_delivery_result"),
        _ResultState.DURABLE,
        "WP07",
    ),
    _ProjectSyncSender(
        "reconnect local commit",
        _SymbolRef("specify_cli/sync/client.py", "WebSocketClient._send_wire"),
        _SymbolRef("specify_cli/sync/local_commit.py", "reconcile_local_commit_result"),
        _ResultState.DURABLE_FILE,
        "WP07",
    ),
    _ProjectSyncSender(
        "history import",
        _SymbolRef("specify_cli/sync/history_import/upload.py", "_deliver_chunks"),
        _SymbolRef("specify_cli/sync/history_import/upload.py", "_tally"),
        _ResultState.IN_MEMORY,
        "WP07",
    ),
    _ProjectSyncSender(
        "tracker hosted channel",
        _SymbolRef("specify_cli/tracker/saas_client.py", "SaaSTrackerClient._physical_request_with_retry"),
        _SymbolRef("specify_cli/sync/transport_attempts.py", "_record_delivery_result"),
        _ResultState.DURABLE,
        "WP07",
        channel_2_narrowing_only=True,
    ),
    _ProjectSyncSender(
        "generic SaaS client",
        _SymbolRef("specify_cli/saas_client/client.py", "SaasClient._send_generic_operation"),
        _SymbolRef("specify_cli/sync/transport_attempts.py", "_record_delivery_result"),
        _ResultState.DURABLE,
        "WP07",
    ),
)

_SENDER_CONTRACT = frozenset(
    {
        "direct dispatcher",
        "emitter websocket",
        "daemon publish",
        "event relay",
        "body drain",
        "final and exit sync",
        "reconnect local commit",
        "history import",
        "tracker hosted channel",
        "generic SaaS client",
    }
)


@dataclass(frozen=True)
class _WP09IntegrationRow:
    surface: str
    symbol: _SymbolRef
    required_delegate: str | None
    final_owner: str
    classification: str = "hosted_sender"


# T040 closes the post-WP07/WP08 hand-off.  These are the non-physical-sink
# producer/discovery/control rows that feed the ten physical families above;
# omitting them would let a file-level sink allowance hide a new raw bypass.
_WP09_INTEGRATION_ROWS = (
    _WP09IntegrationRow(
        "runtime mission start",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_mission_run_started"),
        "emit_mission_run_started",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime next step",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_next_step_issued"),
        "emit_next_step_issued",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime auto complete",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_next_step_auto_completed"),
        "emit_next_step_auto_completed",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime decision request",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_decision_input_requested"),
        "emit_decision_input_requested",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime decision answer",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_decision_input_answered"),
        "emit_decision_input_answered",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime mission complete",
        _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter.emit_mission_run_completed"),
        "emit_mission_run_completed",
        "WP07",
    ),
    _WP09IntegrationRow(
        "runtime significance local-only",
        _SymbolRef(
            "specify_cli/sync/runtime_event_emitter.py",
            "SyncRuntimeEventEmitter.emit_significance_evaluated",
        ),
        None,
        "WP07",
        "local_only",
    ),
    _WP09IntegrationRow(
        "runtime timeout local-only",
        _SymbolRef(
            "specify_cli/sync/runtime_event_emitter.py",
            "SyncRuntimeEventEmitter.emit_decision_timeout_expired",
        ),
        None,
        "WP07",
        "local_only",
    ),
    _WP09IntegrationRow(
        "runtime phase transition", _SymbolRef("specify_cli/sync/runtime_event_emitter.py", "SyncRuntimeEventEmitter._enter_phase"), "emit_phase_entered", "WP07"
    ),
    _WP09IntegrationRow("dossier artifact indexed", _SymbolRef("specify_cli/dossier/events.py", "emit_artifact_indexed"), "fire_dossier_event", "WP07"),
    _WP09IntegrationRow("dossier artifact missing", _SymbolRef("specify_cli/dossier/events.py", "emit_artifact_missing"), "fire_dossier_event", "WP07"),
    _WP09IntegrationRow("dossier snapshot", _SymbolRef("specify_cli/dossier/events.py", "emit_snapshot_computed"), "fire_dossier_event", "WP07"),
    _WP09IntegrationRow("dossier parity drift", _SymbolRef("specify_cli/dossier/events.py", "emit_parity_drift_detected"), "fire_dossier_event", "WP07"),
    _WP09IntegrationRow("dossier adapter", _SymbolRef("specify_cli/dossier/emitter_adapter.py", "fire_dossier_event"), "_emitter", "WP07"),
    # Anchored at _enqueue_artifact since main's S107/S3776 decomposition of
    # prepare_body_uploads (prepare_body_uploads -> _process_artifact ->
    # _enqueue_artifact); the terminal body_queue.enqueue delegation this row
    # proves is unchanged, one extracted helper deeper.
    _WP09IntegrationRow("body enqueue", _SymbolRef("specify_cli/sync/body_upload.py", "_enqueue_artifact"), "enqueue", "WP07"),
    _WP09IntegrationRow(
        "background project discovery",
        _SymbolRef("specify_cli/sync/background.py", "BackgroundSyncService._drain_discovered_body_queues"),
        "_enumerate_project_store_candidates",
        "WP08",
    ),
    _WP09IntegrationRow(
        "background public body drain", _SymbolRef("specify_cli/sync/background.py", "BackgroundSyncService.drain_body_uploads_only"), "_drain_body_queues", "WP08"
    ),
    _WP09IntegrationRow(
        "background gated body transport",
        _SymbolRef("specify_cli/sync/background.py", "BackgroundSyncService._drain_discovered_body_queues"),
        "push_content_with_transport_gate",
        "WP08",
    ),
    _WP09IntegrationRow("daemon publish endpoint", _SymbolRef("specify_cli/sync/daemon.py", "SyncDaemonHandler.handle_sync_publish"), "publish_event", "WP08"),
    _WP09IntegrationRow(
        "daemon public publish", _SymbolRef("specify_cli/sync/runtime.py", "SyncRuntime.publish_event"), "event_project_consents_to_publish", "WP08"
    ),
    _WP09IntegrationRow("daemon websocket terminal ack", _SymbolRef("specify_cli/sync/runtime.py", "SyncRuntime._send_websocket_event"), "send_event", "WP08"),
)


@dataclass(frozen=True)
class _WP09SinkClassification:
    symbol: _SymbolRef
    matrix_families: frozenset[str]
    rationale: str


def _wp09_sink(
    relpath: str,
    qualname: str,
    *families: str,
    rationale: str = "project-bearing transport",
) -> _WP09SinkClassification:
    return _WP09SinkClassification(
        _SymbolRef(relpath, qualname),
        frozenset(families),
        rationale,
    )


_WP09_MATRIX_FAMILIES = frozenset(
    {
        "direct_dispatcher",
        "emitter_websocket",
        "daemon_publish",
        "event_relay",
        "body_drain",
        "final_exit_sync",
        "reconnect_local_commit",
        "history_import",
        "tracker_hosted",
        "generic_saas",
    }
)

# Every source-discovered sink symbol is classified here. Empty family sets are
# explicit non-project loopback/control rows, never an accidental omission.
_WP09_SINK_CLASSIFICATIONS = (
    _wp09_sink("specify_cli/delivery/receivers.py", "_HttpReceiver._attempt_batch_send", "direct_dispatcher", "final_exit_sync", "history_import"),
    _wp09_sink("specify_cli/delivery/receivers.py", "default_http_poster", "direct_dispatcher", "final_exit_sync", "history_import"),
    _wp09_sink("specify_cli/saas_client/client.py", "SaasClient._send_generic_operation", "generic_saas"),
    _wp09_sink("specify_cli/sync/body_transport.py", "_send_content_request", "body_drain"),
    _wp09_sink("specify_cli/sync/client.py", "WebSocketClient._flush_pending_project_events", "emitter_websocket"),
    _wp09_sink("specify_cli/sync/client.py", "WebSocketClient._send_wire", "emitter_websocket", "daemon_publish", "reconnect_local_commit"),
    _wp09_sink("specify_cli/sync/client.py", "WebSocketClient._handle_ping", rationale="WebSocket pong carries no project payload"),
    _wp09_sink("specify_cli/sync/daemon.py", "_fetch_health_payload", rationale="loopback daemon health control"),
    _wp09_sink("specify_cli/sync/daemon.py", "_stop_daemon_by_http", rationale="loopback daemon shutdown control"),
    _wp09_sink(
        "specify_cli/sync/daemon_protocol.py",
        "_fetch_json",
        rationale="WP10 loopback migration-daemon control",
    ),
    _wp09_sink("specify_cli/sync/events.py", "_publish_event_via_sync_daemon", "event_relay"),
    _wp09_sink("specify_cli/sync/events.py", "_request_dashboard_sync", rationale="loopback daemon trigger control"),
    _wp09_sink("specify_cli/sync/history_import/upload.py", "_deliver_chunks", "history_import"),
    _wp09_sink("specify_cli/sync/history_import/upload.py", "_post_server_preflight", "history_import"),
    _wp09_sink("specify_cli/sync/orphan_sweep.py", "_http_shutdown_no_token", rationale="loopback orphan-daemon shutdown control"),
    _wp09_sink("specify_cli/sync/runtime.py", "SyncRuntime._send_websocket_event", "daemon_publish"),
    _wp09_sink("specify_cli/sync/sharing_client.py", "delete_private_project", "generic_saas"),
    _wp09_sink("specify_cli/sync/sharing_client.py", "leave_repository_share", "generic_saas"),
    _wp09_sink("specify_cli/sync/sharing_client.py", "request_repository_share", "generic_saas"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient._request", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient._physical_request_with_retry", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient._request_with_retry", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient.bind_confirm", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient.bind_mission_origin", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient.push", "tracker_hosted"),
    _wp09_sink("specify_cli/tracker/saas_client.py", "SaaSTrackerClient.run", "tracker_hosted"),
)


_PROJECT_SENDER_ROOTS = (
    _SRC / "specify_cli" / "delivery",
    _SRC / "specify_cli" / "sync",
    _SRC / "specify_cli" / "tracker",
    _SRC / "specify_cli" / "saas_client",
)


@dataclass(frozen=True, order=True)
class _ProjectSinkSite:
    relpath: str
    qualname: str
    kind: SinkKind
    callee: str
    lineno: int
    canonical_attempt: bool

    @property
    def key(self) -> str:
        return f"{self.relpath}::{self.qualname}::{self.kind.value}::{self.callee}"


@dataclass(frozen=True)
class _ContextBinding:
    version: int
    dependency_versions: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class _AttemptBinding:
    version: int
    context_name: str
    context_version: int
    body_dump: str | None
    body_dependency_versions: tuple[tuple[str, int], ...]


@dataclass
class _SinkFlowState:
    aliases: dict[str, ast.expr] = field(default_factory=dict)
    versions: Counter[str] = field(default_factory=Counter)
    contexts: dict[str, _ContextBinding] = field(default_factory=dict)
    attempts: dict[str, _AttemptBinding] = field(default_factory=dict)
    eligible: dict[str, int] = field(default_factory=dict)

    def branch(self) -> _SinkFlowState:
        return _SinkFlowState(
            self.aliases.copy(),
            self.versions.copy(),
            self.contexts.copy(),
            self.attempts.copy(),
            self.eligible.copy(),
        )


class _SinkFunctionAnalyzer:
    def __init__(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        relpath: str,
        qualname: str,
    ) -> None:
        self.node = node
        self.relpath = relpath
        self.qualname = qualname
        self.sites: list[_ProjectSinkSite] = []

    @staticmethod
    def _argument_names(call: ast.Call) -> set[str]:
        return {child.id for argument in (*call.args, *(kw.value for kw in call.keywords)) for child in ast.walk(argument) if isinstance(child, ast.Name)}

    @staticmethod
    def _dependency_versions(
        expression: ast.expr,
        state: _SinkFlowState,
    ) -> tuple[tuple[str, int], ...]:
        return tuple(sorted((name, state.versions[name]) for name in _SinkFunctionAnalyzer._names(expression)))

    @staticmethod
    def _names(expression: ast.AST) -> set[str]:
        return {child.id for child in ast.walk(expression) if isinstance(child, ast.Name)}

    @staticmethod
    def _delivery_body(call: ast.Call, context_name: str) -> ast.expr | None:
        for keyword in call.keywords:
            if keyword.arg in {"body", "event", "payload"}:
                return keyword.value
        for argument in call.args:
            if not (isinstance(argument, ast.Name) and argument.id == context_name):
                return argument
        return None

    @staticmethod
    def _resolve_alias(
        expression: ast.expr,
        state: _SinkFlowState,
    ) -> ast.expr:
        resolved = expression
        seen: set[str] = set()
        while isinstance(resolved, ast.Name) and resolved.id in state.aliases:
            if resolved.id in seen:
                break
            seen.add(resolved.id)
            resolved = state.aliases[resolved.id]
        return resolved

    def _apply_binding(
        self,
        item: ast.Assign | ast.AnnAssign,
        state: _SinkFlowState,
    ) -> None:
        # TODO(#3280): Resolve tuple and other non-name assignment targets; current alias evidence is name-target only.
        targets = item.targets if isinstance(item, ast.Assign) else [item.target]
        value = item.value
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            alias = self._resolve_alias(value, state) if isinstance(value, (ast.Name, ast.Attribute)) else None
            state.versions[name] += 1
            state.aliases.pop(name, None)
            state.contexts.pop(name, None)
            state.attempts.pop(name, None)
            state.eligible.pop(name, None)
            if alias is not None:
                state.aliases[name] = alias
            if not isinstance(value, ast.Call):
                continue
            tail = _attr_tail(value.func)
            if tail == "ProjectSyncContext" and (value.args or any(keyword.arg == "project_uuid" for keyword in value.keywords)):
                project = next(
                    (keyword.value for keyword in value.keywords if keyword.arg == "project_uuid"),
                    value.args[0] if value.args else value,
                )
                state.contexts[name] = _ContextBinding(
                    state.versions[name],
                    self._dependency_versions(project, state),
                )
            elif tail == "DeliveryAttempt":
                context = next(
                    (candidate for candidate in self._argument_names(value) if candidate in state.contexts),
                    None,
                )
                if context is None:
                    continue
                context_binding = state.contexts[context]
                if any(state.versions[dependency] != version for dependency, version in context_binding.dependency_versions):
                    continue
                body = self._delivery_body(value, context)
                state.attempts[name] = _AttemptBinding(
                    state.versions[name],
                    context,
                    context_binding.version,
                    ast.dump(body, include_attributes=False) if body else None,
                    self._dependency_versions(body, state) if body else (),
                )

    def _guarded_attempt(
        self,
        test: ast.expr,
        state: _SinkFlowState,
    ) -> tuple[str | None, bool]:
        inverted = isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
        candidate = test.operand if isinstance(test, ast.UnaryOp) and inverted else test
        if not isinstance(candidate, ast.Call) or _attr_tail(candidate.func) != "final_transport_eligible":
            return None, inverted
        attempt = next(
            (name for name in self._argument_names(candidate) if name in state.attempts and state.attempts[name].version == state.versions[name]),
            None,
        )
        return attempt, inverted

    @staticmethod
    def _transmitted_body(call: ast.Call) -> ast.expr | None:
        for keyword in call.keywords:
            if keyword.arg in {"json", "data", "content", "body", "payload", "event"}:
                return keyword.value
        return call.args[-1] if call.args else None

    def _coherent_attempt(
        self,
        call: ast.Call,
        state: _SinkFlowState,
    ) -> bool:
        body = self._transmitted_body(call)
        if body is None:
            return False
        body_dump = ast.dump(body, include_attributes=False)
        body_names = self._names(body)
        for name, eligible_version in state.eligible.items():
            attempt = state.attempts.get(name)
            if attempt is None or attempt.version != eligible_version:
                continue
            context = state.contexts.get(attempt.context_name)
            stable = (
                state.versions[name] == attempt.version
                and context is not None
                and context.version == attempt.context_version
                and all(
                    state.versions[dependency] == version
                    for dependency, version in (
                        *context.dependency_versions,
                        *attempt.body_dependency_versions,
                    )
                )
            )
            related = name in body_names or (attempt.body_dump is not None and attempt.body_dump == body_dump)
            if stable and related:
                return True
        return False

    def _inspect_call(self, call: ast.Call, state: _SinkFlowState) -> None:
        resolved = call
        callee = ast.unparse(call.func)
        if isinstance(call.func, ast.Name) and call.func.id in state.aliases:
            alias = self._resolve_alias(call.func, state)
            resolved = ast.Call(
                func=alias,
                args=call.args,
                keywords=call.keywords,
            )
            callee = ast.unparse(alias)
        kind = _classify(resolved)
        if kind is None:
            return
        self.sites.append(
            _ProjectSinkSite(
                self.relpath,
                self.qualname,
                kind,
                callee,
                call.lineno,
                self._coherent_attempt(call, state),
            )
        )

    def _inspect_block(
        self,
        statements: list[ast.stmt],
        state: _SinkFlowState,
    ) -> None:
        for statement in statements:
            if isinstance(statement, ast.If):
                # TODO(#3280): Join post-branch alias states; this bounded pass only follows each branch independently.
                attempt, inverted = self._guarded_attempt(statement.test, state)
                terminal_guard = bool(statement.body) and isinstance(
                    statement.body[-1],
                    (ast.Return, ast.Raise),
                )
                if attempt and not inverted:
                    body_state = state.branch()
                    body_state.eligible[attempt] = body_state.versions[attempt]
                    self._inspect_block(statement.body, body_state)
                else:
                    self._inspect_block(statement.body, state.branch())
                self._inspect_block(statement.orelse, state.branch())
                if attempt and inverted and terminal_guard:
                    state.eligible[attempt] = state.versions[attempt]
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for call in (child for child in ast.walk(statement) if isinstance(child, ast.Call)):
                self._inspect_call(call, state)
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                self._apply_binding(statement, state)

    def run(self) -> list[_ProjectSinkSite]:
        self._inspect_block(self.node.body, _SinkFlowState())
        return self.sites


class _ProjectSinkVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_root: Path) -> None:
        self.path = path
        self.source_root = source_root
        self.classes: list[str] = []
        self.sites: list[_ProjectSinkSite] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = ".".join((*self.classes, node.name))
        analyzer = _SinkFunctionAnalyzer(
            node,
            self.path.relative_to(self.source_root).as_posix(),
            qualname,
        )
        self.sites.extend(analyzer.run())

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)


def _scan_project_sinks(
    paths: tuple[Path, ...] | None = None,
    *,
    source_root: Path = _SRC,
) -> tuple[_ProjectSinkSite, ...]:
    if paths is None:
        roots = _PROJECT_SENDER_ROOTS if source_root == _SRC else (source_root,)
        paths = _layout_paths(roots)
    sites: list[_ProjectSinkSite] = []
    for path in sorted(paths):
        visitor = _ProjectSinkVisitor(path, source_root)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        sites.extend(visitor.sites)
    return tuple(sorted(sites))


_KNOWN_PROJECT_SINK_COUNTS: Counter[str] = Counter(
    line.strip()
    for line in """
specify_cli/delivery/receivers.py::_HttpReceiver._attempt_batch_send::transport-call::self._poster
specify_cli/delivery/receivers.py::default_http_poster::http-verb::requests.post
specify_cli/saas_client/client.py::SaasClient._send_generic_operation::http-verb::self._http.post
specify_cli/sync/body_transport.py::_send_content_request::http-verb::requests.post
specify_cli/sync/body_transport.py::_send_content_request::transport-call::request_with_stdlib_fallback_sync
specify_cli/sync/body_transport.py::_send_content_request::transport-call::request_with_stdlib_fallback_sync
specify_cli/sync/client.py::WebSocketClient._flush_pending_project_events::send-event::self.send_event
specify_cli/sync/client.py::WebSocketClient._handle_ping::websocket-send::self.ws.send
specify_cli/sync/client.py::WebSocketClient._send_wire::websocket-send::self.ws.send
specify_cli/sync/daemon.py::_fetch_health_payload::urlopen::urllib.request.urlopen
specify_cli/sync/daemon.py::_stop_daemon_by_http::urlopen::urllib.request.urlopen
specify_cli/sync/events.py::_publish_event_via_sync_daemon::urlopen::urllib.request.urlopen
specify_cli/sync/events.py::_request_dashboard_sync::urlopen::urllib.request.urlopen
specify_cli/sync/history_import/upload.py::_deliver_chunks::receiver-deliver::receiver.deliver
specify_cli/sync/history_import/upload.py::_post_server_preflight::transport-call::poster
specify_cli/sync/orphan_sweep.py::_http_shutdown_no_token::urlopen::urllib.request.urlopen
specify_cli/sync/runtime.py::SyncRuntime._send_websocket_event::send-event::self.ws_client.send_event
specify_cli/sync/sharing_client.py::delete_private_project::http-verb::client.post
specify_cli/sync/sharing_client.py::leave_repository_share::http-verb::client.post
specify_cli/sync/sharing_client.py::request_repository_share::http-verb::client.post
specify_cli/tracker/saas_client.py::SaaSTrackerClient._request::http-verb::client.request
specify_cli/tracker/saas_client.py::SaaSTrackerClient._physical_request_with_retry::transport-call::self._request
specify_cli/tracker/saas_client.py::SaaSTrackerClient._physical_request_with_retry::transport-call::self._request
specify_cli/tracker/saas_client.py::SaaSTrackerClient._physical_request_with_retry::transport-call::self._request
specify_cli/tracker/saas_client.py::SaaSTrackerClient._request_with_retry::transport-call::self._physical_request_with_retry
specify_cli/tracker/saas_client.py::SaaSTrackerClient.bind_confirm::transport-call::self._request_with_retry
specify_cli/tracker/saas_client.py::SaaSTrackerClient.bind_mission_origin::transport-call::self._request_with_retry
specify_cli/tracker/saas_client.py::SaaSTrackerClient.push::transport-call::self._request_with_retry
specify_cli/tracker/saas_client.py::SaaSTrackerClient.run::transport-call::self._request_with_retry
""".splitlines()
    if line.strip()
)

_WP10_LOOPBACK_CONTROL_SINK_COUNTS: Counter[str] = Counter(
    {
        "specify_cli/sync/daemon_protocol.py::_fetch_json::urlopen::urllib.request.urlopen": 1,
    }
)


def _new_sender_violations(
    sites: tuple[_ProjectSinkSite, ...],
    baseline: Counter[str],
) -> tuple[_ProjectSinkSite, ...]:
    seen: Counter[str] = Counter()
    violations: list[_ProjectSinkSite] = []
    for site in sites:
        seen[site.key] += 1
        if seen[site.key] > baseline[site.key] and not site.canonical_attempt:
            violations.append(site)
    return tuple(violations)


_KNOWN_NON_MUTATING_SQL = frozenset({"SELECT", "PRAGMA", "EXPLAIN", "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE"})
_UNRESOLVED_SQL = "UNRESOLVED"


@dataclass(frozen=True, order=True)
class _LayoutWriteSite:
    relpath: str
    qualname: str
    operation: str
    callee: str
    statement: str
    owner_wp: str
    lineno: int

    @property
    def key(self) -> str:
        return f"{self.relpath}::{self.qualname}::{self.operation}::{self.callee}"


def _constant_strings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns = [child.value for child in ast.walk(node) if isinstance(child, ast.Return) and child.value is not None]
            rendered_returns = [_sql_text(value, values) for value in returns]
            if (
                rendered_returns
                and all(rendered is not None for rendered in rendered_returns)
                and all(
                    re.search(r"\bSELECT\b", rendered.upper()) is not None and _write_operation(rendered) is None
                    for rendered in rendered_returns
                    if rendered is not None
                )
            ):
                values[node.name] = "SELECT"
            continue
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if value is None:
            continue
        rendered = _sql_text(value, values)
        for target in targets:
            if isinstance(target, ast.Name):
                values.pop(target.id, None)
                if rendered is not None:
                    values[target.id] = rendered
    return values


def _imported_string_bindings(path: Path, source_root: Path) -> dict[str, str]:
    bindings = _constant_strings(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 1 or node.module is None:
            continue
        imported_path = path.parent / f"{node.module.replace('.', '/')}.py"
        if not imported_path.is_file() or source_root not in imported_path.parents:
            continue
        exported = _constant_strings(imported_path)
        for alias in node.names:
            if alias.name in exported:
                bindings[alias.asname or alias.name] = exported[alias.name]
    return bindings


def _sql_text(node: ast.expr, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Dict):
        choices = [_sql_text(value, bindings) for value in node.value.values]
        if choices and all(choice is not None and re.search(r"\bSELECT\b", choice.upper()) is not None and _write_operation(choice) is None for choice in choices):
            return "SELECT"
    if isinstance(node, ast.JoinedStr):
        return ast.unparse(node)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _sql_text(node.left, bindings)
        right = _sql_text(node.right, bindings)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join" and len(node.args) == 1:
        separator = _sql_text(node.func.value, bindings)
        values = node.args[0]
        if separator is None or not isinstance(values, (ast.List, ast.Tuple)):
            return None
        pieces = [_sql_text(item, bindings) for item in values.elts]
        return None if any(piece is None for piece in pieces) else separator.join(piece for piece in pieces if piece is not None)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return _sql_text(node.func.value, bindings)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return bindings.get(node.func.id)
    return None


def _write_operation(text: str | None) -> str | None:
    if text is None:
        return None
    upper = text.upper()
    match = re.search(r"\b(ALTER|CREATE|DELETE|DROP|INSERT|REPLACE|UPDATE)\b", upper)
    if match is not None:
        return match.group(1)
    return None


def _layout_operation(text: str | None) -> str | None:
    write = _write_operation(text)
    if write is not None:
        return write
    if text is None:
        return _UNRESOLVED_SQL
    words = {match.group(0) for match in re.finditer(r"\b[A-Z]+\b", text.upper())}
    return None if words & _KNOWN_NON_MUTATING_SQL else _UNRESOLVED_SQL


def _writer_owner(relpath: str) -> str:
    if "migrate" in relpath or "migration" in relpath or relpath.startswith("specify_cli/cli/"):
        return "WP10"
    if relpath in {
        "specify_cli/sync/consent.py",
        "specify_cli/sync/history_disclosure.py",
    }:
        return "WP03"
    if relpath.startswith("specify_cli/delivery/targets.py"):
        return "WP05"
    if relpath.startswith("specify_cli/sync/admission_operations.py"):
        return "WP05"
    if relpath.startswith("specify_cli/sync/transport_attempts.py"):
        return "WP06"
    if relpath.startswith("specify_cli/delivery/dispatcher.py"):
        return "WP07"
    return "WP04"


class _LayoutWriteVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_root: Path) -> None:
        self.path = path
        self.source_root = source_root
        self.module_bindings = _imported_string_bindings(path, source_root)
        self.bindings = self.module_bindings.copy()
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.sites: list[_LayoutWriteSite] = []
        self.function_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        saved = self.bindings
        self.bindings = self.module_bindings.copy() if self.function_depth == 0 else self.bindings.copy()
        self.functions.append(node.name)
        self.function_depth += 1
        for statement in node.body:
            self.visit(statement)
        self.function_depth -= 1
        self.functions.pop()
        self.bindings = saved

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        saved = self.bindings
        self.bindings = self.module_bindings.copy() if self.function_depth == 0 else self.bindings.copy()
        self.functions.append(node.name)
        self.function_depth += 1
        for statement in node.body:
            self.visit(statement)
        self.function_depth -= 1
        self.functions.pop()
        self.bindings = saved

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        # TODO(#3280): Track tuple/alternate SQL targets rather than only direct name assignments.
        value = _sql_text(node.value, self.bindings)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.bindings.pop(target.id, None)
                if value is not None:
                    self.bindings[target.id] = value
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        value = _sql_text(node.value, self.bindings) if node.value is not None else None
        if isinstance(node.target, ast.Name):
            self.bindings.pop(node.target.id, None)
            if value is not None:
                self.bindings[node.target.id] = value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # TODO(#3280): Merge conditional SQL binding states before execute-family calls; traversal is currently linear.
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"execute", "executemany", "executescript"} and node.args:
            rendered = _sql_text(node.args[0], self.bindings)
            operation = _layout_operation(rendered)
            if operation is not None:
                relpath = self.path.relative_to(self.source_root).as_posix()
                self.sites.append(
                    _LayoutWriteSite(
                        relpath,
                        ".".join((*self.classes, *self.functions)) or "<module>",
                        operation,
                        func.attr,
                        rendered or "",
                        _writer_owner(relpath),
                        node.lineno,
                    )
                )
        self.generic_visit(node)


_LAYOUT_ROOTS = (
    _SRC / "specify_cli" / "event_journal",
    _SRC / "specify_cli" / "delivery",
    _SRC / "specify_cli" / "sync",
    _SRC / "specify_cli" / "cli" / "commands" / "sync.py",
)


def _layout_paths(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in roots:
        paths.extend(root.rglob("*.py") if root.is_dir() else [root])
    return tuple(sorted(set(paths)))


def _scan_layout_writers(
    roots: tuple[Path, ...] | None = None,
    *,
    source_root: Path = _SRC,
) -> tuple[_LayoutWriteSite, ...]:
    if roots is None:
        roots = _LAYOUT_ROOTS if source_root == _SRC else (source_root,)
    sites: list[_LayoutWriteSite] = []
    for path in _layout_paths(roots):
        visitor = _LayoutWriteVisitor(path, source_root)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        sites.extend(visitor.sites)
    return tuple(sorted(sites))


_RETIRED_LAYOUT_BY_WP04_PREFIXES = (
    "specify_cli/delivery/ledger.py::",
    "specify_cli/delivery/retention.py::",
    "specify_cli/event_journal/coalesce.py::",
    "specify_cli/event_journal/journal.py::",
    "specify_cli/sync/body_queue.py::",
    "specify_cli/sync/queue.py::",
)


_KNOWN_LAYOUT_WRITE_COUNTS: Counter[str] = Counter(
    line.strip()
    for line in """
specify_cli/delivery/ledger.py::SqliteDeliveryLedger._record::INSERT::execute
specify_cli/delivery/ledger.py::init_ledger::CREATE::executescript
specify_cli/delivery/retention.py::_purge_all_body_rows::DELETE::execute
specify_cli/delivery/retention.py::_purge_journal_rows::DELETE::executemany
specify_cli/delivery/retention.py::_purge_ledger_rows::DELETE::execute
specify_cli/delivery/targets.py::ProjectDeliveryTargetRegistry.admit_locally::INSERT::execute
specify_cli/delivery/targets.py::ProjectDeliveryTargetRegistry.register::INSERT::execute
specify_cli/event_journal/coalesce.py::_collapse_into::UPDATE::execute
specify_cli/event_journal/coalesce.py::_connect::CREATE::execute
specify_cli/event_journal/coalesce.py::_record_supersede::INSERT::execute
specify_cli/event_journal/journal.py::EventJournal._ensure_schema::CREATE::execute
specify_cli/event_journal/journal.py::EventJournal._ensure_schema::CREATE::execute
specify_cli/event_journal/journal.py::EventJournal._ensure_schema::CREATE::execute
specify_cli/event_journal/journal.py::EventJournal._ensure_schema::CREATE::execute
specify_cli/event_journal/journal.py::EventJournal._migrate_add_identity_columns::ALTER::execute
specify_cli/event_journal/journal.py::EventJournal.append::INSERT::execute
specify_cli/event_journal/journal.py::EventJournal.mark_archived::UPDATE::execute
specify_cli/event_journal/journal.py::EventJournal.set_project_identity::UPDATE::executemany
specify_cli/event_journal/journal.py::JournalTransaction.append::INSERT::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.enqueue::INSERT::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_already_exists::DELETE::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_permanent::DELETE::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_retryable::UPDATE::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_uploaded::DELETE::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.record_permanent_failure::INSERT::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_project_tasks::DELETE::execute
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_stale::DELETE::execute
specify_cli/sync/consent.py::_seal_active_epochs::UPDATE::execute
specify_cli/sync/consent.py::_write_decision::INSERT::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._mark_sent::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._mark_unknown::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._mark_unknown::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._prepare::INSERT::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._record_response::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._record_response::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._record_response::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService._record_response::UPDATE::execute
specify_cli/sync/admission_operations.py::AdmissionOperationService.perform::UNRESOLVED::execute
specify_cli/sync/consent.py::_write_decision::INSERT::execute
specify_cli/sync/consent.py::allocate_capture_sequence::INSERT::execute
specify_cli/sync/consent.py::allocate_capture_sequence::INSERT::execute
specify_cli/sync/history_disclosure.py::confirm_history_disclosure::INSERT::execute
specify_cli/sync/migrate_journal.py::MigrationAudit.__init__::CREATE::executescript
specify_cli/sync/migrate_journal.py::MigrationAudit.clear_conflict::DELETE::execute
specify_cli/sync/migrate_journal.py::MigrationAudit.quarantine_conflict::INSERT::execute
specify_cli/sync/migrate_journal.py::MigrationAudit.record_conflict::INSERT::execute
specify_cli/sync/migrate_journal.py::MigrationAudit.record_provenance::INSERT::execute
specify_cli/sync/queue.py::OfflineQueue._init_db::CREATE::execute
specify_cli/sync/queue.py::OfflineQueue._init_db::CREATE::execute
specify_cli/sync/queue.py::OfflineQueue._init_db::CREATE::execute
specify_cli/sync/queue.py::OfflineQueue._init_db::CREATE::execute
specify_cli/sync/queue.py::OfflineQueue._migrate_add_coalesce_key::ALTER::execute
specify_cli/sync/queue.py::OfflineQueue._try_coalesce::UPDATE::execute
specify_cli/sync/queue.py::OfflineQueue.append::INSERT::execute
specify_cli/sync/queue.py::OfflineQueue.append::UPDATE::execute
specify_cli/sync/queue.py::OfflineQueue.clear::DELETE::execute
specify_cli/sync/queue.py::OfflineQueue.increment_retry::UPDATE::execute
specify_cli/sync/queue.py::OfflineQueue.mark_synced::DELETE::execute
specify_cli/sync/queue.py::OfflineQueue.process_batch_results::DELETE::execute
specify_cli/sync/queue.py::OfflineQueue.process_batch_results::UPDATE::execute
specify_cli/sync/queue.py::OfflineQueue.queue_event::DELETE::execute
specify_cli/sync/queue.py::OfflineQueue.queue_event::INSERT::execute
specify_cli/sync/queue.py::OfflineQueue.queue_event::UPDATE::execute
specify_cli/sync/queue.py::OfflineQueue.remove_events::DELETE::execute
specify_cli/sync/queue.py::_migrate_body_queue_column_rename::ALTER::execute
specify_cli/sync/queue.py::_migrate_body_queue_column_rename::ALTER::execute
specify_cli/sync/queue.py::_migrate_one_table::DELETE::execute
specify_cli/sync/queue.py::_migrate_one_table::INSERT::execute
specify_cli/sync/queue.py::_scoped_dst_schema::CREATE::execute
specify_cli/sync/queue.py::_scoped_dst_schema::CREATE::execute
specify_cli/sync/queue.py::_scoped_dst_schema::CREATE::execute
specify_cli/sync/queue.py::_scoped_dst_schema::CREATE::execute
specify_cli/sync/queue.py::ensure_body_queue_schema::CREATE::executescript
""".splitlines()
    if line.strip() and not line.strip().startswith(_RETIRED_LAYOUT_BY_WP04_PREFIXES)
)

_KNOWN_LAYOUT_WRITE_COUNTS.update(
    {
        "specify_cli/delivery/ledger.py::SqliteDeliveryLedger._record.write::INSERT::execute": 3,
        "specify_cli/delivery/retention.py::purge_project_payloads.write::DELETE::execute": 1,
        "specify_cli/event_journal/journal.py::EventJournal.append.write::INSERT::execute": 1,
        "specify_cli/event_journal/journal.py::EventJournal.mark_archived.write::UPDATE::execute": 1,
        "specify_cli/event_journal/journal.py::EventJournal.purge_events.write::DELETE::execute": 4,
        "specify_cli/event_journal/journal.py::EventJournal.purge_events.write::UPDATE::execute": 1,
        "specify_cli/event_journal/journal.py::EventJournal.record_supersede.write::INSERT::execute": 1,
        "specify_cli/event_journal/journal.py::EventJournal.replace_undelivered_payload.write::UPDATE::execute": 1,
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue._update.write::UPDATE::execute": 1,
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.enqueue.write::INSERT::execute": 1,
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_project_tasks.write::DELETE::execute": 1,
        "specify_cli/sync/queue.py::OfflineQueue._update_tasks.write::UPDATE::execute": 1,
        "specify_cli/sync/queue.py::OfflineQueue.queue_event.write::INSERT::execute": 1,
        "specify_cli/sync/history_disclosure.py::stage_sealed_history_cohort::INSERT::execute": 2,
        "specify_cli/sync/history_disclosure.py::stage_sealed_history_cohort::INSERT::executemany": 1,
        "specify_cli/sync/transport_attempts.py::_persist_logical_terminal_reference::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::_record_delivery_result::INSERT::execute": 1,
        "specify_cli/sync/transport_attempts.py::_record_delivery_result::UPDATE::execute": 2,
        "specify_cli/sync/transport_attempts.py::_settle_open_unit::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::_terminalize_orphaned_attempt::INSERT::execute": 1,
        "specify_cli/sync/transport_attempts.py::_terminalize_orphaned_attempt::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::attach_remote_operation_id::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::execute_remote_operation_query_under_lease::UPDATE::execute": 2,
        "specify_cli/sync/transport_attempts.py::mark_delivery_result_unknown::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::mark_transport_started::UPDATE::execute": 1,
        "specify_cli/sync/transport_attempts.py::prepare_delivery_attempt::INSERT::execute": 1,
        "specify_cli/sync/transport_attempts.py::restart_delivery_attempt::UPDATE::execute": 1,
    }
)

_WP10_MIGRATION_WRITE_COUNTS: Counter[str] = Counter(
    {
        "specify_cli/sync/project_store_migration.py::_copy_project_rows::INSERT::execute": 9,
    }
)

_CANONICAL_PROJECT_STORE_LAYOUT_COUNTS: Counter[str] = Counter(
    {
        "specify_cli/sync/project_store.py::ProjectSyncStore.unit_of_work::INSERT::execute": 1,
        "specify_cli/sync/project_store.py::ProjectSyncStore.unit_of_work::UNRESOLVED::execute": 1,
    }
)


def _is_canonical_project_store_layout_write(site: _LayoutWriteSite) -> bool:
    return site.relpath == "specify_cli/sync/project_store.py" and site.qualname == "ProjectSyncStore.unit_of_work"


def _qualified_functions(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.classes: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            self.classes.append(node.name)
            self.generic_visit(node)
            self.classes.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            found.add(".".join((*self.classes, node.name)))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(  # noqa: N802
            self, node: ast.AsyncFunctionDef
        ) -> None:
            found.add(".".join((*self.classes, node.name)))
            self.generic_visit(node)

    Visitor().visit(tree)
    return frozenset(found)


def _qualified_function_node(
    path: Path,
    qualname: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: ast.FunctionDef | ast.AsyncFunctionDef | None = None

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.classes: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            self.classes.append(node.name)
            self.generic_visit(node)
            self.classes.pop()

        def _visit(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            nonlocal found
            if ".".join((*self.classes, node.name)) == qualname:
                found = node
                return
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            self._visit(node)

        def visit_AsyncFunctionDef(  # noqa: N802
            self, node: ast.AsyncFunctionDef
        ) -> None:
            self._visit(node)

    Visitor().visit(tree)
    return found


_DURABLE_RESULT_AUTHORITIES: dict[_SymbolRef, tuple[str, str]] = {
    _SymbolRef(
        "specify_cli/delivery/ledger.py",
        "SqliteDeliveryLedger._record",
    ): ("delivery_results", "attempt_id"),
    _SymbolRef(
        "specify_cli/sync/body_queue.py",
        "OfflineBodyUploadQueue._update",
    ): ("body_upload_tasks", "row_id"),
    _SymbolRef(
        "specify_cli/sync/queue.py",
        "OfflineQueue.queue_event",
    ): ("outbox_tasks", "event_id"),
    _SymbolRef(
        "specify_cli/sync/transport_attempts.py",
        "_record_delivery_result",
    ): ("delivery_results", "attempt_id"),
}


def _reads_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(item, ast.Name) and item.id == name for item in ast.walk(node))


def _durable_result_write(
    row: _ProjectSyncSender,
    path: Path,
    source_root: Path,
) -> bool:
    # TODO(#3280): Prove identity-to-column value flow; table, operation, and bound-argument evidence is intentionally narrower.
    if row.result_write is None:
        return False
    requirement = _DURABLE_RESULT_AUTHORITIES.get(row.result_write)
    node = _qualified_function_node(path, row.result_write.qualname)
    if requirement is None or node is None:
        return False
    table, identity = requirement
    dml = {"DELETE", "INSERT", "REPLACE", "UPDATE"}
    authority_lines = {
        site.lineno
        for site in _scan_layout_writers((path,), source_root=source_root)
        if (site.qualname == row.result_write.qualname or site.qualname.startswith(f"{row.result_write.qualname}."))
        and site.operation in dml
        and table in site.statement.lower()
    }
    return any(
        isinstance(item, ast.Call)
        and item.lineno in authority_lines
        and isinstance(item.func, ast.Attribute)
        and item.func.attr in {"execute", "executemany", "executescript"}
        and any(
            _reads_name(argument, identity)
            for argument in (
                *item.args[1:],
                *(keyword.value for keyword in item.keywords),
            )
        )
        for item in ast.walk(node)
    )


def _durable_file_result_write(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    # TODO(#3280): Prove mutation-before-save ordering across paths; this predicate only relates the named field, identity, and save.
    records_ack_identity = any(
        isinstance(item, (ast.Assign, ast.AnnAssign))
        and item.value is not None
        and any(
            isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "state" and target.attr == "last_saas_confirmed_hash"
            for target in (item.targets if isinstance(item, ast.Assign) else [item.target])
        )
        and _reads_name(item.value, "git_hash")
        for item in ast.walk(node)
    )
    saves_state = any(
        isinstance(item, ast.Call)
        and _attr_tail(item.func) == "save_sync_state"
        and any(isinstance(argument, ast.Name) and argument.id == "state" for argument in item.args)
        for item in ast.walk(node)
    )
    return records_ack_identity and saves_state


def _in_memory_result_write(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    # TODO(#3280): Add reachability/path proof for result-guarded report mutations; syntactic guards may be unreachable.
    result_fields = frozenset({"outcome", "event_id", "error"})
    report_fields = frozenset({"success", "duplicate", "pending", "rejected", "rejected_samples"})

    def reads_result_member(item: ast.AST, fields: frozenset[str]) -> bool:
        return any(
            isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id == "result" and child.attr in fields
            for child in ast.walk(item)
        )

    def records_documented_member(item: ast.AST) -> bool:
        if (
            isinstance(item, ast.AugAssign)
            and isinstance(item.target, ast.Attribute)
            and isinstance(item.target.value, ast.Name)
            and item.target.value.id == "report"
            and item.target.attr in report_fields
        ):
            return True
        return (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "append"
            and isinstance(item.func.value, ast.Attribute)
            and isinstance(item.func.value.value, ast.Name)
            and item.func.value.value.id == "report"
            and item.func.value.attr in report_fields
            and any(reads_result_member(argument, result_fields) for argument in item.args)
        )

    def guarded_record(statements: list[ast.stmt], outcome_guard: bool = False) -> bool:
        for statement in statements:
            if isinstance(statement, ast.If):
                guarded = outcome_guard or reads_result_member(
                    statement.test,
                    frozenset({"outcome"}),
                )
                if guarded_record(statement.body, guarded) or guarded_record(
                    statement.orelse,
                    guarded,
                ):
                    return True
            elif outcome_guard and any(records_documented_member(item) for item in ast.walk(statement)):
                return True
        return False

    return guarded_record(node.body)


def _has_semantic_result_write(
    row: _ProjectSyncSender,
    *,
    source_root: Path = _SRC,
) -> bool:
    """Prove the named result site mutates durable or explicit result state."""
    if row.result_write is None:
        return row.result_state is _ResultState.MISSING
    path = source_root / row.result_write.relpath
    if row.result_state in {_ResultState.DURABLE, _ResultState.DURABLE_FALLBACK}:
        return _durable_result_write(row, path, source_root)
    node = _qualified_function_node(path, row.result_write.qualname)
    if node is None:
        return False
    if row.result_state is _ResultState.DURABLE_FILE:
        return _durable_file_result_write(node)
    if row.result_state is _ResultState.IN_MEMORY:
        return _in_memory_result_write(node)
    return False


def test_project_sync_sender_matrix_maps_actual_request_and_result_sites() -> None:
    assert {row.surface for row in _PROJECT_SYNC_SENDER_MATRIX} == _SENDER_CONTRACT
    assert {row.final_owner for row in _PROJECT_SYNC_SENDER_MATRIX} == {"WP07", "WP08"}
    sink_symbols = {_SymbolRef(site.relpath, site.qualname) for site in _scan_project_sinks()}
    for row in _PROJECT_SYNC_SENDER_MATRIX:
        assert row.request_start in sink_symbols, f"request start is not a discovered sink: {row.request_start}"
        if row.result_write is None:
            assert row.result_state is _ResultState.MISSING
        else:
            assert row.result_write.qualname in _qualified_functions(_SRC / row.result_write.relpath)
            assert row.result_state is not _ResultState.MISSING
            assert _has_semantic_result_write(row), f"named result site does not perform a {row.result_state.value}: {row.result_write}"
        if row.surface == "tracker hosted channel":
            assert row.channel_2_narrowing_only
        else:
            assert not row.channel_2_narrowing_only


def test_wp09_producer_discovery_and_control_rows_delegate_by_symbol() -> None:
    assert len({row.surface for row in _WP09_INTEGRATION_ROWS}) == len(_WP09_INTEGRATION_ROWS)
    for row in _WP09_INTEGRATION_ROWS:
        node = _qualified_function_node(_SRC / row.symbol.relpath, row.symbol.qualname)
        assert node is not None, f"missing live WP09 integration row: {row}"
        delegates = {_attr_tail(call.func) for call in ast.walk(node) if isinstance(call, ast.Call)}
        if row.required_delegate is None:
            assert row.classification == "local_only"
            assert not delegates, f"local-only row acquired a live call: {row}"
        else:
            assert row.classification == "hosted_sender"
            assert row.required_delegate in delegates, (
                f"{row.surface} no longer delegates through {row.required_delegate}: {sorted(value for value in delegates if value is not None)}"
            )
        assert row.final_owner in {"WP07", "WP08"}


def test_source_discovered_sender_census_is_counted_and_shrink_only() -> None:
    sites = _scan_project_sinks()
    loopback = Counter(site.key for site in sites if site.key in _WP10_LOOPBACK_CONTROL_SINK_COUNTS)
    assert loopback == _WP10_LOOPBACK_CONTROL_SINK_COUNTS
    assert _EGRESS_ALLOWLIST["specify_cli/sync/daemon_protocol.py"].kind is AllowanceKind.LOOPBACK_CONTROL
    observed = Counter(site.key for site in sites if site.key not in _WP10_LOOPBACK_CONTROL_SINK_COUNTS)
    growth = observed - _KNOWN_PROJECT_SINK_COUNTS
    assert not growth, "new project sender sites:\n" + "\n".join(f"{key} (+{count})" for key, count in sorted(growth.items()))
    shrink = _KNOWN_PROJECT_SINK_COUNTS - observed
    if shrink:
        warnings.warn(
            "project sender census shrank: " + ", ".join(f"{key} (-{count})" for key, count in sorted(shrink.items())),
            stacklevel=1,
        )


def test_wp09_sender_census_is_exact_per_symbol_not_per_file() -> None:
    observed = Counter(site.key for site in _scan_project_sinks() if site.key not in _WP10_LOOPBACK_CONTROL_SINK_COUNTS)
    assert observed == _KNOWN_PROJECT_SINK_COUNTS


def test_wp09_every_discovered_sink_symbol_is_classified_into_the_matrix() -> None:
    observed = {_SymbolRef(site.relpath, site.qualname) for site in _scan_project_sinks()}
    classified = {row.symbol for row in _WP09_SINK_CLASSIFICATIONS}
    assert observed == classified
    covered = frozenset(family for row in _WP09_SINK_CLASSIFICATIONS for family in row.matrix_families)
    assert covered == _WP09_MATRIX_FAMILIES
    assert all(row.rationale.strip() for row in _WP09_SINK_CLASSIFICATIONS)
    assert all(row.rationale != "project-bearing transport" for row in _WP09_SINK_CLASSIFICATIONS if not row.matrix_families)


_T034_DURABLE_ADAPTER_SINK_COUNTS: Counter[str] = Counter(
    {
        "specify_cli/saas_client/client.py::SaasClient._send_generic_operation::http-verb::self._http.post": 1,
        "specify_cli/tracker/saas_client.py::SaaSTrackerClient._physical_request_with_retry::transport-call::self._request": 3,
        "specify_cli/tracker/saas_client.py::SaaSTrackerClient._request_with_retry::transport-call::self._physical_request_with_retry": 1,
    }
)


def _t034_durable_adapter_sink_counts(
    sites: tuple[_ProjectSinkSite, ...],
) -> Counter[str]:
    return Counter(site.key for site in sites if site.key in _T034_DURABLE_ADAPTER_SINK_COUNTS)


def test_t034_durable_adapter_sender_census_is_exact() -> None:
    assert _t034_durable_adapter_sink_counts(_scan_project_sinks()) == _T034_DURABLE_ADAPTER_SINK_COUNTS


def test_t034_durable_adapter_sender_census_rejects_extra_retry_mutant(
    tmp_path: Path,
) -> None:
    tracker = tmp_path / "specify_cli" / "tracker" / "saas_client.py"
    tracker.parent.mkdir(parents=True)
    tracker.write_text(
        "class SaaSTrackerClient:\n"
        "    def _physical_request_with_retry(self, payload):\n"
        "        self._request('POST', '/one', json=payload, headers={})\n"
        "        self._request('POST', '/two', json=payload, headers={})\n"
        "        self._request('POST', '/three', json=payload, headers={})\n"
        "        self._request('POST', '/mutant', json=payload, headers={})\n",
        encoding="utf-8",
    )

    observed = _t034_durable_adapter_sink_counts(_scan_project_sinks((tracker,), source_root=tmp_path))

    assert observed - _T034_DURABLE_ADAPTER_SINK_COUNTS == Counter(
        {"specify_cli/tracker/saas_client.py::SaaSTrackerClient._physical_request_with_retry::transport-call::self._request": 1}
    )


def test_source_discovered_layout_writer_census_is_counted_and_shrink_only() -> None:
    sites = _scan_layout_writers()
    canonical = Counter(site.key for site in sites if _is_canonical_project_store_layout_write(site))
    assert canonical == _CANONICAL_PROJECT_STORE_LAYOUT_COUNTS, "the exact ProjectSyncStore unit of work is the sole new schema/layout writer"
    migration = Counter(site.key for site in sites if site.key in _WP10_MIGRATION_WRITE_COUNTS)
    assert migration == _WP10_MIGRATION_WRITE_COUNTS
    assert all(site.owner_wp == "WP10" for site in sites if site.key in _WP10_MIGRATION_WRITE_COUNTS)
    observed = Counter(site.key for site in sites if not _is_canonical_project_store_layout_write(site) and site.key not in _WP10_MIGRATION_WRITE_COUNTS)
    growth = observed - _KNOWN_LAYOUT_WRITE_COUNTS
    assert not growth, "new current layout writers:\n" + "\n".join(f"{key} (+{count})" for key, count in sorted(growth.items()))
    assert all(site.owner_wp.startswith("WP") for site in sites)
    shrink = _KNOWN_LAYOUT_WRITE_COUNTS - observed
    if shrink:
        warnings.warn(
            "layout-writer census shrank: " + ", ".join(f"{key} (-{count})" for key, count in sorted(shrink.items())),
            stacklevel=1,
        )


_WP04_PERMIT_WRITERS = {
    _SymbolRef("specify_cli/delivery/ledger.py", "SqliteDeliveryLedger._record"),
    _SymbolRef("specify_cli/delivery/retention.py", "purge_project_payloads"),
    _SymbolRef("specify_cli/event_journal/journal.py", "EventJournal.append"),
    _SymbolRef("specify_cli/event_journal/journal.py", "EventJournal.mark_archived"),
    _SymbolRef("specify_cli/event_journal/journal.py", "EventJournal.purge_events"),
    _SymbolRef("specify_cli/event_journal/journal.py", "EventJournal.record_supersede"),
    _SymbolRef(
        "specify_cli/event_journal/journal.py",
        "EventJournal.replace_undelivered_payload",
    ),
    _SymbolRef("specify_cli/sync/body_queue.py", "OfflineBodyUploadQueue._update"),
    _SymbolRef("specify_cli/sync/body_queue.py", "OfflineBodyUploadQueue.enqueue"),
    _SymbolRef(
        "specify_cli/sync/body_queue.py",
        "OfflineBodyUploadQueue.remove_project_tasks",
    ),
    _SymbolRef("specify_cli/sync/queue.py", "OfflineQueue._update_tasks"),
    _SymbolRef("specify_cli/sync/queue.py", "OfflineQueue.queue_event"),
}


def _uses_layout_write_permit(path: Path, qualname: str) -> bool:
    node = _qualified_function_node(path, qualname)
    if node is None:
        return False
    calls = [item for item in ast.walk(node) if isinstance(item, ast.Call)]
    has_issue = any(_attr_tail(call.func) == "issue_write_permit" for call in calls)
    has_execute = any(_attr_tail(call.func) == "execute_write" for call in calls)
    has_destination_check = any(isinstance(call.func, ast.Name) and call.func.id == "_require_project_destination" for call in calls)
    return has_issue and has_execute and has_destination_check


def test_every_wp04_current_writer_participates_in_layout_permits() -> None:
    sites = _scan_layout_writers()
    discovered = {
        _SymbolRef(site.relpath, site.qualname.removesuffix(".write"))
        for site in sites
        if site.owner_wp == "WP04" and not _is_canonical_project_store_layout_write(site)
    }
    assert discovered == _WP04_PERMIT_WRITERS
    assert all(_uses_layout_write_permit(_SRC / writer.relpath, writer.qualname) for writer in _WP04_PERMIT_WRITERS)


def test_layout_permit_guard_rejects_a_writer_bypass_mutant(tmp_path: Path) -> None:
    source = tmp_path / "specify_cli" / "sync" / "queue.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "class OfflineQueue:\n    def queue_event(self, unit, payload):\n        unit.execute('INSERT INTO outbox_tasks VALUES (?)', (payload,))\n",
        encoding="utf-8",
    )
    sites = _scan_layout_writers((source,), source_root=tmp_path)
    assert [site.operation for site in sites] == ["INSERT"]
    assert not _uses_layout_write_permit(source, "OfflineQueue.queue_event")


def test_wp10_migration_owner_classification_is_narrow() -> None:
    assert _writer_owner("specify_cli/sync/project_store_migration.py") == "WP10"
    assert _writer_owner("specify_cli/sync/project_store.py") == "WP04"


def test_new_sender_and_layout_writer_mutants_flow_through_real_collectors(
    tmp_path: Path,
) -> None:
    sync_root = tmp_path / "specify_cli" / "sync"
    source = sync_root / "previously_unseen_sender.py"
    alias_source = sync_root / "aliased_transport.py"
    dynamic_writer = sync_root / "dynamic_writer.py"
    clean = sync_root / "wrapped_sender.py"
    sync_root.mkdir(parents=True)
    source.write_text(
        "def bypass(client, payload):\n"
        "    context = ProjectSyncContext(payload['project_uuid'])\n"
        "    attempt = DeliveryAttempt(context, payload)\n"
        "    final_transport_eligible(attempt)\n"
        "    wire = client.post\n"
        "    wire('/events', json=payload)\n"
        "    wire = safe\n"
        "    wire(payload)\n"
        "def exact_reviewer_bypass(client, payload):\n"
        "    ProjectSyncContext(payload['project_uuid'])\n"
        "    DeliveryAttempt(payload)\n"
        "    final_transport_eligible(payload)\n"
        "    client.post('/events', json=payload)\n"
        "def audit_header_decoy(client, payload, foreign_payload):\n"
        "    context = ProjectSyncContext(payload['project_uuid'])\n"
        "    attempt = DeliveryAttempt(context, payload)\n"
        "    if final_transport_eligible(attempt):\n"
        "        client.post('/events', json=foreign_payload, headers={'X-Audit': str(attempt)})\n"
        "def rebound_project(client, payload, a, b):\n"
        "    project = a.uuid\n"
        "    context = ProjectSyncContext(project)\n"
        "    project = b.uuid\n"
        "    attempt = DeliveryAttempt(context, payload)\n"
        "    if final_transport_eligible(attempt):\n"
        "        client.post('/events', json=attempt)\n",
        encoding="utf-8",
    )
    alias_source.write_text(
        "import httpx as wire\ndef send(payload):\n    wire.post('/events', json=payload)\n",
        encoding="utf-8",
    )
    dynamic_writer.write_text(
        "def write(conn, payload):\n"
        "    sql = ''.join(('INS', 'ERT INTO event_outbox VALUES (?)'))\n"
        "    conn.execute(sql, (payload,))\n"
        "    select_sql = ''.join(('SEL', 'ECT * FROM event_outbox'))\n"
        "    conn.execute(select_sql)\n",
        encoding="utf-8",
    )
    clean.write_text(
        "def send(client, payload):\n"
        "    context = ProjectSyncContext(payload['project_uuid'])\n"
        "    attempt = DeliveryAttempt(context, payload)\n"
        "    if final_transport_eligible(attempt):\n"
        "        client.post('/events', json=attempt)\n",
        encoding="utf-8",
    )
    sink_sites = _scan_project_sinks(source_root=tmp_path)
    violations = _new_sender_violations(sink_sites, Counter())
    assert {site.relpath for site in violations} == {
        "specify_cli/sync/aliased_transport.py",
        "specify_cli/sync/previously_unseen_sender.py",
    }
    assert all(not site.canonical_attempt for site in sink_sites if site.relpath == "specify_cli/sync/previously_unseen_sender.py")
    assert all(site.canonical_attempt for site in sink_sites if site.relpath == "specify_cli/sync/wrapped_sender.py")
    writer_sites = _scan_layout_writers(source_root=tmp_path)
    assert [site.operation for site in writer_sites] == ["INSERT"]


def test_sender_aliases_resolve_transitively(tmp_path: Path) -> None:
    source = tmp_path / "specify_cli" / "sync" / "alias_chain.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def alias_chain(client, payload):\n    wire = client.post\n    send = wire\n    send('/events', json=payload)\n",
        encoding="utf-8",
    )
    sites = _scan_project_sinks(source_root=tmp_path)
    assert [(site.qualname, site.callee) for site in sites] == [("alias_chain", "client.post")]


def test_layout_census_surfaces_unresolved_sql_without_stale_bindings(
    tmp_path: Path,
) -> None:
    source = tmp_path / "specify_cli" / "sync" / "unresolved_writer.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def unresolved_write(conn, payload, operation):\n"
        "    sql = f'{operation} INTO event_outbox VALUES (?)'\n"
        "    conn.execute(sql, (payload,))\n"
        "def stale_insert(conn, payload):\n"
        "    sql = 'INSERT INTO event_outbox VALUES (?)'\n"
        "    sql = build_query()\n"
        "    conn.execute(sql, (payload,))\n",
        encoding="utf-8",
    )
    sites = _scan_layout_writers(source_root=tmp_path)
    assert [(site.qualname, site.operation) for site in sites] == [
        ("stale_insert", "UNRESOLVED"),
        ("unresolved_write", "UNRESOLVED"),
    ]


def test_result_matrix_rejects_a_named_function_without_a_result_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_root = tmp_path / "specify_cli" / "sync"
    sync_root.mkdir(parents=True)
    specimens = {
        "durable.py": ("def record(conn, event_id):\n    audit(event_id)\n    conn.execute('INSERT INTO delivery_ledger(other) VALUES (?)', ('constant',))\n"),
        "memory.py": ("def record(report, result):\n    audit(result)\n    report.debug.append('unrelated')\n"),
        "file.py": ("def record(state, git_hash):\n    audit(git_hash)\n    state.unrelated = True\n    save_sync_state(state)\n"),
    }
    states = {
        "durable.py": _ResultState.DURABLE,
        "memory.py": _ResultState.IN_MEMORY,
        "file.py": _ResultState.DURABLE_FILE,
    }
    for filename, source in specimens.items():
        path = sync_root / filename
        path.write_text(source, encoding="utf-8")
        symbol = _SymbolRef(f"specify_cli/sync/{filename}", "record")
        if filename == "durable.py":
            monkeypatch.setitem(
                _DURABLE_RESULT_AUTHORITIES,
                symbol,
                ("delivery_ledger", "event_id"),
            )
        row = _ProjectSyncSender(
            filename,
            symbol,
            symbol,
            states[filename],
            "WP04",
        )
        assert not _has_semantic_result_write(row, source_root=tmp_path)
