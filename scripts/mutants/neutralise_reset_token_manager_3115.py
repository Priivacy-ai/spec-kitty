"""Mutant: neutralise FR-009's ``reset_token_manager()`` hardening at hook level
(C-003, FR-009, #3030 / #3115).

`578a659162` / `4f8e4ca781` added a process-wide ``TokenManager`` singleton reset
to five ``#3030`` CLI test files as **self-declared unproven hardening** ("Could
not force a live reproduction of the reported empty-journal CI failure locally
... this is defensive hardening of a credible process-global per the
maintainer's lead, not a confirmed-necessary fix"). The width finding (WP02,
approved) gives a strong prior that the reset was aimed at a global that was
never the CLI cause -- but a prior is not a measurement. This mutant makes the
claim cheap to test in both directions: with it loaded, ``reset_token_manager()``
is replaced by a no-op at every one of the five call sites it can reach, so a
run under this mutant answers "does removing the reset change the outcome?"
directly, rather than by argument.

Loading (binding, C-003 §1 -- corrected contract)
----------------------------------------------------
    PYTHONPATH=scripts/mutants:$WT/src <venv>/bin/python -m pytest \\
        -p neutralise_reset_token_manager_3115 \\
        tests/cli/commands/test_sync_status_per_project_3030.py

``PYTHONPATH`` alone loads nothing: it only makes this module *importable*.
Pytest does not import every importable module on ``sys.path`` as a plugin --
only ones it is told to load. Without ``-p`` (or ``PYTEST_PLUGINS=...``) this
file is never imported, never binds, and the run reads as a passing gate while
mutating nothing. The ``-p`` flag is therefore load-bearing and MUST be quoted
in any evidence taken under this mutant (mirrors ``disable_render_seam_3115``
and ``nonterminating_dispatch_3115``, both approved precedents on this
mission).

Neutralisation site (binding, C-003 §2)
-------------------------------------------
Hook level, in ``pytest_configure`` -- **never** a same-named fixture. All five
``578a659162`` files import ``reset_token_manager`` **function-locally, inside
the fixture body, from the defining module** ``specify_cli.auth.manager``
(measured: ``test_sync_doctor_per_project_3030.py:62``,
``test_sync_status_per_project_3030.py:73``,
``test_sync_migrate_backfills_h4.py:57``, ``test_sync_purge_3030.py:83``,
``test_sync_doctor_consent_health_3030.py:70``), so this module patches the
**production attribute** ``specify_cli.auth.manager.reset_token_manager``
directly at ``pytest_configure`` -- before any fixture body runs -- rather than
shadowing a fixture. Each fixture's function-local ``from
specify_cli.auth.manager import reset_token_manager`` re-resolves the name off
the module *at call time* (one ``IMPORT_FROM`` + ``STORE_FAST`` per fixture
invocation, same fact ``nonterminating_dispatch_3115`` verified with ``dis``
for its own function-local import), so it picks up whichever object the module
attribute holds at the moment the fixture runs -- which, once
``pytest_configure`` has replaced it, is this mutant's no-op.

This is deliberately **not** the ``pytest_fixture_setup``-interception shape
``disable_render_seam_3115`` uses: that mutant neutralises a named *fixture*
(``tests.conftest._plain_cli_console_seam``), where a same-named plugin
fixture would lose to the conftest fixture for items under that conftest's
directory. There is no fixture named ``reset_token_manager`` to collide with --
it is a plain function imported and called inline -- so patching the
**production module attribute it is imported from** is both sufficient and the
correct site, the same shape ``nonterminating_dispatch_3115`` uses for
``specify_cli.delivery.dispatcher.dispatch``.

Per-site split (binding, C-003 §3 -- mandatory, shape already measured)
----------------------------------------------------------------------------
A single aggregate suppressed count cannot distinguish "all five mutated" from
"one mutated, four inert" (the mission's fifth rot mode). Every call this
mutant intercepts is attributed to its caller's frame -- the fixture body that
invoked ``reset_token_manager()`` -- by that frame's source file basename, and
counted **per site** against the five known basenames:

    test_sync_doctor_per_project_3030.py
    test_sync_status_per_project_3030.py
    test_sync_migrate_backfills_h4.py
    test_sync_purge_3030.py
    test_sync_doctor_consent_health_3030.py

Two other sites bind ``reset_token_manager`` **eagerly by value** at module
import, via the package name rather than the defining module --
``tests/auth/integration/conftest.py:22`` and
``tests/auth/test_websocket_provisioning.py:28``, both
``from specify_cli.auth import reset_token_manager``. ``specify_cli/auth/__init__.py:44``
re-exports the symbol with the same shape
(``from .manager import get_token_manager, reset_token_manager``), which binds
a **name in the ``specify_cli.auth`` package's own namespace** to whatever
object ``specify_cli.auth.manager.reset_token_manager`` held at the moment
``specify_cli.auth`` was first imported -- not a live reference to the
submodule attribute this mutant patches. Patching
``specify_cli.auth.manager.reset_token_manager`` therefore does **not** reach
either of those two sites (the fifth rot mode named in the mission's own
standing rules: "``from X import f`` rebinds by value"). They are **outside
this WP's cone** (``tests/auth/**`` is "nobody's" per the WP brief) and are
**deliberately left unpatched** -- this mutant's report names them explicitly,
by path, and never folds them into the numeric split as a zero, which would
misreport "attempted and inert" where the truth is "never attempted."

Self-proof (binding, C-003 §3)
-----------------------------------
1. **Binding assertion.** ``pytest_configure`` imports
   ``specify_cli.auth.manager`` and asserts ``reset_token_manager`` is present
   under that exact name and callable. Absent, renamed or relocated -> loud
   failure (``pytest.UsageError``) before the session runs; no test result
   from this run may be trusted (mirrors both precedents' configure-time
   contract).
2. **Per-site split, reported by name.** See above; the report distinguishes
   the five patched sites from the two named-but-deliberately-unpatched ones,
   never conflating them.
3. **Loud failure on zero suppressions.** If the sum of the five per-site
   counts is zero at session end, that is a finding about the mutant (wrong
   node-ids selected, binding failed silently, or the patched attribute was
   genuinely unreached this session), never a finding about the reset under
   test, and no verdict may be drawn from such a run (C-003, standing-rules.md
   rot-mode #4). Reported via a forced non-zero ``session.exitstatus`` plus a
   bold/red terminal line rather than a raise from ``pytest_sessionfinish`` --
   ``nonterminating_dispatch_3115`` measured that raising from that hook (or
   from the ``pytest_terminal_summary`` its own sessionfinish sibling is
   called from) propagates as an uncaught traceback that pre-empts
   ``TerminalReporter.summary_stats()``, destroying the final ``N
   passed/failed in Ys`` count line -- exactly the evidence NFR-003 says is
   load-bearing, for exactly the run meant to prove there is none. The same
   non-raising shape is used here for the same measured reason.

Reporting (binding, C-003 §4)
----------------------------------
``pytest_terminal_summary`` prints the per-site suppression split (five named
sites plus the two deliberately-unpatched ones, by path) so it can be quoted
beside the run's own count line and collected count. Every load-bearing quote
of a run under this mutant MUST include this report, not just "ran under the
mutant, still green" or "still red."

What the replacement does, and why
---------------------------------------
The real ``reset_token_manager`` (``src/specify_cli/auth/manager.py:34-41``)
does exactly one thing: ``global _tm; with _tm_lock: _tm = None`` -- drop the
cached singleton so the next ``get_token_manager()`` call constructs a fresh
one. This mutant's replacement does **nothing at all**: it does not touch
``_tm``, does not acquire ``_tm_lock``, and returns ``None`` (matching the real
function's return annotation) after recording the call for the per-site
report. Whatever ``TokenManager`` instance a prior test in the same worker
process left cached therefore survives, untouched, into whichever of the five
``578a659162`` files' tests run next in that process -- which is exactly the
leak the original hardening's docstring describes as its threat model. If that
threat model is real, a discriminating case turns red under this mutant; if it
does not, that is the measurement, not an assumption.

Known limits of the per-site attribution (noted, not currently load-bearing)
----------------------------------------------------------------------------
The per-site split keys on the caller's frame filename by **basename only**
(see ``_neutralised_reset_token_manager``), so two same-named test files in
different directories would conflate into one bucket. None of this mission's
five sites collide by basename with anything else in the tree today. The
per-site counters are also plain module-level globals, scoped to one plugin
instance in one interpreter process: under ``xdist`` each worker loads its
own copy of this plugin and prints its own report independently, with no
cross-worker aggregation. Neither limit bites the measurements this WP took
(single-process, no ``-n``/``--dist``, per C-004), and both are recorded here
so a future user of this plugin under a different invocation shape does not
inherit them silently.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

_TARGET_MODULE = "specify_cli.auth.manager"
_TARGET_SYMBOL = "reset_token_manager"

# BOTH module names the symbol is reachable by, patched in this order.
#
# CORRECTED ON A PRE-MERGE REVIEW. This mutant used to patch only the defining
# module, `specify_cli.auth.manager`. But `src/specify_cli/auth/__init__.py:44`
# does `from .manager import get_token_manager, reset_token_manager` at package
# scope, re-exporting the name by value -- and `reset_token_manager` is in that
# package's `__all__` (`__init__.py:51`), i.e. it is the DOCUMENTED public way
# to reach the symbol. A census of the whole tree found 12 in-process bindings
# that go through the re-export against only 5 that go through the defining
# module: patching one module was patching the minority. This is C-003's fifth
# rot mode ("`from X import f` rebinds by value") landing in the very file that
# quotes it.
_PATCHED_MODULES: tuple[str, ...] = ("specify_cli.auth.manager", "specify_cli.auth")

# Files whose calls this mutant's patch reaches, keyed by basename (the
# attribution key `_neutralised_reset_token_manager` derives from its caller's
# frame). Split by WHICH module name each one resolves the symbol through.
#
# (a) Function-local `from specify_cli.auth.manager import reset_token_manager`
#     inside an autouse fixture -- re-resolved per call off the DEFINING module.
_PATCHED_SITES_VIA_MANAGER: tuple[str, ...] = (
    "test_sync_doctor_per_project_3030.py",
    "test_sync_status_per_project_3030.py",
    "test_sync_migrate_backfills_h4.py",
    "test_sync_purge_3030.py",
    "test_sync_doctor_consent_health_3030.py",
)

# (b) Reachable ONLY because this mutant now also patches the re-export.
#     Every one of these was silently repairing the mutation before the fix.
#
#     The three `tests/cli/commands/test_auth_*.py` files sit in the SAME
#     directory as the five above and each drives an autouse fixture that
#     performs a real reset on setup AND teardown -- so a green under the old
#     one-module patch was not evidence that the reset is inert, which is the
#     FR-009 claim this mutant exists to support. They bind at MODULE scope,
#     but a test module is imported during COLLECTION, which is after
#     `pytest_configure` has already installed the patch, so the by-value bind
#     captures the neutralised function.
#
#     `test_device_code_flow.py` binds function-locally off the re-export
#     (`:824`, `:865`) -- re-resolved per call, so also reached.
_PATCHED_SITES_VIA_REEXPORT: tuple[str, ...] = (
    "test_auth_login.py",  # tests/cli/commands/test_auth_login.py:29, autouse _reset_tm
    "test_auth_logout.py",  # tests/cli/commands/test_auth_logout.py:29, autouse _isolate
    "test_auth_status.py",  # tests/cli/commands/test_auth_status.py:35, autouse _isolate
    "test_factory.py",  # tests/auth/test_factory.py:10, autouse _reset_tm
    "test_http_transport.py",  # tests/auth/test_http_transport.py:24, fixture (not autouse)
    "test_websocket_provisioning.py",  # tests/auth/test_websocket_provisioning.py:28, fixture
    "test_single_flight_refresh.py",  # tests/auth/concurrency/...:30, autouse _clean_factory
    "test_refresh_through_transport.py",  # tests/auth/integration/...:34, autouse _isolate
    "test_device_code_flow.py",  # tests/auth/test_device_code_flow.py:824,865, function-local
)

_PATCHED_SITES: tuple[str, ...] = _PATCHED_SITES_VIA_MANAGER + _PATCHED_SITES_VIA_REEXPORT

# Named, never counted as zero (C-003: "patched 3 of 7 call sites" is a
# finding; "patched" is not). These are the bindings the census found that
# this mutant still does NOT reach, each with the reason.
_DELIBERATELY_UNPATCHED_SITES: tuple[str, ...] = (
    # INITIAL conftests: pytest imports the conftest.py files covering the
    # initial argument paths during pre-parse, which is BEFORE pytest_configure
    # -- so these eager module-scope binds capture the ORIGINAL function and no
    # hook-level patch can reach them. This is the one shape that is genuinely
    # unreachable from a plugin, and it is why these are declared rather than
    # counted.
    "tests/auth/conftest.py:7 (eager module-scope, initial-conftest: imported before pytest_configure)",
    "tests/auth/integration/conftest.py:22 (eager module-scope, initial-conftest: imported before pytest_configure)",
    # Separate interpreters: these live inside textwrap.dedent(...) source
    # strings executed by spawned subprocesses that load no pytest plugin at
    # all, so no in-process patch is even applicable.
    "tests/auth/concurrency/test_incident_regression.py:79-80 (subprocess source string, _WORKER_A_SCRIPT)",
    "tests/auth/concurrency/test_incident_regression.py:125-126 (subprocess source string, _WORKER_B_SCRIPT)",
)

# Key under which a worker ships its local counters to the controller.
_WORKEROUTPUT_KEY = "neutralise_reset_token_manager_3115"

_state: dict[str, Any] = {"bound": False, "original": None}
_bound_modules: dict[str, bool] = dict.fromkeys(_PATCHED_MODULES, False)
_suppressed_by_site: dict[str, int] = dict.fromkeys(_PATCHED_SITES, 0)
_suppressed_other: dict[str, int] = {}


def _neutralised_reset_token_manager(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
    """Stand-in for the real reset: records the call, touches nothing.

    Attributes the call to its caller's source file (the fixture body that
    invoked ``reset_token_manager()``) so the per-site split can distinguish
    which of the five patched sites actually exercised the patch this
    session, per C-003's fifth-rot-mode rule ("a single aggregate count
    cannot distinguish 'both sites mutated' from 'one mutated, one inert'").

    The permissive ``*args, **kwargs`` signature is deliberate, not
    laziness: the real ``reset_token_manager()`` takes no arguments today,
    but a bare ``def _neutralised_reset_token_manager() -> None`` would turn
    any future signature change on the real function into a ``TypeError``
    red under this mutant -- a red that satisfies nothing (NFR-007) and
    would misreport as "the reset is load-bearing" when the actual finding
    is "the mutant's stand-in is stale." Accepting and discarding whatever
    arguments arrive keeps a signature drift from being conflated with a
    genuine discriminating result.
    """
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    caller_name = "<unknown>"
    if caller is not None:
        caller_path = caller.f_code.co_filename
        caller_name = caller_path.rsplit("/", 1)[-1]

    if caller_name in _suppressed_by_site:
        _suppressed_by_site[caller_name] += 1
    else:
        _suppressed_other[caller_name] = _suppressed_other.get(caller_name, 0) + 1
    return None


def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001 -- pytest hook signature
    """Bind at hook level (C-003 §2) and assert the binding took (C-003 §3.1).

    Patches EVERY module name the symbol is reachable by -- both the defining
    module and the package re-export -- per C-003's fifth rot mode. Patching
    only the definer left the documented public name
    (`specify_cli.auth.reset_token_manager`, in that package's `__all__`)
    holding the original function, and the census found more bindings going
    through the re-export than through the definer.
    """
    import importlib

    for module_name in _PATCHED_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:  # pragma: no cover - defensive, loud by design
            raise pytest.UsageError(
                f"neutralise_reset_token_manager_3115: cannot import {module_name!r} "
                f"to bind the symbol it is meant to neutralise ({exc}). This mutant's "
                "self-proof failed at configure time; no test result from this run may "
                "be trusted."
            ) from exc

        original = getattr(module, _TARGET_SYMBOL, None)
        if original is None or not callable(original):
            raise pytest.UsageError(
                f"neutralise_reset_token_manager_3115: {module_name}.{_TARGET_SYMBOL} "
                "is absent, renamed, relocated, or not callable. This mutant's binding "
                "assertion failed at pytest_configure -- nothing was neutralised, and "
                "no verdict about FR-009's reset may be drawn from this run."
            )

        if module_name == _TARGET_MODULE:
            _state["original"] = original
        setattr(module, _TARGET_SYMBOL, _neutralised_reset_token_manager)
        bound_here = getattr(module, _TARGET_SYMBOL) is _neutralised_reset_token_manager
        _bound_modules[module_name] = bound_here
        if not bound_here:  # pragma: no cover - defensive, loud by design
            raise pytest.UsageError(
                f"neutralise_reset_token_manager_3115: FAILED TO BIND at "
                f"{module_name}.{_TARGET_SYMBOL} -- attribute assignment did not "
                "stick. This is a finding about the mutant, not about the code under "
                "test; no verdict may be drawn from this run (C-003 self-proof "
                "requirement)."
            )

    _state["bound"] = all(_bound_modules.values())
    print(
        f"\n[neutralise_reset_token_manager_3115] BOUND at {len(_PATCHED_MODULES)} module "
        f"names: {list(_PATCHED_MODULES)!r} "
        f"({len(_PATCHED_SITES_VIA_MANAGER)} site(s) reachable via the defining module, "
        f"{len(_PATCHED_SITES_VIA_REEXPORT)} via the re-export; "
        f"{len(_DELIBERATELY_UNPATCHED_SITES)} declared unreachable -- see module docstring)."
    )


def _format_report() -> list[str]:
    total_patched = sum(_suppressed_by_site.values())
    via_manager = {s: _suppressed_by_site.get(s, 0) for s in _PATCHED_SITES_VIA_MANAGER}
    via_reexport = {s: _suppressed_by_site.get(s, 0) for s in _PATCHED_SITES_VIA_REEXPORT}
    lines = [
        "neutralise_reset_token_manager_3115 mutant report (C-003 self-proof):",
        f"  bound at pytest_configure, per module name: {_bound_modules!r}",
        f"  per-site split via the DEFINING module ({_TARGET_MODULE}): {via_manager!r}",
        f"    subtotal: {sum(via_manager.values())}",
        f"  per-site split via the RE-EXPORT (specify_cli.auth): {via_reexport!r}",
        f"    subtotal: {sum(via_reexport.values())}",
        f"  total suppressed (all {len(_PATCHED_SITES)} declared sites): {total_patched}",
    ]
    if _suppressed_other:
        lines.append(f"  suppressed at sites not in the declared inventory: {_suppressed_other!r}")
    lines.append(
        "  deliberately unpatched (named, never counted as zero): "
        f"{list(_DELIBERATELY_UNPATCHED_SITES)!r}"
    )
    return lines


def pytest_testnodedown(node: Any, error: Any) -> None:  # noqa: ARG001
    """CONTROLLER side of the xdist aggregation -- merge one worker's counters.

    Fires on the controller as each worker shuts down, before the controller's
    own ``pytest_sessionfinish``/``pytest_terminal_summary``. Absent in a
    serial run, where the local counters are already the whole truth.
    """
    workeroutput = getattr(node, "workeroutput", None)
    if not workeroutput:
        return
    payload = workeroutput.get(_WORKEROUTPUT_KEY)
    if not payload:
        return
    for module_name, was_bound in (payload.get("bound_modules") or {}).items():
        _bound_modules[module_name] = bool(_bound_modules.get(module_name) or was_bound)
    _state["bound"] = all(_bound_modules.values())
    for site, count in (payload.get("suppressed_by_site") or {}).items():
        _suppressed_by_site[site] = _suppressed_by_site.get(site, 0) + int(count)
    for site, count in (payload.get("suppressed_other") or {}).items():
        _suppressed_other[site] = _suppressed_other.get(site, 0) + int(count)


def pytest_sessionfinish(session: pytest.Session) -> None:  # noqa: ARG001
    """Ship counters (worker), or force a non-zero exit status (controller/serial).

    MEASURED DEFECT, fixed here -- the xdist controller/worker state split
    ----------------------------------------------------------------------
    ``_neutralised_reset_token_manager`` runs, and so ``_suppressed_by_site``
    increments, ONLY inside the worker that owns the test. This verdict, and
    ``pytest_terminal_summary``, run ONLY on the controller, whose counters are
    permanently 0 because no test executes there. Uncorrected, EVERY ``-n`` run
    printed ``NO VERDICT: ... suppressed ZERO calls`` and forced exit 1 --
    including runs that manifestly did reach the patched symbol. Measured with
    a known-answer control: a selection whose reaching test calls the patched
    name gave ``3 passed`` + exit 0 serially, and ``3 passed`` + exit 1 with
    the spurious NO VERDICT under ``-n 2``, byte-identical to the genuine
    non-arrival run -- so the guard could not discriminate at all under xdist.

    A worker's ``session.exitstatus`` mutation is discarded by xdist, so the
    counters must travel instead. ``config.workeroutput`` exists on workers
    only (its absence is how this hook tells the topologies apart) and reaches
    the controller as ``node.workeroutput`` in ``pytest_testnodedown``.

    Deliberately does not raise -- see ``nonterminating_dispatch_3115``'s
    docstring for the measured reason: a raise from this hook (or from
    ``pytest_terminal_summary``) propagates as an uncaught traceback that
    pre-empts ``TerminalReporter.summary_stats()`` and destroys the final
    count line, which would defeat NFR-003's "the count line is the evidence"
    rule for exactly the run meant to prove there is no evidence.
    """
    workeroutput = getattr(session.config, "workeroutput", None)
    if workeroutput is not None:
        # WORKER: ship local counters upward; do not judge on a partial shard.
        workeroutput[_WORKEROUTPUT_KEY] = {
            "bound_modules": dict(_bound_modules),
            "suppressed_by_site": dict(_suppressed_by_site),
            "suppressed_other": dict(_suppressed_other),
        }
        return

    # CONTROLLER (totals merged by pytest_testnodedown) or serial run.
    total_patched = sum(_suppressed_by_site.values())
    if not _state["bound"] or total_patched == 0:
        session.exitstatus = 1


def pytest_terminal_summary(
    terminalreporter: Any, exitstatus: int, config: pytest.Config  # noqa: ARG001
) -> None:
    """Print the per-site suppression split; write loudly if it is zero.

    Skipped on xdist workers, whose counters cover only their own shard and
    whose terminal summary xdist does not surface anyway.
    """
    if getattr(config, "workeroutput", None) is not None:
        return

    for line in _format_report():
        terminalreporter.write_line(line)

    total_patched = sum(_suppressed_by_site.values())
    if _state["bound"] and total_patched:
        return

    if not _state["bound"]:  # pragma: no cover - defensive, loud by design
        message = (
            "[neutralise_reset_token_manager_3115] NO VERDICT: FAILED TO BIND at "
            f"{_TARGET_MODULE}.{_TARGET_SYMBOL} -- see the pytest_configure "
            "failure. This is a finding about the mutant, not about the code "
            "under test."
        )
    else:
        message = (
            "[neutralise_reset_token_manager_3115] NO VERDICT: bound at "
            f"{list(_PATCHED_MODULES)!r} but suppressed ZERO calls across "
            f"the {len(_PATCHED_SITES)} declared sites this session. A zero-suppressed-count run is a "
            "finding about the mutant (wrong node-ids selected, or the patched "
            "symbol genuinely unreached), not about the reset under test -- no "
            "verdict may be drawn from it (C-003 self-proof requirement, "
            "spec.md C-003 / standing-rules.md rot-mode #4)."
        )
    terminalreporter.write_line(message, red=True, bold=True)
