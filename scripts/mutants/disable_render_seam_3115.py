"""Mutant: neutralise WP02's render-surface seam at hook level (C-003, FR-002, #3115).

Proves the FR-002 falsifier actually discriminates: run WP01's victim files
with this mutant loaded and they must red with WP01's exact assertion text;
without it (seam enabled), the same command must green. "A green that was
never shown to be able to red is not a pass" (R8).

Loading (binding, C-003 §1 — corrected contract)
--------------------------------------------------
    PYTHONPATH=scripts/mutants <venv>/bin/python -m pytest -p disable_render_seam_3115 ...

``PYTHONPATH`` alone loads nothing: it only makes the module *importable*.
Pytest does not import every importable module on ``sys.path`` as a plugin —
only ones it is told to load. Without ``-p`` (or ``PYTEST_PLUGINS=...``) this
file is never imported, never binds, and the run reads as a passing gate
while having mutated nothing. The ``-p`` flag is therefore load-bearing and
MUST be quoted in any evidence taken under this mutant.

Neutralisation site (binding, C-003 §2)
----------------------------------------
Hook level, via ``pytest_fixture_setup`` — NEVER a same-named fixture. A
same-named autouse fixture defined in a plugin *loses* to the conftest
fixture for every item collected under that conftest's directory (pytest
resolves conftest-defined fixtures at higher precedence than plugin-defined
ones with the same name), so "redefine ``_plain_cli_console_seam`` in this
plugin" is a guaranteed no-op — probed against a known-answer baseline: the
hook-level form below produces a named red (``AssertionError: seam was off``
from the FR-001 falsifier's own assertions); the same-named-fixture form did
not bind at all (the conftest fixture kept winning).

This module intercepts ``tests.conftest._plain_cli_console_seam``'s setup at
``pytest_fixture_setup`` (``tryfirst=True`` so it is asked before the core
implementation in ``_pytest.fixtures``) and, when the requested fixture is
the seam, short-circuits it to a cached ``None`` result *without* calling the
real generator body — so neither the colour toggle (``CliConsole.set_all_plain``)
nor the width/height pin (``console.size = (...)``) ever runs, and the ambient
dumb-terminal / ``FORCE_COLOR`` environment is left exactly as narrow and
untinted as it would be with no seam at all.

Self-proof (binding, C-003 §3 — all three mandatory)
------------------------------------------------------
1. **Binding assertion.** ``pytest_configure`` imports ``tests.conftest`` and
   asserts ``_plain_cli_console_seam`` is present under that exact name.
   Absent, renamed or relocated -> loud failure (``pytest.UsageError``)
   *before* the session runs; no test result from this run may be trusted.
2. **Per-site split, reported by name.** The seam has exactly ONE definition
   site — ``tests/conftest.py`` — unlike FR-009's ``reset_token_manager``
   (five function-local imports plus two eager-by-value ones). The split is
   therefore ``{"tests.conftest._plain_cli_console_seam": <suppressed count>}``,
   reported by name rather than folded into a bare aggregate integer, per
   C-003's fifth rot mode: "a single aggregate count cannot distinguish 'both
   sites mutated' from 'one mutated, one inert'" — stated explicitly even
   though N=1 here, so a future second definition site cannot silently join
   the aggregate unnoticed.
3. **Loud failure on zero suppressions.** If the seam's setup was never
   intercepted during the session, ``pytest_sessionfinish`` forces a non-zero
   exit status and ``pytest_terminal_summary`` writes a red/bold NO VERDICT
   line -- it does **NOT** raise (see below). "Ran under the mutant, still
   green" with a suppressed count of zero is a finding about the mutant
   (nothing requested the fixture) or the environment (autouse fixture never
   bound), never about the seam, and no verdict may be drawn from it.

   **Corrected on a pre-merge review, because this file was the outlier.**
   The zero-suppression path used to ``raise pytest.UsageError`` from
   ``pytest_sessionfinish``. ``TerminalReporter.pytest_sessionfinish`` is a
   ``wrapper=True`` hookimpl, so the raise surfaces at its ``yield`` and skips
   ``pytest_terminal_summary``, ``summary_failures`` and ``summary_stats``.
   Measured on a 2-test throwaway carrying one real failure: without the
   plugin, exit 1 and ``1 failed, 1 passed in 0.02s``; with the raising form,
   **exit 4, no count line at all** (``grep -c`` -> 0) and no traceback. So
   NFR-003 wants a quoted count line and under the raising form no run could
   produce one. All four sibling mutants already cited this exact behaviour as
   the measured reason not to raise; this file now matches them.

Topology (binding, C-003 §3 -- added on the same review)
---------------------------------------------------------
The suppression counter increments in whichever process runs the fixture; the
verdict is taken on the controller. Under ``-n`` those are different
processes, so the counters are shipped worker -> controller via
``config.workeroutput`` / ``pytest_testnodedown``. Without that, every xdist
run reported a spurious zero-suppression finding.

Reporting (binding, C-003 §4)
------------------------------
``pytest_terminal_summary`` prints the binding/suppression report so it
appears beside the run's own count line. Every load-bearing quote of a run
under this mutant MUST include this report, not just "ran under the mutant,
still green".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureDef, SubRequest

_TARGET_MODULE = "tests.conftest"
_TARGET_FIXTURE = "_plain_cli_console_seam"

# Module-level mutable state: one pytest session runs one instance of this
# plugin, so plain module globals are session-scoped storage, same shape as
# every other single-file mutant in this mission (C-003).
_bound_at_configure = False
_suppressed_by_site: dict[str, int] = {f"{_TARGET_MODULE}.{_TARGET_FIXTURE}": 0}

# Key under which a worker ships its local counters to the controller. See
# `pytest_sessionfinish` / `pytest_testnodedown` below.
_WORKEROUTPUT_KEY = "disable_render_seam_3115"

# ``pytest_fixture_setup`` is a ``firstresult=True`` hook: pluggy keeps calling
# implementations until one returns a value that is not ``None`` -- returning
# ``None`` reads as "this impl declined", not "the fixture's value is None",
# so it does NOT stop the chain. The real seam legitimately yields ``None``,
# so a neutralising impl that also returns ``None`` is silently skipped over
# and the core implementation runs the REAL fixture body right after it --
# a probed, measured no-op (the earlier draft of this file made exactly this
# mistake: suppressed count was non-zero, the hook clearly ran, yet the run
# stayed green because the real body ran anyway straight afterwards). A
# distinct sentinel object is truthy/non-``None`` and stops the chain; nothing
# reads this fixture's return value (it is consumed only for its autouse
# side effect), so substituting the sentinel for the fixture's real ``None``
# result is unobservable to every caller except this mutant's own cache entry.
_NEUTRALISED_SENTINEL = object()


def pytest_configure() -> None:
    """Assert the seam this mutant intends to patch is still where expected.

    Takes no arguments -- pluggy matches a hookimpl's declared parameters by
    name against the hookspec and only passes the ones actually declared, so
    an unused ``config: pytest.Config`` parameter is neither required nor
    wanted here (and would otherwise be an unused-argument lint finding).

    Fails loudly (rather than silently doing nothing) if ``tests.conftest``
    cannot be imported or no longer defines ``_plain_cli_console_seam`` under
    that name — a renamed or relocated seam must not read as "successfully
    neutralised".
    """
    global _bound_at_configure

    try:
        import tests.conftest as _conftest_module
    except ImportError as exc:  # pragma: no cover - defensive, loud by design
        raise pytest.UsageError(
            f"disable_render_seam_3115: cannot import {_TARGET_MODULE!r} to bind the "
            f"seam it is meant to neutralise ({exc}). This mutant's self-proof "
            "failed at configure time; no test result from this run may be trusted."
        ) from exc

    seam_attr = getattr(_conftest_module, _TARGET_FIXTURE, None)
    if seam_attr is None:
        raise pytest.UsageError(
            f"disable_render_seam_3115: {_TARGET_MODULE}.{_TARGET_FIXTURE} is absent, "
            "renamed or relocated. This mutant's binding assertion failed at "
            "pytest_configure -- nothing was neutralised, and no verdict about the "
            "FR-002 render seam may be drawn from this run."
        )

    _bound_at_configure = True


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef: FixtureDef[Any], request: SubRequest) -> object:
    """Short-circuit the render seam's setup instead of running its body.

    ``pytest_fixture_setup`` is a ``firstresult=True`` hook: the first
    non-``None`` return value wins and the core implementation in
    ``_pytest.fixtures`` (which would otherwise call the real fixture
    generator) is never reached for this fixture request.
    ``tryfirst=True`` asks pluggy to offer this hookimpl before others so the
    short-circuit actually happens rather than losing a call-order race.

    Every OTHER fixture is passed through untouched (returns ``None``, the
    "I did not handle this" signal for a firstresult hook), so this mutant's
    blast radius is exactly the one seam it names -- not every autouse
    fixture in the suite.
    """
    if fixturedef.argname != _TARGET_FIXTURE:
        return None

    site_key = f"{_TARGET_MODULE}.{_TARGET_FIXTURE}"
    _suppressed_by_site[site_key] = _suppressed_by_site.get(site_key, 0) + 1

    # Cache the sentinel under this fixture's current cache key -- same shape
    # ``_pytest.fixtures.pytest_fixture_setup`` uses for a successful run
    # (a ``(value, cache_key, exc_info)`` triple) -- so downstream fixture
    # bookkeeping (cache-hit checks, finalizer scheduling) still works
    # normally. Returning the sentinel (not ``None``) is what actually stops
    # the ``firstresult`` hook chain before it reaches the real fixture body.
    result: object = _NEUTRALISED_SENTINEL
    my_cache_key = fixturedef.cache_key(request)
    fixturedef.cached_result = (result, my_cache_key, None)
    return result


def _format_report() -> list[str]:
    total = sum(_suppressed_by_site.values())
    lines = [
        "disable_render_seam_3115 mutant report (C-003 self-proof):",
        f"  bound at pytest_configure: {_bound_at_configure}",
        f"  per-site suppression split: {_suppressed_by_site!r}",
        f"  total suppressed: {total}",
    ]
    return lines


def pytest_testnodedown(node: Any, error: Any) -> None:  # noqa: ARG001
    """CONTROLLER side of the xdist aggregation -- merge one worker's counters.

    Fires on the controller as each worker shuts down, before the
    controller's own ``pytest_sessionfinish``/``pytest_terminal_summary``, so
    merged totals are in place when the loudness verdict is taken. Absent
    under a serial run, where the local counters are already the whole truth.
    """
    global _bound_at_configure

    workeroutput = getattr(node, "workeroutput", None)
    if not workeroutput:
        return
    payload = workeroutput.get(_WORKEROUTPUT_KEY)
    if not payload:
        return
    _bound_at_configure = bool(_bound_at_configure or payload.get("bound"))
    for site, count in (payload.get("suppressed_by_site") or {}).items():
        _suppressed_by_site[site] = _suppressed_by_site.get(site, 0) + int(count)


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Ship counters (worker), or force a non-zero exit status (controller/serial).

    MEASURED DEFECT #1, fixed here -- raising destroyed the count line
    ----------------------------------------------------------------------
    This hook used to ``raise pytest.UsageError`` on a zero-suppression run.
    ``TerminalReporter.pytest_sessionfinish`` is a ``wrapper=True`` hookimpl,
    so a raise from another implementation of the same hook surfaces at its
    ``yield`` and skips everything after it: ``pytest_terminal_summary``,
    ``summary_failures`` and ``summary_stats``. Measured on a 2-test throwaway
    carrying one real failure:

    ======================  ====  ======================================  =========
    run                     exit  count line                              traceback
    ======================  ====  ======================================  =========
    no plugin                  1  ``1 failed, 1 passed in 0.02s``         present
    with the raise (before)    4  ABSENT (``grep -c`` -> 0)               absent
    with this fix (after)      1  ``1 failed, 1 passed in 0.02s``         present
    ======================  ====  ======================================  =========

    So under the raising form NO run could produce the quoted count line
    NFR-003 requires -- and it destroyed the failure traceback too, which is
    how "read the failure text, not the tally" is meant to be satisfied. All
    four sibling mutants on this mission already cite this exact behaviour as
    the measured reason NOT to raise, and set ``session.exitstatus`` instead;
    this file was the outlier. It now matches them: the process still exits
    non-zero (``wrap_session`` reads ``session.exitstatus`` after every
    ``pytest_sessionfinish`` hook has run), the loud red/bold line still
    prints, and the count line survives.

    MEASURED DEFECT #2, fixed here -- the xdist controller/worker state split
    -------------------------------------------------------------------------
    ``pytest_fixture_setup`` fires, and so ``_suppressed_by_site`` increments,
    only in the worker that owns the item; the verdict is taken only on the
    controller, whose counters are permanently 0. Uncorrected, every ``-n``
    run reports a spurious zero-suppression finding. A worker's
    ``session.exitstatus`` mutation is discarded by xdist, so the counters
    themselves must travel: ``config.workeroutput`` exists on workers ONLY
    (its absence is how this hook tells the topologies apart) and is exposed
    to the controller as ``node.workeroutput`` in ``pytest_testnodedown``.
    """
    workeroutput = getattr(session.config, "workeroutput", None)
    if workeroutput is not None:
        # WORKER: ship local counters upward; do not judge on a partial shard.
        workeroutput[_WORKEROUTPUT_KEY] = {
            "bound": bool(_bound_at_configure),
            "suppressed_by_site": dict(_suppressed_by_site),
        }
        return

    # CONTROLLER (totals merged by pytest_testnodedown) or serial run.
    if sum(_suppressed_by_site.values()) == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:  # noqa: ARG001
    """Print the per-site split, and a loud red line if it is zero.

    Writes rather than raises -- see :func:`pytest_sessionfinish` for the
    measured table showing that a raise from either hook destroys the count
    line and the failure traceback. Skipped on xdist workers, whose local
    counters describe only their own shard and whose terminal summary xdist
    does not surface anyway.
    """
    if getattr(config, "workeroutput", None) is not None:
        return

    for line in _format_report():
        terminalreporter.write_line(line)

    if sum(_suppressed_by_site.values()) > 0:
        return

    terminalreporter.write_line(
        "[disable_render_seam_3115] NO VERDICT: suppressed count is 0 -- the render "
        "seam was never invoked during this session. This run proves nothing about "
        "the FR-002 seam (no fixture request reached it), and no verdict may be "
        "drawn from it (C-003 self-proof requirement).",
        red=True,
        bold=True,
    )
