"""Mutant: attribute every mocked ``time.sleep`` call to its calling thread
and its patch site (C-003, FR-005, #3115).

WP06's floor (T020) tried ten selections against
``tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after``
and reproduced the reported ``AssertionError: Expected 'sleep' to be called
once. Called <n> times.`` in **none** of them (see the WP06 report /
``notes/`` for the full enumeration with collected counts). This mutant does
not try to force that reproduction again -- it instruments the *mechanism*
FR-005 already established as given, so that **if** an extra call ever does
land on a ``time.sleep`` mock in this cone, this run can say *which thread*
made it, rather than only that the tally moved.

Why the target is ``(time, sleep)``, not an import site
---------------------------------------------------------
``src/specify_cli/tracker/saas_client.py:19`` is a bare ``import time``, so
``specify_cli.tracker.saas_client.time`` **is** the stdlib ``time`` module
object -- not a separate name bound to it. Every ``@patch("<anything>.time.sleep")``
in the tree, regardless of which module's dotted path is used to reach it,
resolves ``getter()`` to that same module object and patches the same
``sleep`` attribute on it. This is the **opposite** shape from
``neutralise_reset_token_manager_3115``'s fifth-rot-mode target (``from X
import f`` rebinds by value, producing genuinely independent references) --
here there is structurally only ONE object being patched, ever, however many
dotted strings name it. So "the per-site split across every name the symbol
is reachable by" (C-003 contract) is reported here as the **distinct
``@patch(...)`` target strings** actually entered this session (the "site"
dimension the contract asks for), crossed with the **calling thread name**
(the dimension this specific investigation needs) -- not an import-rebind
census, because there is no rebinding to census.

Loading (binding, C-003 §1 -- corrected contract)
----------------------------------------------------
    PYTHONPATH=scripts/mutants <venv>/bin/python -m pytest \\
        -p attribute_sleep_count_3115 \\
        tests/sync/tracker/test_saas_client.py

``PYTHONPATH`` alone loads nothing: it only makes this module *importable*.
Pytest does not import every importable module on ``sys.path`` as a plugin --
only ones it is told to load. Without ``-p`` (or ``PYTEST_PLUGINS=...``) this
file is never imported, never binds, and the run reads as a passing gate
while instrumenting nothing. The ``-p`` flag is therefore load-bearing and
MUST be quoted in any evidence taken under this mutant (mirrors
``disable_render_seam_3115`` and ``neutralise_reset_token_manager_3115``,
both approved precedents on this mission).

**Binding, serial-only (round 2, measured).** This mutant's module-level
dicts (``_activations_by_site``, ``_calls_by_site_thread``) live in **one
Python process**. Under ``-n auto`` / ``-n <N> --dist loadfile``, pytest-xdist
runs each worker (``gw0``, ``gw1``, ...) as a **separate OS process**, each
with its own import of this module and its own empty dicts; nothing merges
them back to the controller process that prints
``pytest_terminal_summary``. Measured twice: a 53-test file at
``-n 2 --dist loadfile`` gave ``53 passed`` but
``activations per site: {}``, ``total recorded calls: 0``, exit status 1, no
``VERDICT`` banner content; a full ``tests/sync/`` run at
``-n auto --dist loadfile`` (16 workers) gave ``3 failed, 2367 passed, 18
skipped`` with the identical empty-report shape. Both runs' individual tests
still passed or failed correctly -- the *tests'* own mocks worked per-worker
-- only this mutant's **aggregate report** is structurally empty under xdist.
**Serial mode (no ``-n``) is required for this mutant's report to mean
anything**; it recorded 11 real activations there in round 1's mechanism
proof. Cheap per-worker aggregation (e.g. writing each worker's dicts to a
per-``gw<N>`` file at ``pytest_sessionfinish`` and reconciling them in a
follow-up pass) is possible but not built here -- this caveat is the binding
substitute.

Instrumentation site (binding, C-003 §2)
-------------------------------------------
Hook level, in ``pytest_configure`` -- **never** a same-named fixture. There
is no fixture named ``time.sleep`` to shadow; the thing being intercepted is
``unittest.mock._patch.__enter__`` itself, which every ``@patch(...)``
decorator and every ``with patch(...):`` block calls to perform the patch
(the decorator form calls it via ``_patch.start()``, which calls
``__enter__``; both paths go through this one method). This module wraps
``unittest.mock._patch.__enter__`` at ``pytest_configure`` -- before any test
collects or runs -- so every patch entered for the rest of the session,
across every test file selected, passes through the wrapper. The wrapper
calls the real ``__enter__`` first and only acts on the result when
``self.attribute == "sleep"`` and the resolved target module's ``__name__``
is ``"time"`` -- every other patch (``httpx.Client``, ``time.monotonic``,
``_force_refresh_sync``, ...) passes through completely untouched.

Non-destructive by construction: if the matched mock already has a
non-``None``, non-callable ``side_effect`` at the moment this wrapper
inspects it (e.g. ``patch(..., side_effect=some_list_or_exception)``, a shape
used outside this WP's ownership --
``tests/sync/test_final_sync_diagnostics.py:260`` patches
``specify_cli.sync.batch.time.sleep`` this way), this mutant does **not**
touch it: the activation is recorded (the site is seen) but call-attribution
is skipped for that one mock, named in the report as "seen, not
instrumented" rather than silently folded into the counted totals or, worse,
silently corrupting an unrelated test's behavior. Where the existing
``side_effect`` is callable (or absent), this mutant wraps it: its own
recorder runs first, then the original callable runs (chained), so the
underlying test's own semantics are preserved bit-for-bit -- only the
recording is added.

Self-proof (binding, C-003 §3 -- all three mandatory)
------------------------------------------------------
1. **Binding assertion.** ``pytest_configure`` imports ``unittest.mock`` and
   asserts ``_patch.__enter__`` is present and callable before wrapping it.
   Absent, renamed or relocated -> loud failure (``pytest.UsageError``)
   *before* the session runs; no test result from this run may be trusted.
2. **Per-site split, reported by name.** Every matching patch activation is
   attributed to the exact string passed to ``patch(...)`` (reconstructed
   from ``self.getter.args[0] + "." + self.attribute`` -- ``self.getter`` is
   ``functools.partial(pkgutil.resolve_name, "<module-path>")`` per
   ``unittest.mock._get_target``), and every recorded call is attributed to
   that site **and** to ``threading.current_thread().name``. The report
   prints both the per-site activation counts and the full
   ``(site, thread) -> call count`` table, never a bare aggregate integer,
   per C-003's fifth rot mode ("a single aggregate count cannot distinguish
   'both sites mutated' from 'one mutated, one inert'") -- restated here for
   the thread dimension this investigation actually needs: a single
   aggregate call count cannot distinguish "all calls came from the test's
   own thread" from "some calls came from a leaked thread," which is
   precisely FR-005's open question.
3. **Loud failure if the symbol it patched was never called.** If the sum of
   every recorded call across every site is zero at session end -- whether
   because no test in this run ever entered a matching patch, or because one
   was entered but the mock was never invoked -- that is a finding about the
   run's selection (wrong node-ids, or the patched attribute genuinely
   unreached), never a finding about FR-005's mechanism, and no verdict may
   be drawn from it. Reported via a forced non-zero ``session.exitstatus``
   plus a bold/red terminal line rather than a raise from
   ``pytest_sessionfinish`` -- ``nonterminating_dispatch_3115`` measured
   that raising from that hook (or from ``pytest_terminal_summary``, its own
   ``sessionfinish`` sibling calls it from) propagates as an uncaught
   traceback that pre-empts ``TerminalReporter.summary_stats()``, destroying
   the final ``N passed/failed in Ys`` count line -- exactly the evidence
   NFR-003 says is load-bearing, for exactly the run meant to prove there is
   none. The same non-raising shape is used here for the same measured
   reason.

Reporting (binding, C-003 §4)
----------------------------------
``pytest_terminal_summary`` prints the per-site activation counts, the full
``(site, thread)`` call table, and the per-thread totals, so they can be
quoted beside the run's own count line. Every load-bearing quote of a run
under this mutant MUST include this report, not just "ran under the mutant,
thread X showed up."

Call-stack attribution (round 2 -> round 3 addition)
------------------------------------------------------
A thread *name* is not a call site: most leaked worker/daemon threads in
this tree are unnamed (``threading.Thread(target=...).start()`` with no
``name=``), so every one of them reports as ``"Thread-N"`` or, when the
intruder is a background ``.wait()`` running synchronously on a thread that
was itself started without a name, indistinguishable from any other. To
name the actual call site, ``_recorder`` captures
``traceback.extract_stack()`` on the first ``_MAX_STACK_SAMPLES_PER_KEY``
(5) calls for each ``(site, thread)`` key and reports the **modal**
signature -- the most common stack shape among the samples -- because a
busy-wait loop (this mutant's whole reason for existing: FR-005's own
established mechanism is a *loop* re-entering ``time.sleep`` from the same
source line every iteration) produces near-identical stacks call after
call, so even 5 samples reliably name it. Capped, not unconditional:
measured independently that a single ``Popen.wait(timeout=0.2)`` produces
tens of thousands of calls in one patch window, so capturing on every call
would make this mutant itself the bottleneck.
"""

