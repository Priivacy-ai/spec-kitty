"""FR-018 / T034 -- the non-terminating-loop plugin mutant for WP11's counter pin.

Load with (the ``-p`` flag is what actually loads it; ``PYTHONPATH`` alone loads
nothing -- C-003's corrected contract):

    PYTHONPATH=scripts/mutants:$WT/src .venv/bin/python -m pytest \\
        -p nonterminating_dispatch_3115 \\
        tests/delivery/test_dispatch_window_consent_3030.py

Contract this module obeys in full (spec.md C-003, corrected by the post-plan
squad; mirrored in ``kitty-specs/.../standing-rules.md``):

1. **Loading**: importable via ``PYTHONPATH=scripts/mutants`` AND loaded with
   ``-p nonterminating_dispatch_3115``. A ``PYTHONPATH``-only mutant is imported
   by nothing and binds nothing -- it is the exact rot mode this mission exists
   to guard against.
2. **Neutralisation site**: hook level, ``pytest_configure`` -- never a
   same-named fixture. A same-named autouse fixture defined in a ``-p``-loaded
   plugin LOSES to the conftest fixture for items collected under that
   conftest's directory (measured on this mission); this module patches the
   production module attribute directly instead of shadowing anything.
3. **Self-proof**: asserts its own binding, reports the per-site split across
   every production (``src/``) name the patched symbol is reachable by, and
   fails loudly if the symbol it patched was never called during the session
   -- loud via a bold/red terminal line and a forced non-zero exit status
   (``pytest_terminal_summary`` + ``pytest_sessionfinish``), not via a raise:
   raising from either hook was measured to pre-empt
   ``TerminalReporter.summary_stats()`` and destroy the final count line,
   which would defeat NFR-003's "the count line is the evidence" rule for
   exactly the run meant to prove there is no evidence. A zero-suppressed-count
   run is a finding about the mutant, not about the code, and draws no
   verdict.
4. **Reporting**: prints a binding report at configure time and a
   suppression/per-site report at session end, so both can be quoted beside a
   run's count line and collected count.

What it patches, and why it is the only PRODUCTION site
----------------------------------------------------------
``_run_dispatch_batches`` (``src/specify_cli/cli/commands/sync.py:818``) does::

    from specify_cli.delivery.dispatcher import DispatchSummary, dispatch

INSIDE its own function body, so ``dispatch`` is re-resolved off the
``specify_cli.delivery.dispatcher`` module on every CALL to
``_run_dispatch_batches`` -- this is the same fact
``test_nfr002_loop_permanence_3030.py``'s ``counted_dispatch`` fixture already
relies on ("patching it here reaches the live loop"). (Verified with ``dis``:
a function-local ``from X import f`` compiles to one ``IMPORT_FROM`` +
``STORE_FAST`` at function entry, so the name is resolved once per call, not
once per loop iteration -- the patch still reaches the live loop either way,
since patching happens before the call, but the earlier "fresh on every loop
iteration" phrasing in this docstring was wrong and is corrected here.)

Grepping ``src/`` for every other importer of the symbol turns up only
importers of ``DispatchSummary`` alone (``sync.py:28``, ``:749``, ``:1110``,
``:1113``) -- nothing else in production code imports or rebinds ``dispatch``
itself at module scope, and ``specify_cli/delivery/__init__.py`` does not
re-export it. So there is exactly ONE **production** site the symbol is
reachable by (unlike the mission's recorded "owner=20, preflight=14" split for
a ``from X import f`` rebind-by-value case): this module reports that as a
one-site split rather than inventing a second production site that does not
exist.

This mutant does NOT patch, and does not need to patch, seven **test-side**
``from specify_cli.delivery.dispatcher import dispatch`` rebinds that exist at
module scope for other reasons: ``test_envelope.py:27``,
``test_cross_project_refusal_state_3030.py:26``,
``test_dispatch_project_consent_3030.py:108``,
``test_dispatch_honours_drain_blocked_3031.py:87``,
``test_incident_reproduction_3030.py:59``,
``test_nfr003_predicate_cost_3030.py:41``,
``test_liveness_predicate_before_limit_3030.py:45``. Those are exactly the
"``from X import f`` rebinds by value" shape the mission's fifth rot mode
warns about, but they are irrelevant to THIS mutant's acceptance: this WP's
two tests call ``sync_module._run_dispatch_batches`` directly (never
``dispatch`` by name), and module collection for all seven happens after
``pytest_configure`` has already run, so none of the seven capture a stale
pre-patch reference. They are named here as known-and-out-of-scope, not as
zero -- the mission's own precedent for this is FR-009's handling of its two
deliberately-unpatched eager binds, reported by name rather than folded into
a misleading total.

What the replacement does, and why it is non-terminating
----------------------------------------------------------
``_run_dispatch_batches``'s loop only stops when::

    if batch.selected == 0 or not advanced:
        break

where ``advanced = terminal_progress or len(skip) > before`` and
``terminal_progress = (delivered + duplicate + terminal_failed) > 0``. The
replacement always reports ``selected=1, delivered=1`` -- a claim of real,
successful progress on EVERY call -- while never touching the real journal,
ledger or receiver at all. That defeats both halves of the break condition
forever: ``selected`` is never 0, and ``terminal_progress`` is always true, so
``advanced`` is always true. The loop spins without end: a claimed success
that never corresponds to the real journal actually draining, which is the
"fails to make progress" shape T034 requires, and the shape measured on
``#3030`` -- 1,603 retried empty selections, no assertion to catch them, the
session killed with no verdict.
"""

