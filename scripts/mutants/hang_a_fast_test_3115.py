"""FR-016 / FR-017 / T037 -- the deliberately non-terminating `fast` test
mutant that proves the timeout backstop reds by name instead of hanging the
job.

Load with (the ``-p`` flag is what actually loads it; ``PYTHONPATH`` alone
loads nothing -- C-003's corrected contract, mirrored in
``kitty-specs/.../standing-rules.md`` and already applied by WP11's
``nonterminating_dispatch_3115.py``):

    PYTHONPATH=scripts/mutants:$WT/src .venv/bin/python -m pytest \\
        -p hang_a_fast_test_3115 \\
        <a real fast selection, e.g. tests/kernel/>

Contract this module obeys, adapted for an INJECTED test rather than a
patched symbol (spec.md C-003, corrected by the post-plan squad; the WP12
brief's own restatement: "its loudness condition is 'the injected test was
never collected'"):

1. **Loading**: importable via ``PYTHONPATH=scripts/mutants`` AND loaded
   with ``-p hang_a_fast_test_3115``. A ``PYTHONPATH``-only mutant is
   imported by nothing and binds nothing.
2. **Injection site**: hook level, ``pytest_collection_modifyitems`` --
   never a same-named fixture. This module does not shadow any fixture; it
   appends one extra, hand-built ``pytest.Item`` to the collected list. It
   is a **plugin, not a committed test file** under ``tests/``, so nothing
   else can collect it, and removing ``-p hang_a_fast_test_3115`` from the
   invocation makes it vanish completely (no residual node-id anywhere).
3. **Self-proof**: prints a per-process binding report at collection time
   (the hook ran and the item was appended in THIS process), and separately
   verifies, at session end, that the injected node-id actually appears
   among ``terminalreporter.stats`` -- i.e. that some process in the
   session actually collected, ran and reported it. **This check is
   deliberately NOT ``session.items`` on the process running
   ``pytest_terminal_summary``/``pytest_sessionfinish``**: probed under
   ``-n2`` (xdist) on this WP, the CONTROLLER process's own
   ``pytest_collection_modifyitems`` never fires and its own
   ``session.items`` never contains the injected item -- collection happens
   in the WORKER, which is where the item is actually appended, run and
   timed out -- so a controller-``session.items`` check reads
   "never collected" on a run that manifestly did collect and red it (the
   ``FAILED ...`` line and the ``N failed, M passed`` count line both name
   it). ``terminalreporter.stats`` is populated from aggregated worker
   reports on the controller and from local reports in a serial run alike,
   so it is the one check that is correct in both topologies. If the
   injected test is absent from it, that is a **finding about the mutant,
   not about the code under test**, and it fails loudly: a forced non-zero
   exit status plus a printed red/bold terminal line
   (``pytest_terminal_summary`` + ``pytest_sessionfinish``), never a raise.
   A raise from either hook was measured on this mission (WP11's sibling
   mutant, same probe) to pre-empt
   ``TerminalReporter.summary_stats()`` -- the code that prints the final
   ``N passed/failed in Ys`` summary line -- which would defeat NFR-003's
   "the count line is the evidence" rule for exactly the run meant to prove
   there is no evidence.
4. **Reporting**: prints a binding report at collection time and a
   collected/verified report at session end, so both can be quoted beside a
   run's own summary line.

Why an injected test, not a patched symbol
-------------------------------------------
FR-017's red-first proof needs an actual **non-terminating `fast` test** in
the selection -- not a slow-but-finite one, and not a patched production
symbol (there is no single "make a test hang" production seam to patch;
hanging is a property of the *test*, not of any `src/` code this mission
touches). So this mutant injects one directly, at hook level, the same way
WP11's sibling mutant patches one production symbol at hook level -- both
obey C-003's "no source edits, no fixture shadowing" rule, applied to the
two different shapes of defect (a symbol swap vs. a synthetic node).

What the injected test does, and why it never terminates on its own
----------------------------------------------------------------------
``_HangingItem.runtest`` is an infinite ``while True: time.sleep(1)`` loop.
It touches no journal, ledger, receiver, or any other production state --
it is pure harness surface, deliberately inert except for never returning.
Nothing in this module ever breaks that loop; the only things that can end
it are (a) an external kill (a "no measurement" outcome per NFR-003 /
standing-rules.md), or (b) `pytest-timeout` firing inside the worker that
owns it, which is exactly the backstop FR-016/FR-017 add and the thing this
mutant exists to red-first before that backstop is in place.

Collected-count caveat (NFR-008): read any run under this mutant as
"collected N" **+ 1**
---------------------------------------------------------------------------
``items.append(item)`` in ``pytest_collection_modifyitems`` adds the
injected item to pytest's own execution list, but it does NOT bump
``TerminalReporter._numcollected`` -- that counter is set once, earlier,
from the ordinary collection pass, before this hook runs. So a run under
this mutant prints a "collected N items" line and a progress bar denominator
that are both **one short** of what actually executes: the terminal
percentage reads "N of (N+1)" style, and the final tally (e.g.
"1 failed, 11 passed") sums to N+1 while the printed "collected" line still
says N. Anyone quoting NFR-008's collected count from a run under this
mutant must add 1 to the printed "collected" figure to get the true count,
or (better) quote the tally sum instead, which is correct as printed.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

_MODULE_PATH = Path(__file__)
_ITEM_NAME = "test_injected_hang_a_fast_test_3115"

_state: dict[str, Any] = {"appended": False, "nodeid": None, "verified": False}


class _HangingItem(pytest.Item):
    """A hand-built pytest.Item whose ``runtest`` never returns.

    Deliberately not a ``pytest.Function`` wrapping a normal ``def
    test_...():`` -- full control over ``runtest`` is what lets this stay a
    pure, unconditional hang with no dependency on how pytest resolves a
    callable's signature/fixtures across versions.
    """

    def runtest(self) -> None:
        while True:  # noqa: ASYNC110 -- deliberately non-terminating
            time.sleep(1)

    def repr_failure(self, excinfo: Any, style: Any = None) -> Any:  # noqa: ARG002
        return super().repr_failure(excinfo)

    def reportinfo(self) -> tuple[Any, int, str]:
        return self.path, 0, f"hang_a_fast_test_3115: injected non-terminating fast test ({self.nodeid})"


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:  # noqa: ARG001
    """Injection site (C-003 (2), adapted): hook level, never a fixture."""
    parent = pytest.Module.from_parent(session, path=_MODULE_PATH)
    item = _HangingItem.from_parent(parent, name=_ITEM_NAME)
    item.add_marker("fast")
    items.append(item)
    _state["appended"] = True
    _state["nodeid"] = item.nodeid
    print(
        f"\n[hang_a_fast_test_3115] APPENDED nodeid={item.nodeid!r} "
        "(1 injected item -- see module docstring for why this is an "
        "injected test rather than a patched production symbol)."
    )


def _verified_via_stats(terminalreporter: Any) -> bool:
    """Self-proof (C-003 (3), adapted), made xdist-safe.

    MEASURED CORRECTION during this WP's own probe: under ``-n`` (xdist),
    ``pytest_collection_modifyitems`` fires in each WORKER subprocess (that
    is what actually runs and times out the injected item -- confirmed by a
    real ``Failed: Timeout (>3.0s) from pytest-timeout.`` red), but the
    CONTROLLER process does not perform its own local
    ``pytest_collection_modifyitems``/``session.items`` pass the way a
    serial run does -- it aggregates worker reports instead. A
    ``session.items``-based check (this module's first draft) therefore
    read ``appended=False, verified_collected=False`` on the controller
    even on a run that manifestly DID collect, run and red the injected
    test (the ``FAILED ...`` line and the ``1 failed, N passed`` count line
    both name it) -- a false "no verdict" alarm, the mutant's self-proof
    lying in the paranoid direction. Fixed by reading
    ``terminalreporter.stats`` instead: it is populated from aggregated
    worker reports on the controller (and from local reports in a serial
    run) alike, so this check is correct in both topologies.
    """
    for reports in terminalreporter.stats.values():
        for rep in reports:
            nodeid = getattr(rep, "nodeid", "")
            if nodeid.endswith(f"::{_ITEM_NAME}"):
                return True
    return False


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    """Force a non-zero exit status on a no-verdict run, without raising.

    See ``nonterminating_dispatch_3115.py``'s sibling hook for the measured
    reason this mutates ``session.exitstatus`` instead of raising: a raise
    here (or from ``pytest_terminal_summary``) was measured to pre-empt
    ``TerminalReporter.summary_stats()`` and destroy the final count line --
    the exact evidence NFR-003 requires from a run meant to prove there is
    none.
    """
    terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
    _state["verified"] = bool(terminalreporter is not None and _verified_via_stats(terminalreporter))
    if not _state["verified"]:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:  # noqa: ARG001
    """Report the binding/verification outcome; print loudly if it failed."""
    verified = _verified_via_stats(terminalreporter)
    _state["verified"] = verified
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"[hang_a_fast_test_3115] SESSION REPORT: appended_this_process={_state['appended']}, "
        f"verified_via_stats={verified}, nodeid_this_process={_state['nodeid']!r}. "
        "('appended_this_process'/'nodeid_this_process' reflect only THIS process's own "
        "pytest_collection_modifyitems call -- under xdist that is correctly False/None on "
        "the controller even on a fully successful run, since the controller does not "
        "collect locally; 'verified_via_stats' is the authoritative, topology-independent "
        "check.)"
    )
    if verified:
        return
    message = (
        "[hang_a_fast_test_3115] NO VERDICT: the injected test "
        f"({_ITEM_NAME!r}) never appears in terminalreporter.stats -- it was "
        "never collected/run/reported by any process in this session. "
        "This is a finding about the mutant, not about the code under "
        "test -- no verdict about the timeout backstop may be drawn from "
        "this run (C-003 self-proof requirement, spec.md C-003 / "
        "standing-rules.md rot-mode #4)."
    )
    terminalreporter.write_line(message, red=True, bold=True)