from __future__ import annotations

import threading
import traceback
from collections import Counter
from typing import Any
from unittest import mock

import pytest

_TARGET_ATTRIBUTE = "sleep"
_TARGET_MODULE_NAME = "time"

# Key under which a worker ships its local counters to the controller.
_WORKEROUTPUT_KEY = "attribute_sleep_count_3115"

# Sentinel distinguishing "argument not supplied" from a legitimate `None`
# in the wrapped `MonkeyPatch.setattr` signature (which is overloaded: the
# 2-arg form takes a "module.attr" string, the 3-arg form an object + name).
_MP_NOTSET = object()

# The substitution mechanisms this instrument DOES observe.
_COVERED_MECHANISMS: tuple[str, ...] = (
    "unittest.mock._patch.__enter__ -- i.e. mock.patch(...) / @patch(...) naming (time, sleep)",
    'MonkeyPatch.setattr(<module>, "sleep", <callable>) -- the 3-arg object+name form',
)

# Declared, never counted as zero (C-003: report the per-site split; "patched"
# alone is not a finding). Ways a test can substitute a sleep that this
# instrument still cannot see.
_UNCOVERED_MECHANISMS: tuple[str, ...] = (
    'MonkeyPatch.setattr(<obj>, "time", <fake module>) -- substitutes the whole time '
    "module rather than its sleep attribute (e.g. tests/sync/test_daemon.py:229)",
    'MonkeyPatch.setattr("module.path.sleep", <callable>) -- the 2-arg string-target form',
    "plain assignment (`mod.time.sleep = f`) and fixtures that swap the clock wholesale",
    "any substitution performed before pytest_configure runs",
)