from __future__ import annotations

from typing import Any

import pytest

_SYMBOL = "dispatch"
_SITE = "specify_cli.delivery.dispatcher.dispatch"

_state: dict[str, Any] = {"bound": False, "calls": 0}

# Key under which a worker ships its local counters to the controller. See
# `pytest_sessionfinish` / `pytest_testnodedown` below.
_WORKEROUTPUT_KEY = "nonterminating_dispatch_3115"


def _non_progressing_dispatch(**kwargs: Any) -> Any:
    """Stand-in for the real ``dispatch``: always selected, always "delivered",
    never real. Bypasses the journal/ledger/receiver entirely on purpose --
    the defect under test is that nothing downstream can tell the difference."""
    from specify_cli.delivery.dispatcher import DispatchSummary

    _state["calls"] += 1
    target = kwargs.get("target")
    target_id = getattr(target, "target_id", None) if target is not None else None
    return DispatchSummary(
        target_id=target_id,
        selected=1,
        delivered=1,
        duplicate=0,
        pending=0,
        rejected=0,
        transient=0,
        terminal_failed=0,
        failures=(),
        retryable_event_ids=(),
    )


def pytest_configure(config: Any) -> None:  # noqa: ARG001 -- pytest hook signature
    """Bind at hook level (C-003 (2)) and assert the binding took (C-003 (3)).

    The pre-assignment existence check is load-bearing, and its absence was a
    real defect in this file. ``dispatcher_module.dispatch = ...`` CREATES the
    attribute when it does not already exist, so the post-assignment
    ``is _non_progressing_dispatch`` identity check that used to stand alone
    here was a tautology: it could never fail, because assignment always
    succeeds. If ``dispatch`` were renamed or relocated -- C-003's rot mode 1,
    "the architecture moved", the first one listed -- this plugin would have
    happily invented the attribute on the module, reported ``BOUND``, then
    suppressed zero calls and misreported that architectural rot as the
    unrelated "wrong node-ids selected". Both siblings
    (``neutralise_reset_token_manager_3115``, ``attribute_sleep_count_3115``)
    already check for absent/non-callable BEFORE assigning; this one now
    matches them.
    """
    from specify_cli.delivery import dispatcher as dispatcher_module

    original = getattr(dispatcher_module, _SYMBOL, None)
    if original is None or not callable(original):
        raise pytest.UsageError(
            f"nonterminating_dispatch_3115: {_SITE} is absent, renamed, "
            "relocated, or not callable -- there was no existing `dispatch` to "
            "replace. This mutant's binding assertion failed at "
            "pytest_configure; nothing was neutralised, and no verdict about "
            "the counter pin may be drawn from this run (C-003 self-proof "
            "requirement, rot mode 1: the architecture moved)."
        )

    _state["original"] = original
    dispatcher_module.dispatch = _non_progressing_dispatch
    _state["bound"] = dispatcher_module.dispatch is _non_progressing_dispatch
    if not _state["bound"]:  # pragma: no cover - defensive, loud by design
        raise pytest.UsageError(
            f"nonterminating_dispatch_3115: FAILED TO BIND at {_SITE} -- "
            "attribute assignment did not stick. This is a finding "
            "about the mutant, not about the code under test; no verdict may "
            "be drawn from this run (C-003 self-proof requirement)."
        )
    print(
        f"\n[nonterminating_dispatch_3115] BOUND at {_SITE} "
        "(1 production site total -- the only src/ name `dispatch` is "
        "reachable by; see module docstring for the grep that establishes it "
        "and for the seven test-side rebinds this mutant leaves unpatched "
        "on purpose)."
    )