_state: dict[str, Any] = {"bound": False, "original_enter": None, "original_mp_setattr": None}

# site (the exact string passed to `patch(...)`) -> number of times a
# matching `_patch.__enter__` ran this session.
_activations_by_site: dict[str, int] = {}

# (site, calling-thread-name) -> number of recorded calls to the mock.
_calls_by_site_thread: dict[tuple[str, str], int] = {}

# Sites seen with a pre-existing non-callable side_effect -- activation
# recorded, call-attribution deliberately skipped (see module docstring).
_uninstrumented_sites: set[str] = set()

# Round 3 (FR-005 rejection #2): naming the call site, not just the thread.
# A leaked live thread's *name* ("MainThread" is the common case when the
# intruder is spawned without an explicit `name=`) does not say what code is
# calling `time.sleep`. Capped at this many stack captures per (site,
# thread) key -- capturing on every call is not affordable once a saturated
# `subprocess.Popen._wait` busy-loop is producing tens of thousands of calls
# inside a single patch window (measured independently: a single 0.2s
# `Popen.wait(timeout=0.2)` produced 30169 calls to a patched `time.sleep` on
# this machine; the reviewer's own probe produced hundreds of thousands).
# The first few calls from a given (site, thread) key already carry the
# call site, because a busy-wait loop calls `time.sleep` from the same
# source line on every iteration.
_MAX_STACK_SAMPLES_PER_KEY = 5

# (site, calling-thread-name) -> list of stack signatures, one per captured
# call, each signature innermost-frame-first (see `_capture_stack_signature`).
_stack_samples: dict[tuple[str, str], list[tuple[str, ...]]] = {}


def _capture_stack_signature() -> tuple[str, ...]:
    """A short, comparable signature naming the real caller.

    ``traceback.extract_stack()`` returns outermost-frame-first; this
    function drops its own frame and `_recorder`'s frame, reverses to
    innermost-first (the direct caller of the mocked ``time.sleep`` comes
    first), skips frames inside ``unittest/mock.py`` and inside this module
    (both are the instrumentation, not the caller), and keeps at most 6
    frames -- enough to name the call site without printing the interpreter
    bootstrap and pytest's own frames on every sample.
    """
    frames = traceback.extract_stack()[:-2]  # drop this frame + _recorder's
    signature: list[str] = []
    for frame in reversed(frames):
        if frame.filename.endswith("unittest/mock.py") or frame.filename == __file__:
            continue
        signature.append(f"{frame.filename}:{frame.lineno} in {frame.name}")
        if len(signature) >= 6:
            break
    return tuple(signature)


def _site_for(patcher: Any) -> str | None:
    """Reconstruct the exact `patch("...")` string from a `_patch` instance.

    Returns ``None`` if this patcher does not match ``(time, sleep)`` --
    the fast-path guard every other patch in the suite takes.
    """
    if getattr(patcher, "attribute", None) != _TARGET_ATTRIBUTE:
        return None
    target = getattr(patcher, "target", None)
    if getattr(target, "__name__", None) != _TARGET_MODULE_NAME:
        return None
    getter = getattr(patcher, "getter", None)
    module_path = None
    if getter is not None and hasattr(getter, "args") and getter.args:
        module_path = getter.args[0]
    if module_path is None:
        return f"<unresolved-module-path>.{_TARGET_ATTRIBUTE}"
    return f"{module_path}.{_TARGET_ATTRIBUTE}"


def _record(site: str) -> None:
    """Count one call and, for the first few, capture the calling stack."""
    key = (site, threading.current_thread().name)
    _calls_by_site_thread[key] = _calls_by_site_thread.get(key, 0) + 1
    samples = _stack_samples.setdefault(key, [])
    if len(samples) < _MAX_STACK_SAMPLES_PER_KEY:
        samples.append(_capture_stack_signature())