def pytest_testnodedown(node: Any, error: Any) -> None:  # noqa: ARG001
    """CONTROLLER side of the xdist aggregation -- merge one worker's counters.

    Fires on the controller as each worker shuts down, which is before the
    controller's own ``pytest_sessionfinish``/``pytest_terminal_summary``, so
    the merged totals are in place by the time the loudness verdict is taken.
    Absent under a serial run (no workers), where the local counters are
    already the whole truth.
    """
    workeroutput = getattr(node, "workeroutput", None)
    if not workeroutput:
        return
    payload = workeroutput.get(_WORKEROUTPUT_KEY)
    if not payload:
        return
    _state["bound"] = bool(_state["bound"] or payload.get("bound"))
    _state["calls"] += int(payload.get("calls", 0))


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:  # noqa: ARG001
    """Ship counters (worker) or force a non-zero exit status (controller/serial).

    MEASURED DEFECT, fixed here -- the xdist controller/worker state split
    ------------------------------------------------------------------------
    Under ``-n``, ``_non_progressing_dispatch`` runs, and so ``_state["calls"]``
    increments, ONLY inside the worker subprocess that owns the test. The
    loudness verdict below, and ``pytest_terminal_summary``, run ONLY on the
    controller, whose own ``_state["calls"]`` is permanently 0 because no test
    ever executes there. Before this fix, that made every ``-n`` run report
    ``NO VERDICT: ... suppressed ZERO calls`` and forced exit 1 -- on runs that
    manifestly DID reach the patched symbol.

    Measured with a known-answer control (the diagnostic-control rule): a
    3-test selection whose first test calls the patched symbol and asserts it
    got the mutated result. Serial: ``3 passed``, exit 0, guard quiet. Same
    selection under ``-n 2``: ``3 passed`` -- the reaching test still passes,
    proving the patch was live and called in the worker -- yet the controller
    printed ``suppressed ZERO calls`` and exit was 1. That run was
    indistinguishable from the genuine-non-arrival run, so the guard had no
    discriminating power at all under xdist: it was not merely noisy, it was
    uninformative in both directions.

    Forcing the exit status in the worker is NOT an available fix: a worker's
    ``session.exitstatus`` mutation is discarded by xdist rather than
    propagated to the controller's exit code. So the counters themselves have
    to travel. ``config.workeroutput`` is the supported channel -- xdist
    creates that dict on workers ONLY (its absence is exactly how this hook
    tells the two topologies apart), ships it to the controller at worker
    shutdown, and exposes it as ``node.workeroutput`` in
    ``pytest_testnodedown`` above.

    ``hang_a_fast_test_3115`` already solved its own version of this problem,
    via ``terminalreporter.stats``; that channel works there because the thing
    it needs to prove is the arrival of a TEST REPORT, which xdist already
    aggregates. A suppression COUNTER rides on no report, so it needs this
    explicit channel instead.

    Deliberately does not raise: a raise from ``pytest_sessionfinish`` (or
    from ``pytest_terminal_summary``, which this hook's sibling below is
    called from, internally, by the terminal reporter's own
    ``pytest_sessionfinish``) was measured, with a two-line probe plugin
    against this same pytest, to propagate as an uncaught traceback that
    pre-empts ``TerminalReporter.summary_stats()`` -- the code that prints the
    final ``N passed/failed in Ys`` line -- and the summary line is the count
    line NFR-003 says is the evidence. Mutating ``session.exitstatus`` here
    instead is read by ``wrap_session`` after every ``pytest_sessionfinish``
    hook has run, so the process still exits non-zero, and the trailing
    summary line still prints.
    """
    workeroutput = getattr(session.config, "workeroutput", None)
    if workeroutput is not None:
        # WORKER: ship local counters upward. Do not judge here -- this
        # process sees only its own shard, and its exit status is discarded.
        workeroutput[_WORKEROUTPUT_KEY] = {"bound": bool(_state["bound"]), "calls": int(_state["calls"])}
        return

    # CONTROLLER (totals merged by pytest_testnodedown) or serial run.
    if not _state["bound"] or _state["calls"] == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:  # noqa: ARG001 -- pytest hook signature
    """Report the per-site suppression split; print loudly if it is zero.

    See ``pytest_sessionfinish`` above for why this writes instead of
    raising, and for the xdist controller/worker split this guard reflects:
    on a WORKER the local counters describe only that worker's shard, so a
    per-worker report would be both wrong and (since xdist does not surface
    worker terminal summaries) invisible. The controller reports the merged
    totals.
    """
    if getattr(config, "workeroutput", None) is not None:
        return
    calls = _state["calls"]
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"[nonterminating_dispatch_3115] SESSION REPORT: "
        f"per-site split = {{{_SITE!r}: {calls}}} (1 production site, "
        f"{calls} call(s) suppressed this session)."
    )
    if _state["bound"] and calls:
        return
    if not _state["bound"]:
        message = (
            f"[nonterminating_dispatch_3115] NO VERDICT: FAILED TO BIND at "
            f"{_SITE} -- see the pytest_configure failure. This is a finding "
            "about the mutant, not about the code under test."
        )
    else:
        message = (
            f"[nonterminating_dispatch_3115] NO VERDICT: bound at {_SITE} "
            "but suppressed ZERO calls this session. A zero-suppressed-count "
            "run is a finding about the mutant (wrong node-ids selected, or "
            "the patched symbol genuinely unreached), not about the code "
            "under test -- no verdict may be drawn from it (C-003 self-proof "
            "requirement, spec.md C-003 / standing-rules.md rot-mode #4)."
        )
    terminalreporter.write_line(message, red=True, bold=True)