def _make_recorder(site: str, existing: Any):
    """Chain a call-recorder in front of a mock's existing ``side_effect``.

    Two bugs fixed here on a pre-merge review, both of which made loading this
    module CHANGE THE OUTCOME of tests it does not own -- unacceptable in
    something whose whole purpose is to observe. Both were measured red-first
    against a 2-test control that passes with no plugin loaded and failed with
    it:

    ``return mock.DEFAULT``, not ``None``
        For a ``side_effect`` callable, ``mock`` treats a ``None`` return as
        "this IS the call's return value" and a ``DEFAULT`` return as "fall
        through to ``return_value``". The old ``return None`` therefore
        silently clobbered whatever ``return_value`` the test had configured:
        ``mock.patch("time.sleep", return_value="configured")`` yielded
        ``None``, failing ``assert time.sleep(0) == "configured"``.

    exception classes must be RAISED, not called
        ``mock`` semantics: a ``side_effect`` that is an exception class or
        instance is raised. But a class IS callable, so the old
        ``not callable(existing)`` guard let it past and the
        ``existing(*args, **kwargs)`` line CONSTRUCTED it and returned the
        instance. ``mock.patch("time.sleep", side_effect=ValueError)`` then did
        not raise at all -- turning a test that asserts a raise into a silent
        pass or an unrelated failure.
    """
    is_exception = isinstance(existing, BaseException) or (isinstance(existing, type) and issubclass(existing, BaseException))

    def _recorder(*args: Any, **kwargs: Any) -> Any:
        _record(site)
        if existing is None:
            # Hand control back to the mock so it returns whatever
            # `return_value` the test configured. Returning None would
            # OVERRIDE that, changing an unowned test's observed behavior.
            return mock.DEFAULT
        if is_exception:
            raise existing
        return existing(*args, **kwargs)

    return _recorder


def _instrumented_enter(self: Any, *args: Any, **kwargs: Any) -> Any:
    result = _state["original_enter"](self, *args, **kwargs)

    site = _site_for(self)
    if site is None:
        return result

    _activations_by_site[site] = _activations_by_site.get(site, 0) + 1

    mock_obj = result
    existing = getattr(mock_obj, "side_effect", None)
    if existing is not None and not callable(existing):
        _uninstrumented_sites.add(site)
        return result

    try:
        mock_obj.side_effect = _make_recorder(site, existing)
    except Exception:  # pragma: no cover - defensive, never observed
        _uninstrumented_sites.add(site)

    return result


def _make_mp_counter(site: str, replacement: Any):
    """Wrap a monkeypatch replacement so calls to it are counted.

    A separate factory, deliberately, NOT a closure defined inline in
    `_instrumented_mp_setattr`: an inline closure over the local `value` that
    is then rebound (`value = _counting`) captures the VARIABLE, not the
    object, so the wrapper ends up calling itself. That was measured here as a
    real `RecursionError` (957 recorded calls before the stack blew) on the
    first draft of this fix -- caught by the red-first control, which is the
    only reason it is not in the committed file.
    """

    def _counting(*args: Any, **kwargs: Any) -> Any:
        _record(site)
        return replacement(*args, **kwargs)

    return _counting


def _instrumented_mp_setattr(self: Any, target: Any, name: Any = _MP_NOTSET, value: Any = _MP_NOTSET, raising: bool = True) -> Any:
    """Intercept ``MonkeyPatch.setattr`` for `time.sleep` substitutions.

    THE MEASURED BLIND SPOT this closes. `_instrumented_enter` sees only
    ``unittest.mock._patch``, so every `monkeypatch`-based sleep substitution
    was invisible -- and in the cone this instrument was built for
    (``tests/sync/``) those are the MAJORITY: 12 of them, at
    ``test_issue_598_hang_fixes.py:632,656,674,703,722,798,854,921`` and
    ``test_daemon.py:229,306,329,386``, against a handful of ``mock.patch``
    forms. A zero-count run over ``tests/sync/`` therefore forced exit 1 and
    printed "the patched attribute genuinely unreached" while sleeps were in
    fact mocked throughout -- an assertion of absence that did not establish
    why the thing would otherwise have happened, which is precisely the shape
    standing-rules.md forbids. Measured red-first: a single monkeypatch-based
    test that substitutes and calls ``time.sleep`` twice reported
    ``activations {}, total recorded calls 0`` plus the NO VERDICT line.

    Only the ``setattr(obj, "sleep", callable)`` form is wrapped, which is 11
    of the 12 cited sites. ``test_daemon.py:229`` replaces the whole ``time``
    MODULE on the target rather than its ``sleep`` attribute; that form is
    declared in `_UNCOVERED_MECHANISMS` rather than silently counted as zero.
    """
    # Only the 3-arg form `setattr(target, name, value)` names an attribute;
    # the 2-arg string form `setattr("mod.attr", value)` is passed through.
    if name is not _MP_NOTSET and value is not _MP_NOTSET and name == _TARGET_ATTRIBUTE and callable(value):
        module_name = getattr(target, "__name__", None)
        if module_name is not None:
            site = f"monkeypatch:{module_name}.{_TARGET_ATTRIBUTE}"
            _activations_by_site[site] = _activations_by_site.get(site, 0) + 1
            value = _make_mp_counter(site, value)

    if value is _MP_NOTSET:
        return _state["original_mp_setattr"](self, target, name, raising=raising)
    return _state["original_mp_setattr"](self, target, name, value, raising=raising)


def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001 -- pytest hook signature
    """Bind at hook level (C-003 §2) and assert the binding took (C-003 §3.1)."""
    try:
        from _pytest.monkeypatch import MonkeyPatch
    except ImportError as exc:  # pragma: no cover - defensive, loud by design
        raise pytest.UsageError(
            "attribute_sleep_count_3115: cannot import _pytest.monkeypatch.MonkeyPatch "
            f"to bind the second substitution mechanism it instruments ({exc})."
        ) from exc

    original_mp = getattr(MonkeyPatch, "setattr", None)
    if original_mp is None or not callable(original_mp):
        raise pytest.UsageError(
            "attribute_sleep_count_3115: _pytest.monkeypatch.MonkeyPatch.setattr is "
            "absent, renamed, relocated, or not callable. This mutant's binding "
            "assertion failed at pytest_configure."
        )
    _state["original_mp_setattr"] = original_mp
    MonkeyPatch.setattr = _instrumented_mp_setattr
    _state["bound_monkeypatch"] = MonkeyPatch.setattr is _instrumented_mp_setattr

    try:
        import unittest.mock as mock_module
    except ImportError as exc:  # pragma: no cover - defensive, loud by design
        raise pytest.UsageError(
            "attribute_sleep_count_3115: cannot import unittest.mock to bind the "
            f"method it is meant to instrument ({exc}). This mutant's self-proof "
            "failed at configure time; no test result from this run may be trusted."
        ) from exc

    original = getattr(mock_module._patch, "__enter__", None)
    if original is None or not callable(original):
        raise pytest.UsageError(
            "attribute_sleep_count_3115: unittest.mock._patch.__enter__ is absent, "
            "renamed, relocated, or not callable. This mutant's binding assertion "
            "failed at pytest_configure -- nothing was instrumented, and no verdict "
            "about FR-005's mechanism may be drawn from this run."
        )

    _state["original_enter"] = original
    mock_module._patch.__enter__ = _instrumented_enter
    _state["bound"] = mock_module._patch.__enter__ is _instrumented_enter
    if not _state["bound"]:  # pragma: no cover - defensive, loud by design
        raise pytest.UsageError(
            "attribute_sleep_count_3115: FAILED TO BIND at unittest.mock._patch.__enter__ "
            "-- attribute assignment did not stick. This is a finding about the mutant, "
            "not about the code under test; no verdict may be drawn from this run "
            "(C-003 self-proof requirement)."
        )
    print(
        "\n[attribute_sleep_count_3115] BOUND at unittest.mock._patch.__enter__ "
        "(matches any `@patch(\"<...>.time.sleep\")`, reported per exact target "
        "string -- see module docstring for why there is exactly one underlying "
        "object regardless of how many strings name it)."
    )


def _format_report() -> list[str]:
    total_calls = sum(_calls_by_site_thread.values())
    total_activations = sum(_activations_by_site.values())
    lines = [
        "attribute_sleep_count_3115 instrument report (C-003 self-proof):",
        f"  bound at pytest_configure: mock._patch.__enter__={_state['bound']}, "
        f"MonkeyPatch.setattr={_state.get('bound_monkeypatch')}",
        "  mechanisms OBSERVED by this instrument:",
        *(f"    + {m}" for m in _COVERED_MECHANISMS),
        "  mechanisms NOT observed (declared, so a zero count cannot read as 'unreached'):",
        *(f"    - {m}" for m in _UNCOVERED_MECHANISMS),
        f"  activations per site (patch entered, matched (time, sleep)): {_activations_by_site!r}",
        f"  total activations: {total_activations}",
        f"  calls per (site, thread): {dict(sorted(_calls_by_site_thread.items()))!r}",
        f"  total recorded calls: {total_calls}",
    ]
    threads_seen = sorted({thread for (_site, thread) in _calls_by_site_thread})
    per_thread_totals = {
        thread: sum(c for (_s, t), c in _calls_by_site_thread.items() if t == thread) for thread in threads_seen
    }
    lines.append(f"  per-thread totals across all sites: {per_thread_totals!r}")
    if _uninstrumented_sites:
        lines.append(
            "  seen, NOT instrumented (pre-existing non-callable side_effect, left "
            f"untouched to avoid corrupting an unowned test's behavior): {sorted(_uninstrumented_sites)!r}"
        )
    if _stack_samples:
        lines.append(
            f"  modal call-stack per (site, thread) -- up to {_MAX_STACK_SAMPLES_PER_KEY} "
            "samples each, innermost frame first, unittest/mock.py and this module elided:"
        )
        for key in sorted(_stack_samples):
            samples = _stack_samples[key]
            if not samples:
                continue
            counts = Counter(samples)
            modal_signature, modal_count = counts.most_common(1)[0]
            innermost = modal_signature[0] if modal_signature else "<empty stack>"
            lines.append(f"    {key}: modal {modal_count}/{len(samples)} samples -> {innermost}")
            lines.append(f"      full modal stack (innermost..outermost): {list(modal_signature)!r}")
    return lines


def pytest_testnodedown(node: Any, error: Any) -> None:  # noqa: ARG001
    """CONTROLLER side of the xdist aggregation -- merge one worker's counters.

    Fires on the controller as each worker shuts down, before the controller's
    own ``pytest_sessionfinish``/``pytest_terminal_summary``. Absent in a
    serial run, where the local counters are already the whole truth.

    ``_calls_by_site_thread`` and ``_stack_samples`` are keyed by a
    ``(site, thread)`` TUPLE, which does not survive the execnet round trip as
    a dict key, so the payload carries them as ``[site, thread, count]`` lists
    and they are re-keyed here.
    """
    workeroutput = getattr(node, "workeroutput", None)
    if not workeroutput:
        return
    payload = workeroutput.get(_WORKEROUTPUT_KEY)
    if not payload:
        return
    _state["bound"] = bool(_state["bound"] or payload.get("bound"))
    _state["bound_monkeypatch"] = bool(_state.get("bound_monkeypatch") or payload.get("bound_monkeypatch"))
    for site, count in (payload.get("activations_by_site") or {}).items():
        _activations_by_site[site] = _activations_by_site.get(site, 0) + int(count)
    for site, thread, count in payload.get("calls_by_site_thread") or []:
        key = (site, thread)
        _calls_by_site_thread[key] = _calls_by_site_thread.get(key, 0) + int(count)
    for site, thread, samples in payload.get("stack_samples") or []:
        bucket = _stack_samples.setdefault((site, thread), [])
        for sample in samples:
            if len(bucket) < _MAX_STACK_SAMPLES_PER_KEY:
                bucket.append(tuple(sample))
    _uninstrumented_sites.update(payload.get("uninstrumented_sites") or [])


def pytest_sessionfinish(session: pytest.Session) -> None:  # noqa: ARG001
    """Ship counters (worker), or force a non-zero exit status (controller/serial).

    MEASURED DEFECT, fixed here -- the xdist controller/worker state split
    ----------------------------------------------------------------------
    The recorders run, and so the counters increment, ONLY inside the worker
    that owns the test; this verdict runs ONLY on the controller, whose
    counters are permanently 0. Uncorrected, EVERY ``-n`` run reported
    ``recorded ZERO calls`` and forced exit 1. Measured: a 3-test selection
    whose first test enters a ``(time, sleep)`` patch and calls it twice gave
    ``total activations: 1, total recorded calls: 2``, exit 0 serially -- and
    ``total activations: 0, total recorded calls: 0`` plus the NO VERDICT line
    and exit 1 under ``-n 2``, on the same passing selection. A worker's
    ``session.exitstatus`` mutation is discarded by xdist, so the counters
    themselves travel via ``config.workeroutput`` (workers only) and are
    merged on the controller in ``pytest_testnodedown``.

    Deliberately does not raise -- see ``nonterminating_dispatch_3115``'s and
    ``neutralise_reset_token_manager_3115``'s docstrings for the measured
    reason: a raise from this hook (or from ``pytest_terminal_summary``)
    propagates as an uncaught traceback that pre-empts
    ``TerminalReporter.summary_stats()`` and destroys the final count line,
    which would defeat NFR-003's "the count line is the evidence" rule for
    exactly the run meant to prove there is none.
    """
    workeroutput = getattr(session.config, "workeroutput", None)
    if workeroutput is not None:
        # WORKER: ship local counters upward; do not judge on a partial shard.
        workeroutput[_WORKEROUTPUT_KEY] = {
            "bound": bool(_state["bound"]),
            "bound_monkeypatch": bool(_state.get("bound_monkeypatch")),
            "activations_by_site": dict(_activations_by_site),
            "calls_by_site_thread": [[site, thread, count] for (site, thread), count in _calls_by_site_thread.items()],
            "stack_samples": [[site, thread, [list(s) for s in samples]] for (site, thread), samples in _stack_samples.items()],
            "uninstrumented_sites": sorted(_uninstrumented_sites),
        }
        return

    # CONTROLLER (totals merged by pytest_testnodedown) or serial run.
    total_calls = sum(_calls_by_site_thread.values())
    if not _state["bound"] or total_calls == 0:
        session.exitstatus = 1


def pytest_terminal_summary(
    terminalreporter: Any, exitstatus: int, config: pytest.Config  # noqa: ARG001
) -> None:
    """Print the per-site/per-thread report; write loudly if it proves nothing.

    Skipped on xdist workers, whose counters cover only their own shard and
    whose terminal summary xdist does not surface anyway.
    """
    if getattr(config, "workeroutput", None) is not None:
        return

    for line in _format_report():
        terminalreporter.write_line(line)

    total_calls = sum(_calls_by_site_thread.values())
    if _state["bound"] and total_calls:
        return

    if not _state["bound"]:  # pragma: no cover - defensive, loud by design
        message = (
            "[attribute_sleep_count_3115] NO VERDICT: FAILED TO BIND at "
            "unittest.mock._patch.__enter__ -- see the pytest_configure failure. "
            "This is a finding about the mutant, not about the code under test."
        )
    else:
        message = (
            "[attribute_sleep_count_3115] NO VERDICT: bound, but recorded ZERO "
            "calls to any (time, sleep) substitution this session. This does NOT "
            "establish that sleeps were unmocked: this instrument observes only "
            f"the {len(_COVERED_MECHANISMS)} mechanisms listed as OBSERVED above, and a sleep "
            f"substituted by any of the {len(_UNCOVERED_MECHANISMS)} mechanisms listed as NOT observed "
            "produces exactly this same zero. A zero here is a finding about the "
            "selection or about this instrument's coverage -- never evidence that "
            "the attribute was genuinely unreached (C-003 self-proof requirement; "
            "standing-rules.md: any assertion of absence must establish why the "
            "thing would otherwise have happened)."
        )
    terminalreporter.write_line(message, red=True, bold=True)
