"""FR-007 sync-cone leak-guard detection layer (#3115).

Extracted from ``tests/sync/conftest.py`` (landing-fold cohesion refactor,
PR #3144) -- a pure, hook-independent move with **zero logic, threshold,
string, or control-flow change**. This module holds the watched-global /
watched-env registries, the pinned-known-leaks allowlist (#3130), the
snapshot/diff/fingerprint primitives, and the strict per-pin evaluator.

The pytest HOOKS that drive this detection layer
(``pytest_runtest_setup``, ``pytest_runtest_teardown``,
``pytest_terminal_summary``) stay in ``tests/sync/conftest.py`` --  pytest
only discovers hook implementations in a ``conftest.py``, not in an
arbitrary module -- and import everything they need from here. See that
file's own hook docstrings for why the guard is a hookwrapper and not a
fixture, and for the "fail the polluter, not the victim" design.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import threading
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# FR-007 -- the sync-cone leak guard (#3115, WP05)
#
# Autouse guard: snapshots the module-level mutable globals and the
# live-thread set that WP04's inventory
# (docs/development/process-global-inventory-3115.md) marks reachable, then
# fails the test whose run leaves any of them different from how it found
# them -- naming the symbol (or the thread's name and target) and the
# node-id. Scoped to WP04's inventory, not to WP06's attribution, so it
# ships whether or not the sync-half attribution ever converges (H4).
#
# It detects and fails. It does NOT repair -- see
# ``pytest_runtest_teardown``'s own docstring below for why restoring
# would silence the pins this guard exists to protect.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _WatchedGlobal:
    """One process-global entry this guard watches, traced to its inventory row."""

    inventory_id: str
    module_path: str
    attr_path: str
    description: str


# The two canonical sync singletons -- WP04 inventory E26/E27. Each has a
# named reset seam (``reset_runtime`` / ``reset_sync_service``) that several
# cone tests bypass via direct attribute mutation with their own local
# try/finally restore (see the inventory rows). Watched here as the
# backstop for a bypass site that omits the restore.
_WATCHED_SINGLETONS: tuple[_WatchedGlobal, ...] = (
    _WatchedGlobal("E26", "specify_cli.sync.runtime", "_runtime", "canonical SyncRuntime singleton"),
    _WatchedGlobal("E27", "specify_cli.sync.background", "_service", "canonical BackgroundSyncService singleton"),
)

# WP04 carry-forward (notes/inventory-carry-forward.md): a scope decision,
# recorded deliberately rather than left silent. `LEVEL_RESOLVERS` sits on
# `test_429`'s chokepoint path, squarely inside FR-006's own definition
# (module-level mutable, worker-process lifetime), but it lives in `src/`
# and the inventory found nothing in the cone that mutates it -- so it is
# absent from the 53-entry inventory proper. Watching it is a single cheap
# dict-fingerprint check, and the carry-forward note calls it "defensible" --
# extended here as a deliberate, documented addition, not an inventory entry.
_WATCHED_CARRY_FORWARD: tuple[_WatchedGlobal, ...] = (
    _WatchedGlobal(
        "carry-forward:LEVEL_RESOLVERS",
        "specify_cli.sync.consent",
        "LEVEL_RESOLVERS",
        "consent precedence dispatch table (WP04 carry-forward, deliberately watched though not an inventory row)",
    ),
)

# Mutable-container / import-time-bound-path test-fixture data -- WP04
# inventory E28-E41. Every one of these was verified by WP04 to be confined
# to exactly one file with zero in-place mutation call sites today; watched
# here so a *future* mutation is caught rather than trusted to stay absent.
_WATCHED_FIXTURE_DATA: tuple[_WatchedGlobal, ...] = (
    _WatchedGlobal("E28", "tests.sync.test_consent_field_fault_3030", "_UNUSABLE_ENABLED", "fixture data list"),
    _WatchedGlobal("E29", "tests.sync.test_consent_field_fault_3030", "_UNUSABLE_UUID", "fixture data list"),
    _WatchedGlobal("E30", "tests.sync.test_consent_write_refusal_3030", "_WRITER_IDS", "fixture data list"),
    _WatchedGlobal("E31", "tests.sync.test_daemon_intent_gate", "ALLOWED_CALL_SITES", "fixture data set"),
    _WatchedGlobal("E32", "tests.sync.test_event_emission", "_DONE_EVIDENCE", "fixture data dict"),
    _WatchedGlobal("E33", "tests.sync.test_history_import_pipeline", "_LEGACY_WP_SPECS", "fixture data list"),
    _WatchedGlobal("E34", "tests.sync.test_history_import_pipeline", "_PREFIXED_WP_SPECS", "fixture data list"),
    _WatchedGlobal("E35", "tests.sync.test_history_import_scan", "_LEGACY_WP_SPECS", "fixture data list"),
    _WatchedGlobal("E36", "tests.sync.test_history_import_scan", "_PREFIXED_WP_SPECS", "fixture data list"),
    _WatchedGlobal("E37", "tests.sync.test_mission_created_payload_parity", "_FACTS", "fixture data dict"),
    _WatchedGlobal("E38", "tests.sync.tracker.test_origin_consumer", "_DUMMY_META", "fixture data dict"),
    _WatchedGlobal("E39", "tests.sync.tracker.test_saas_client_consent_gate_3030", "_IDENTITY_PAYLOAD", "fixture data dict"),
    _WatchedGlobal("E40", "tests.sync.tracker.test_saas_client_consent_gate_3030", "ENDPOINT_CALLS", "fixture data dict of lambdas"),
    _WatchedGlobal("E41", "tests.sync.tracker.test_saas_client_discovery", "PROJECT_IDENTITY", "fixture data dict"),
)

_WATCHED_GLOBALS: tuple[_WatchedGlobal, ...] = _WATCHED_SINGLETONS + _WATCHED_CARRY_FORWARD + _WATCHED_FIXTURE_DATA

# Raw ``os.environ[...] =`` writes with no ``monkeypatch`` teardown -- WP04
# inventory E51 (test_target_authority.py) and E52
# (test_target_authority_wiring.py) write the same key, so one watch covers
# both rows.
_WATCHED_ENV_KEYS: tuple[tuple[str, str], ...] = (
    ("E51/E52", "SPEC_KITTY_SAAS_URL"),
)

# WP04 inventory entries this guard deliberately does NOT watch, and why.
# Reported every session by ``pytest_terminal_summary`` (H8 / NFR-008) so the
# gap is stated, not silently accepted.
_UNWATCHED_ENTRIES: tuple[tuple[str, str], ...] = (
    (
        "E15, E16",
        "not reachable -- frozen str constants (E15) / function-local variables that "
        "structurally cannot be promoted to a module global (E16); nothing to snapshot",
    ),
    (
        "E17, E18, E19",
        "module-singleton CliRunner() instances reused by design across their own "
        "file's tests; there is no 'clean' baseline to diff against, and the "
        "inventory records 'does not depend' for all three",
    ),
    (
        "E20, E21, E22",
        "conftest.py's own autouse reset-seam providers (monkeypatch.setattr / "
        "monkeypatch.delenv); pytest's own monkeypatch teardown already guarantees "
        "their restoration every test -- they ARE the reset mechanism, not the "
        "state this guard protects",
    ),
    (
        "E42-E50",
        "not reachable -- import-time-bound Path/str values resolved once at "
        "import time (Path(__file__).resolve() and friends) and never reassigned; "
        "a leak here is structurally impossible, only a rename/move is "
        "representable, which the rot control below would catch if these were "
        "added to the watch list",
    ),
    (
        "carry-forward:machine-global-consent-index",
        "written 94 times across 15 tests/sync/ files via set_project_consent() "
        "(consent.py:447-451), but its lifetime is the MACHINE "
        "(a SPEC_KITTY_HOME-scoped file on disk), not the worker process -- "
        "outside FR-006's own process-global definition and outside what an "
        "in-process snapshot guard can observe at all. WP04's carry-forward note "
        "names this as a scope question, not a defect; the deliberate decision "
        "here is NOT to extend this in-process guard to disk-resident, "
        "machine-lifetime state -- that would need a different mechanism "
        "(e.g. a SPEC_KITTY_HOME-scoped fixture-level assertion), not a bigger "
        "snapshot dict",
    ),
)


# ---------------------------------------------------------------------------
# FR-007 pinned-known-leaks allowlist (#3130) -- operator decision, WP05
# review round 2.
#
# **This is a pin on KNOWN, ALREADY-FILED defects, not a permanent
# exemption.** Each entry names one node-id this guard has proven leaks a
# specific symbol or thread, cross-referenced to issue #3130 (filed against
# the 12 files these node-ids live in -- none of which any work package on
# this mission owns, so the fix belongs to #3130's own follow-up, not here).
# Removing an entry -- because the underlying leak was actually fixed -- is
# how that fix gets proven: see the strictness rule below. Adding an entry
# for a leak that has not been independently verified is not permitted by
# this mechanism's own design (an unverified pin would silently defeat the
# guard's purpose, which is exactly what C-011's strict-xfail discipline
# this pin borrows its reasoning from exists to prevent).
#
# **Why this is a bespoke allowlist check inside the guard, not
# ``pytest.mark.xfail`` on the 12 test functions.** Two independent reasons:
# (1) none of the 12 files are owned by this WP -- editing them (even to add
# a marker) would be the exact ownership violation C-007 exists to prevent,
# and the pins must therefore live entirely in ``tests/sync/conftest.py``,
# which this WP does own. (2) Measured, not assumed, during WP05's first
# review round: ``xfail`` governs the *call*-phase outcome, and this guard's
# failure is raised from ``pytest_runtest_teardown`` -- a *teardown*-phase
# failure. A test marked ``xfail(strict=True)`` whose call phase raises
# nothing (all 12 of these tests pass their own assertions; only this
# guard's own teardown check reds) is reported ``XPASS``, which
# ``strict=True`` then turns into ITS OWN hard failure -- two failure
# reports for one test, not the silent-accept this pin needs. So the
# allowlist lives beside the check it exempts, and reproduces the strictness
# property ``xfail(strict=True)`` provides -- "quietly accepted while it
# still reproduces; loudly fails if it stops" -- by direct comparison
# against what was actually observed, not by delegating to a mechanism that
# cannot see a teardown-phase failure in the first place. See the both-
# directions proof in the WP05 transition note / final report.
@dataclass(frozen=True)
class _MarkerBaseline:
    """Per-marker ``requires_clean_baseline`` for one marker of a ``_PinnedLeak``.

    ``baseline_watch`` names the one snapshot slot to read (same resolution
    rule as ``_PinnedLeak.baseline_watch``: an env-key label or a watched-
    global's ``inventory_id``). ``unobservable_when`` is ``"clean"`` or
    ``"dirty"`` -- the ``before`` state of that slot under which THIS
    marker's absence from ``dirty`` is unobservable rather than evidence of
    a fix. See ``_PinnedLeak``'s own docstring for why the polarity is not
    assumed to match the whole-pin case.
    """

    baseline_watch: str
    unobservable_when: str  # "clean" or "dirty"


@dataclass(frozen=True)
class _PinnedLeak:
    """One #3130-filed, guard-proven leak, pinned at its exact node-id.

    ``markers`` are substrings, each expected to be contained in at least
    one of the dirty lines this node-id produces; a dirty line matching
    none of them is treated as a NEW, unpinned leak (fails loudly, same as
    an unlisted node). Chosen to be stable across runs -- thread ``ident``
    and the auto-incrementing ``Thread-N`` name are process-specific and
    deliberately NOT part of any marker; the function/mock name a thread's
    ``target`` resolves to, or the watched entry's inventory id, is.

    **Named residual, not fixed here** (round-3 review): markers are bare
    substrings, so ``"target=None"`` matches ANY anonymous leaked thread on
    the node it is pinned for. If one of the four nodes pinned with
    ``"target=None"`` develops a second, genuinely different anonymous-
    thread leak, this mechanism absorbs it into the existing pin rather
    than flagging it as new. A precise fix (e.g. requiring an exact COUNT
    of matching lines, or a per-marker cardinality) was judged out of
    proportion for a pin registry whose entries are meant to shrink, not
    grow a more elaborate matching language. Left as a stated limitation.

    ``requires_clean_baseline`` (round-4 review, operator decision): a
    handful of leaks are observable ONLY from a worker whose ``before``
    snapshot for the specific watched entry was already clean --
    ``test_target_authority_wiring.py``'s pin is the first instance
    (``SPEC_KITTY_SAAS_URL`` inherited-dirty from
    ``test_target_authority.py`` in a serial run masks it; a fresh
    ``--dist loadfile`` worker reveals it). For such a pin, ``dirty ==
    []`` is ambiguous by itself -- it means either "fixed" or "the exact
    entry this pin watches was already dirty when this test started, so
    nothing NEW could show up even though the leak still fires". The
    guard resolves the ambiguity by reading the SAME ``before`` snapshot
    it already captured (see ``_pin_baseline_was_already_dirty`` below),
    not by approximating it from ``dirty`` alone -- an approximation
    (e.g. "just don't fail if this pin has ever passed before") would
    silently readmit the exact "mechanism reporting success for having
    done nothing" shape this guard exists to catch. ``baseline_watch``
    names which single snapshot slot to read for this determination (an
    env-key label from ``_WATCHED_ENV_KEYS`` or a global's
    ``inventory_id`` from ``_WATCHED_GLOBALS``); required when
    ``requires_clean_baseline`` is ``True``, unused otherwise.

    ``marker_baselines`` (round-5 review, operator decision): the same
    ambiguity as ``requires_clean_baseline``, one level down -- ONE marker
    of a multi-marker pin, not the whole pin, can be structurally
    unobservable depending on baseline state. ``test_lifecycle_readiness``'s
    pin is the first instance: its ``[E26]`` symptom is a "create a
    SyncRuntime, then wrongly clear the global" bug, observable
    (``SyncRuntime -> None``) only when ``_runtime`` was ALREADY non-None
    coming in (inherited from an earlier leak); when it starts clean, the
    same bug round-trips through a throwaway instance back to ``None``,
    which is indistinguishable from never touching it at all. **The
    polarity is the opposite of the whole-pin case, measured, not
    assumed**: the whole-pin wiring case suppresses when its watched entry
    was already DIRTY (an unconditional overwrite to the same literal is
    invisible only when the prior value already matched); this one
    suppresses when its watched entry was already CLEAN (a create-then-
    clear round-trip is invisible only when there was nothing to clear
    away from). Reusing the wrong polarity would either never suppress
    (reintroducing the false failure) or always suppress (a silent pass) --
    ``unobservable_when`` on each ``_MarkerBaseline`` names the polarity
    explicitly per marker rather than assuming one direction fits every
    case.
    """

    node_id: str
    markers: tuple[str, ...]
    issue: str
    note: str
    requires_clean_baseline: bool = False
    baseline_watch: str | None = None
    marker_baselines: dict[str, _MarkerBaseline] = field(default_factory=dict)


# The 12, enumerated by node-id -- not a pattern, not a directory, so a
# 13th leak (on any of these files, or elsewhere) reds rather than joining
# silently. Markers are re-derived from #3130's own leaked-symbol column
# (not from one local run's output, which round-3 review found had
# under-modelled one node -- see the test_lifecycle_readiness entry below),
# cross-checked node-id-by-node-id and symbol-by-symbol against the issue.
#
# test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target
# carries `requires_clean_baseline=True` -- the only one of the 12 that does.
# History matters here, so it is kept rather than trimmed:
#
# 1. Round 3 pinned it like the other 11. In a SERIAL full-cone run it fired
#    the "stopped leaking" strict failure -- FALSE, because alphabetical file
#    ordering runs test_target_authority.py first in the same worker, which
#    already left `SPEC_KITTY_SAAS_URL` dirty; this node's own before-
#    snapshot for that entry was therefore already non-None, its dirty diff
#    was empty, and the guard could not tell "fixed" from "the one entry I
#    watch was already dirty coming in" -- the exact ambiguity this flag
#    exists to resolve.
# 2. Round 3 dropped the pin entirely as the fix. That moved the red instead
#    of removing it: UNPINNED, the node fires a TRUE unpinned-leak error
#    every time it lands on a clean-baseline worker, which `--dist loadfile`
#    hands it routinely (measured directly: `1 passed, 1 error` running the
#    node alone). Four green CI-selection samples were worker-placement
#    luck, not proof of absence -- confirmed by running the node ALONE, which
#    removes the placement lottery entirely and reproduces the leak, always.
# 3. Round 4 (this revision) re-pins it with `requires_clean_baseline=True`:
#    quiet when the node's own before-snapshot for `SPEC_KITTY_SAAS_URL` was
#    clean and it leaks (a normal accept); quiet when that same entry was
#    ALREADY dirty coming in, because an empty diff there is unobservable,
#    not fixed (the strict "stopped leaking" check is suppressed, not
#    satisfied); and it still hard-fails like every other pin if a NEW,
#    different leak shows up on this node. Proved in both directions plus a
#    discriminating control (flag flipped off reproduces the false failure
#    again) -- see the WP05 transition note / final report.
#
# #3130's OTHER ``--dist loadfile``-only candidate,
# ``test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance``,
# is also deliberately EXCLUDED from this list -- but for the opposite
# reason, and the justification is the measurement, not the issue text
# (#3130 says the two-workers-diverge shape IS real: "That is not
# flakiness -- it is the polluter/victim discrimination working"). Three
# independent ``--dist loadfile`` runs in the actual CI selection --this
# WP's own ``-n 8`` run plus the reviewer's two -- all show this specific
# node GREEN, unlike ``test_readiness_host_config_keys_off_resolved_target``
# which is reliably red there. Excluded because it has not been
# independently reproduced dirty in the selection that matters, not because
# the issue records it as clean -- pinning an unconfirmed node would be
# exactly the "unverified pin" this registry's own docstring forbids.
#
# ===========================================================================
# #3167 CONE HAZARD -- three of these twelve entries sit in another mission's
# write scope, and the rule that protects them is recorded HERE rather than in
# that mission's dossier, because a successor opens this file, not a spec
# (mission chain-b-consent-bypass-3167-01KZ63HK, its C-006).
#
# #3167 opens ``tests/sync/conftest.py`` -- this guard's HOST -- and it LANDS
# BEFORE the sync-cone mission's pinned-leak enumeration opens. That ordering is
# the hazard: the successor's fresh enumeration only means something if these
# entries were not churned in the window before it starts. Hence, binding:
#
#   DO NOT RE-PIN OPPORTUNISTICALLY. Do not add an entry, widen a marker tuple,
#   or re-pin a node in order to absorb a red. A pin comes OFF only when its leak
#   provably stops reproducing AS A CONSEQUENCE of the change that removes it,
#   and the removal is attributed per node id in that mission's handoff note.
#   No other reason to touch these three is in scope. (The guard hard-fails on a
#   pin whose leak stopped, so "leave it and see" is not an option either -- the
#   choice is un-pin-with-attribution or do not change the behaviour.)
#
# The three are marked ``[#3167 cone]`` below. Their state as measured by #3167,
# at its base ``b0482a832^`` and again after its ``tests/sync/conftest.py``
# change, so a successor can separate a pre-existing observation from a new one:
#
#   * test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
#     -- ERRORS as a PARTIAL match in the full serial ``tests/sync`` sweep, and
#     PASSES in isolation. Its ``[E26]`` observability is supplied by an UNPINNED
#     leak in ``tests/sync/test_dual_write_integration.py``, a file #3167 does
#     not own. Pre-existing at both commits; not a regression, not #3167's to fix.
#   * test_runtime.py::TestSyncRuntime::test_starts_background_service -- ACCEPTED.
#   * test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated
#     -- ACCEPTED.
#
# #3167 changed none of the three, and could not have: the seam it removed from
# ``conftest.py`` was a ``monkeypatch.setattr`` on a name deleted along with the
# queue-backed drain, and that name is not a watched entry, so it can neither
# start nor stop a pinned leak. Note also that the volatile band in this cone --
# ``live thread name='Thread-N' target=None``, produced by ``_ChainedTimer``
# (``sync/daemon.py:687,:715,:745``) and ``threading.Timer``
# (``sync/background.py:528``) -- moves between observing nodes from run to run
# (``Priivacy-ai/spec-kitty#3193``). The observer moves; the leak does not. Do
# not pin a node just because it was the observer on the run you happened to see.
# ===========================================================================
_PINNED_LEAKS: tuple[_PinnedLeak, ...] = (
    # UN-PINNED 2026-08-06 (#3130 fold, landing pass for #3209; attributed
    # per node id below, per the "un-pinning requires a leak that provably
    # stopped as a consequence of the change" rule stated for this registry).
    # All four node-ids below now call stop()/service.stop() in a try/finally
    # after starting real background work (a self-rescheduling
    # threading.Timer for the TestTimerBodyQueue pair, a real
    # spec-kitty-sync-async-loop thread for the TestRuntimeLifecycle pair) --
    # none of them previously joined/cancelled what they started. Removing
    # the pin and re-running each in isolation confirms the guard's own
    # self-proving mechanism: "this run left NOTHING dirty. The pinned leak
    # no longer reproduces" for all four.
    #   - tests/sync/test_background_body.py::TestTimerBodyQueue::test_timer_triggers_when_only_body_queue_has_tasks
    #   - tests/sync/test_background_body.py::TestTimerBodyQueue::test_timer_skips_when_both_queues_empty
    #   - tests/sync/test_background_body.py::TestRuntimeLifecycle::test_start_creates_body_queue
    #   - tests/sync/test_background_body.py::TestRuntimeLifecycle::test_shared_db_path
    # UN-PINNED 2026-08-06 (#3130 fold, landing pass for #3209; attributed
    # per node id below). Both node-ids' final-sync thread is a deliberately-
    # outlives-the-bounded-join thread (that IS the behaviour under test --
    # stop() must not block on a slow sync) with no external seam to reach
    # it; both now track it via the same TrackingThread pattern
    # test_stop_final_sync_thread_is_daemon (same file) already used, and
    # join it after their own assertions so it has actually finished before
    # the guard's post-teardown snapshot runs. Removing the pin and
    # re-running each in isolation confirms the guard's own self-proving
    # mechanism: "this run left NOTHING dirty. The pinned leak no longer
    # reproduces" for both.
    #   - tests/sync/test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_does_not_hang_when_sync_is_slow
    #   - tests/sync/test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_emits_structured_warning_when_sync_times_out
    # UN-PINNED 2026-08-11 (WP08 assertive sanitation). The lifecycle
    # readiness oracle now replaces incidental runtime attachment with a
    # no-thread fake and restores the exact prior emitter. Its former pin was
    # itself order-flaky: documented to error as a partial match in a full
    # sweep while passing in isolation. Dirty-predecessor and isolated probes
    # now both leave E26 and the async-loop thread unchanged.
    #   - tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
    # UN-PINNED 2026-08-06 (#3130 fold, landing pass for #3209; per the
    # "un-pinning requires a leak that provably stopped as a consequence of
    # the change, attributed per node id" rule the #3167-cone block above
    # states). Both of the following two node-ids added `runtime.stop()` in a
    # try/finally (they construct their own local SyncRuntime() and call
    # start(), which spawns a real spec-kitty-sync-async-loop thread neither
    # test previously joined -- unlike their sibling tests in this same file
    # that patch `_ensure_async_loop` and never spawn a real thread at all).
    # Removing the pin and re-running each in isolation confirms the guard's
    # own self-proving mechanism: "this run left NOTHING dirty. The pinned
    # leak no longer reproduces" -- both nodes now pass clean.
    #   - tests/sync/test_runtime.py::TestSyncRuntime::test_starts_background_service
    #   - tests/sync/test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated
    # UN-PINNED 2026-08-06 (#3130 fold, landing pass for #3209). Both node-ids
    # below, plus every OTHER raw `os.environ["SPEC_KITTY_SAAS_URL"] = ...`
    # write across test_target_authority.py and test_target_authority_wiring.py
    # (11 total, only 2 of which were ever pinned here), now go through
    # `monkeypatch.setenv(...)`, which restores the pre-test value in
    # teardown. Fixing only the two pinned node-ids would not have proven
    # anything: `test_all_fields_populated_under_env_equals_config`'s own fix
    # immediately re-exposed `test_env_equals_config_is_not_an_override`'s
    # identical unfixed leak in the very next serial node, and
    # `test_readiness_host_config_keys_off_resolved_target`'s
    # `requires_clean_baseline` framing (history kept above) exists
    # specifically because an UNFIXED upstream leak in this same file family
    # can make a clean node's own before-snapshot dirty. All 11 sites needed
    # fixing together to actually reach a clean baseline. Re-running the full
    # serial suite (`-p no:xdist`, matching the ordering both pins'
    # historical notes above depend on) confirms the guard's own self-proving
    # mechanism for both: "this run left NOTHING dirty. The pinned leak no
    # longer reproduces."
    #   - tests/sync/test_target_authority.py::test_all_fields_populated_under_env_equals_config
    #   - tests/sync/test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target
    # UN-PINNED 2026-08-06 (#3130 fold, landing pass for #3209): the test now
    # wraps its call chain in try/finally and calls
    # specify_cli.sync.runtime.reset_runtime() to restore the singleton the
    # production call chain sets, with no restoring finally of its own.
    # Re-running in isolation confirms the guard's own self-proving
    # mechanism: "this run left NOTHING dirty. The pinned leak no longer
    # reproduces."
    #   - tests/sync/tracker/test_saas_client_consent_gate_3030.py::test_mission_creation_bind_transmits_for_a_consenting_project
)

_PINNED_LEAKS_BY_NODE_ID: dict[str, _PinnedLeak] = {pin.node_id: pin for pin in _PINNED_LEAKS}


def _baseline_state_for(label: str, before: dict[str, object]) -> str:
    """Was the watched slot named ``label`` already dirty in THIS test's own
    before-snapshot? Returns ``"clean"`` or ``"dirty"``.

    Reads the exact same ``before`` dict ``pytest_runtest_teardown`` already
    captured at this test's setup (via ``_leak_guard_snapshot()``) -- not an
    approximation of it. ``label`` resolves against an env-key label
    (checked against ``_WATCHED_ENV_KEYS``, "clean" is ``None``) or a
    watched-global's ``inventory_id`` (checked against ``_WATCHED_GLOBALS``,
    "clean" is whatever ``_content_fingerprint(None)`` currently computes --
    recomputed here, not hardcoded as a literal tuple, so this stays correct
    if ``_content_fingerprint``'s own shape ever changes; true for every
    global a ``requires_clean_baseline``/``marker_baselines`` entry targets
    today, since all of them are None-when-clean singleton slots -- a future
    entry naming a global whose clean state is not "unset" would need this
    branch extended, not reused as-is).

    Shared by the whole-pin ``requires_clean_baseline`` check
    (``_pin_baseline_was_already_dirty``) and the per-marker
    ``marker_baselines`` check in ``_evaluate_pin`` -- one resolution rule,
    not two copies that could drift.

    Raises loudly, rather than guessing, if ``label`` does not resolve to a
    real watched slot -- degrading silently in either direction (always
    "clean", or always "dirty") would reintroduce either a false failure or
    a silent pass.
    """
    for env_label, _var_name in _WATCHED_ENV_KEYS:
        if env_label == label:
            return "clean" if before["env"].get(label) is None else "dirty"
    for entry in _WATCHED_GLOBALS:
        if entry.inventory_id == label:
            return "clean" if before["globals"].get(label) == _content_fingerprint(None) else "dirty"
    raise AssertionError(
        f"[FR-007 leak guard] baseline_watch={label!r} resolves to neither a watched "
        "env key nor a watched global -- a requires_clean_baseline/marker_baselines "
        "check cannot be evaluated. Fix the pin's baseline_watch (or a "
        "_MarkerBaseline's) in tests/sync/conftest.py; do not let this fail silently."
    )


def _pin_baseline_was_already_dirty(pin: _PinnedLeak, before: dict[str, object]) -> bool:
    """For a ``requires_clean_baseline`` pin: was ITS watched entry already
    non-default (``"dirty"``) in THIS test's own before-snapshot?

    Thin wrapper over ``_baseline_state_for`` for the whole-pin case; see
    that function's docstring for the resolution rule and rot control.
    """
    if not pin.requires_clean_baseline or pin.baseline_watch is None:
        raise AssertionError(
            f"[FR-007 leak guard] {pin.node_id} was routed to the "
            "requires_clean_baseline check without requires_clean_baseline=True "
            "and a baseline_watch set -- this is a bug in pytest_runtest_teardown, "
            "not a stale pin."
        )
    return _baseline_state_for(pin.baseline_watch, before) == "dirty"


#: pins actually observed dirty (and therefore silently accepted) this
#: session -- printed by ``pytest_terminal_summary`` so acceptance is
#: visible even though it does not fail the run.
_ACCEPTED_PINNED_LEAKS: list[tuple[str, list[str]]] = []

#: requires_clean_baseline pins suppressed this session because their
#: watched entry was already dirty at this test's own setup -- "unobserved",
#: not "accepted" (nothing was actually seen leaking this run) and not
#: "fixed" either. Printed separately so this third outcome is never
#: silently folded into either of the other two.
_SUPPRESSED_INHERITED_DIRTY: list[str] = []

#: (node_id, marker) pairs where a multi-marker pin was accepted with ONE
#: OR MORE of its markers excused as unobservable-this-run via
#: pin.marker_baselines, rather than fully reproduced. A fourth, narrower
#: cousin of _SUPPRESSED_INHERITED_DIRTY -- this node IS still recorded in
#: _ACCEPTED_PINNED_LEAKS (something genuinely leaked), but a reader should
#: be able to tell "every symptom observed" from "some symptoms excused"
#: rather than have both read identically as ACCEPTED.
_MARKER_LEVEL_UNOBSERVED: list[tuple[str, str]] = []


#: inventory_id -> human-readable reason, populated at most once per session
#: the first time a watched module's FILE exists (findable on the import
#: path) but its import raises anyway -- e.g. a platform-specific call at
#: module level. NOT staleness (see _resolve_watched_global's docstring);
#: reported once via pytest_terminal_summary rather than silently accepted.
_UNEVALUATABLE_WATCHED_ENTRIES: dict[str, str] = {}

#: Stable fingerprint returned for an unevaluatable entry's "value" -- the
#: same tuple every call, so before == after always for that entry and it
#: never contributes to `dirty` (the guard cannot watch what it cannot
#: import, and must not pretend to by inventing a value that could
#: spuriously differ).
_UNEVALUATABLE_SENTINEL: tuple[str] = ("unevaluatable-on-this-platform",)


def _resolve_watched_global(entry: _WatchedGlobal) -> object:
    """Resolve one watched entry's current value -- rot control lives here.

    A renamed, moved or deleted watched symbol must fail loudly rather than
    let the guard silently watch nothing (WP05 T019 rot control).

    **Platform-import distinguished from staleness** (CI finding, post-
    merge review: the Windows job's rot control failed importing
    ``tests.sync.test_consent_write_refusal_3030``, which calls
    ``os.geteuid()`` at module level -- a function that does not exist on
    Windows). The first version of this function treated ANY import
    failure as staleness, which is wrong: a module whose FILE exists but
    fails to import on the current platform is not "renamed, moved or
    deleted" -- the registry is fine, this process simply cannot evaluate
    the watch from here. Conflating the two makes the message actively
    misleading (it tells the operator to fix a registry that isn't broken)
    and fails the whole run for every test in the cone on that platform,
    which is the guard blinding itself to protect its own uptime -- the
    same defect shape this mission exists to remove.

    Distinguished via ``importlib.util.find_spec``, which locates a module
    without executing its body:

    * ``find_spec`` returns ``None`` (or raises resolving the name) --
      genuinely missing. Fails loudly, unchanged from before.
    * ``find_spec`` finds a real spec but ``import_module`` still raises --
      platform-unevaluatable. Recorded once into
      ``_UNEVALUATABLE_WATCHED_ENTRIES`` (reported every session via
      ``pytest_terminal_summary``, not silently swallowed) and this call
      returns ``_UNEVALUATABLE_SENTINEL`` instead of raising -- the entry
      is excluded from this session's dirty-detection via a stable
      fingerprint rather than failing every test in the cone on an import
      that will never succeed on this platform.

    A second call for the same entry short-circuits on the cache rather
    than re-attempting an import already known to fail here.
    """
    if entry.inventory_id in _UNEVALUATABLE_WATCHED_ENTRIES:
        return _UNEVALUATABLE_SENTINEL
    try:
        module = importlib.import_module(entry.module_path)
    except Exception as exc:  # noqa: BLE001 - must distinguish missing-module from unimportable-here, not just catch-and-fail
        try:
            spec = importlib.util.find_spec(entry.module_path)
        except (ImportError, ValueError, ModuleNotFoundError):
            spec = None
        if spec is None:
            raise AssertionError(
                f"[FR-007 leak guard] rot control: watched entry {entry.inventory_id} "
                f"({entry.module_path}) failed to import: {exc!r}. The watch-list "
                f"registry in tests/sync/conftest.py is stale for this module -- "
                f"update it rather than let the guard silently watch nothing."
            ) from exc
        reason = f"{entry.module_path} exists but failed to import on this platform: {exc!r}"
        _UNEVALUATABLE_WATCHED_ENTRIES[entry.inventory_id] = reason
        return _UNEVALUATABLE_SENTINEL
    _sentinel = object()
    value = getattr(module, entry.attr_path, _sentinel)
    if value is _sentinel:
        raise AssertionError(
            f"[FR-007 leak guard] rot control: watched entry {entry.inventory_id} "
            f"({entry.module_path}.{entry.attr_path}) no longer exists -- renamed, "
            f"moved or deleted since the inventory was written. The watch-list "
            f"registry in tests/sync/conftest.py is stale -- update it rather "
            f"than let the guard silently watch nothing."
        )
    return value


def _content_fingerprint(value: object) -> object:
    """A comparable, order-stable fingerprint for one watched value.

    Dict values are fingerprinted by ``id()`` per entry (not full ``repr()``)
    because at least one watched dict (E40, ``ENDPOINT_CALLS``) holds
    unreprable-by-content lambdas whose *identity* is what in-place
    reassignment would change, not their source text. Literal/near-literal
    fixture-data containers (``list``/``set``/``frozenset``/``tuple``) use
    ``repr()``, which is content-sensitive and correctly catches in-place
    mutation (an ``.append``/``.add`` changes the repr even though the
    container's own ``id()`` does not).

    **Everything else -- arbitrary class instances, including the two
    watched singletons E26/E27, and ``None`` -- is fingerprinted by
    ``(type(value).__name__, id(value), repr(value))``: identity first,
    repr() second, as defense in depth.**

    **Corrected, not merely re-derived** (reviewer HIGH, this revision):
    an earlier version of this function fell through to ``repr()``-only for
    this branch, and this docstring *claimed* that repr'd "as a live
    instance's default ``<Class object at 0x...>`` repr, unchanged unless
    the slot itself is reassigned" -- stated, not measured, and wrong.
    ``SyncRuntime`` (``src/specify_cli/sync/runtime.py``) is a
    ``@dataclass`` that marks 7 of its 9 fields ``repr=False``
    (``background_service``, ``ws_client``, ``emitter``, ``body_queue``,
    ``resolved_target``, ``_async_loop``, ``_async_loop_thread``); its
    generated repr carries no address and reduces to two booleans, e.g.
    ``SyncRuntime(_build_registered=False, started=False)``. Every
    unstarted ``SyncRuntime`` fingerprinted identically under repr()-only
    comparison -- measured: injecting a leaked ``SyncRuntime()`` (via a
    ``-p`` plugin, no file edited) across 22 nodes caught only the first
    (the ``None -> SyncRuntime`` transition); the remaining 21, all
    ``SyncRuntime -> SyncRuntime`` replacements, were silent. A control
    with ``MagicMock()`` as the leaked object (address-bearing default
    repr) caught all 22 -- proving the comparison mechanism itself was
    sound and the specific fallback was the gap. ``E27``
    (``BackgroundSyncService``) was not independently broken only by
    accident: its ``queue`` field is ``repr=True`` and ``OfflineQueue``'s
    own default repr carries an address, so two different queue instances
    already discriminated -- a future field marked ``repr=False`` on
    ``BackgroundSyncService`` (or its ``queue`` swapped for a value type)
    would silently reopen the same hole E26 had. Identity does not depend
    on any field's own ``repr=`` setting, so both are fixed the same way.

    **Why ``id()`` is safe here, and why ``repr()`` rides along anyway.**
    ``id()`` values are only ever compared WITHIN one test's own
    setup-to-teardown window (``_LEAK_GUARD_BEFORE`` is popped at that
    test's own teardown, never held across tests), and the watched slot
    itself (``getattr(module, attr_path)``) is what keeps an object alive
    for as long as nothing reassigns it -- so a leak (the slot pointing at
    a *different* object) is never confused with "no change" merely
    because CPython freed the old object and happened to reuse its address
    for something unrelated created earlier or later in the same process;
    that reuse can only matter if it happens to the SAME slot's OWN two
    reads, milliseconds apart, of a same-sized same-class object -- narrow,
    but not zero (this codebase's own closures were shown elsewhere in this
    file to churn addresses within a single test). ``repr()`` is folded
    into the same tuple as a second, independent signal precisely for that
    narrow case: an ``id()`` collision would additionally need the two
    objects' reprs to coincidentally match too, which -- for
    ``SyncRuntime``'s own two-boolean repr -- only happens when the
    *values* those booleans hold also happen to match, not merely the
    address.

    **Named blind spot, stated rather than left implicit** (reviewer LOW,
    prior round): for the six watched dicts (E32, E37-E40), ``id()``-per-
    value only detects a KEY added/removed or a value REASSIGNED to a
    different object -- it cannot see in-place mutation of a value's own
    contents. Measured directly: ``{"k": ["a"]}`` with an ``.append`` onto
    the inner list fingerprints unchanged, because the list object's
    ``id()`` does not change when it is mutated in place. A list-of-dicts
    held as a watched value (list mutation, e.g. ``.append``/``.pop`` on
    the outer list) IS caught, because that changes the outer container's
    own repr at the point this function is called on it directly (only
    *dict* values get the ``id()`` treatment; a list passed in directly is
    fingerprinted by content). The gap is specifically "a dict whose value
    is itself a mutable container, mutated in place without reassignment"
    -- none of E32/E37-E40's current values are structured that way (WP04
    verified zero in-place mutation call sites for all of them), so this
    is a stated limitation of the mechanism, not a known-missed leak.
    """
    if isinstance(value, dict):
        return ("dict", tuple(sorted((repr(k), id(v)) for k, v in value.items())))
    if isinstance(value, (list, set, frozenset, tuple)):
        return (type(value).__name__, repr(value))
    return (type(value).__name__, id(value), repr(value))


def _snapshot_watched_globals(entries: tuple[_WatchedGlobal, ...]) -> dict[str, object]:
    return {entry.inventory_id: _content_fingerprint(_resolve_watched_global(entry)) for entry in entries}


def _snapshot_env(keys: tuple[tuple[str, str], ...]) -> dict[str, str | None]:
    return {label: os.environ.get(var_name) for label, var_name in keys}


def _snapshot_live_threads() -> set[tuple[int | None, str]]:
    return {(t.ident, t.name) for t in threading.enumerate() if t.is_alive()}


#: node-ids the guard has run for, in order -- the positive control's
#: "how many tests it inspected" (H8 / NFR-008).
_LEAK_GUARD_INSPECTED_NODE_IDS: list[str] = []

#: this test's own before-snapshot, keyed by nodeid -- populated by
#: ``pytest_runtest_setup`` and consumed by ``pytest_runtest_teardown``.
_LEAK_GUARD_BEFORE: dict[str, dict[str, object]] = {}


def _leak_guard_snapshot() -> dict[str, object]:
    return {
        "globals": _snapshot_watched_globals(_WATCHED_GLOBALS),
        "env": _snapshot_env(_WATCHED_ENV_KEYS),
        "cwd": os.getcwd(),
        "threads": _snapshot_live_threads(),
    }


def _compute_dirty_lines(before: dict[str, object], after: dict[str, object]) -> list[str]:
    """Diff two ``_leak_guard_snapshot()`` results into human-readable lines.

    Extracted from ``pytest_runtest_teardown`` (reviewer MEDIUM, teardown-
    safety revision) purely to keep that hook's own cyclomatic complexity
    within ``ruff``'s C901 budget -- no behaviour change from the inline
    version.
    """
    dirty: list[str] = []

    for entry in _WATCHED_GLOBALS:
        before_val = before["globals"][entry.inventory_id]
        after_val = after["globals"][entry.inventory_id]
        if before_val != after_val:
            dirty.append(
                f"  - [{entry.inventory_id}] {entry.module_path}.{entry.attr_path} "
                f"({entry.description}): before={before_val!r} after={after_val!r}"
            )

    for label, var_name in _WATCHED_ENV_KEYS:
        before_val = before["env"][label]
        after_val = after["env"][label]
        if before_val != after_val:
            dirty.append(f"  - [{label}] os.environ[{var_name!r}]: before={before_val!r} after={after_val!r}")

    if before["cwd"] != after["cwd"]:
        dirty.append(f"  - [E53] cwd: before={before['cwd']!r} after={after['cwd']!r}")

    leaked_threads = after["threads"] - before["threads"]
    for ident, name in sorted(leaked_threads, key=lambda pair: (pair[1], pair[0] or -1)):
        target_repr = "<unresolved: thread exited between snapshot and report>"
        for live_thread in threading.enumerate():
            if live_thread.ident == ident:
                target_repr = repr(getattr(live_thread, "_target", "<cleared by Thread.run()>"))
                break
        dirty.append(f"  - live thread name={name!r} ident={ident} target={target_repr}")

    return dirty


def _evaluate_pin(pin: _PinnedLeak, dirty: list[str], before: dict[str, object], node_id: str) -> list[str] | None:
    """Strict allowlist check for one pinned node -- see ``_PINNED_LEAKS``'s
    own docstring for why this replaces ``xfail(strict=True)`` rather than
    using it. Returns the failure message lines if ``node_id`` must fail
    this run, or ``None`` if it is accepted quietly (records into
    ``_ACCEPTED_PINNED_LEAKS``) or suppressed as unobservable this run
    (records into ``_SUPPRESSED_INHERITED_DIRTY``). Four outcomes total,
    and only the last two are quiet:

    1. Dirt this pin's markers do not explain (``unaccounted`` non-empty)
       -- a NEW leak on an already-pinned node, or the filed defect
       changed shape. Must not be silently absorbed by a pin scoped to a
       different, already-verified observation.
    2. Nothing dirty at all (reviewer MEDIUM, requires_clean_baseline
       revision) -- either the leak is genuinely fixed (fail, name the
       node, strictness cuts this direction too) or -- only for a
       ``requires_clean_baseline`` pin whose one watched entry was already
       non-default in ``before`` -- unobservable this run, not fixed
       (suppress without recording an acceptance).
    3. Every dirty line is accounted for, but not every marker is
       accounted for by some dirty line (reviewer MEDIUM, marker-
       completeness revision) -- a partially-fixed leak reading as a full,
       unchanged reproduction. Fails, naming the missing markers -- UNLESS
       every missing marker is excused by ``pin.marker_baselines`` (round-5
       revision: the missing marker's own watched entry's ``before`` state
       matches that marker's declared ``unobservable_when`` polarity), in
       which case it is accepted quietly with the excused markers recorded
       into ``_MARKER_LEVEL_UNOBSERVED`` rather than silently indistinguishable
       from a full reproduction.
    4. Every dirty line is accounted for AND every marker is accounted
       for (or excused) -- the known, filed leak reproduced exactly as
       expected. Accepted quietly.
    """
    unaccounted = [line for line in dirty if not any(marker in line for marker in pin.markers)]
    if unaccounted:
        accounted = [line for line in dirty if line not in unaccounted]
        return [
            f"[FR-007 leak guard] {node_id} is pinned ({pin.issue}) for: {pin.note} "
            "-- but this run's dirty state includes lines the pin does NOT account for. "
            "A pin covers exactly what was independently verified, not 'anything on this "
            "node' -- if this is the same filed defect in a new shape, update the pin's "
            f"markers in tests/sync/conftest.py after re-verifying against {pin.issue}; "
            "if it is a new, different leak, it needs its own issue, not this pin:",
            *unaccounted,
            "",
            "(already accounted for by the existing pin, not the cause of this failure:)",
            *accounted,
        ]

    if not dirty:
        if pin.requires_clean_baseline and _pin_baseline_was_already_dirty(pin, before):
            # This pin's one watched entry was ALREADY non-default before
            # this test's own setup ran (inherited from an earlier test in
            # the same worker) -- an empty diff here is UNOBSERVABLE, not
            # "fixed": there was nothing left for this test to dirty
            # further. Suppress the strict failure without recording an
            # acceptance either (nothing was actually seen leaking this
            # run) -- see _pin_baseline_was_already_dirty's docstring and
            # this pin's own requires_clean_baseline note.
            _SUPPRESSED_INHERITED_DIRTY.append(node_id)
            return None
        # The pin's markers matched nothing because there was nothing to
        # match -- the node left NOTHING dirty this run, and (for a
        # requires_clean_baseline pin) its own watched entry was already
        # clean coming in, so this run genuinely had the chance to show the
        # leak and didn't. Strictness cuts the other way here: a pin that
        # stays in place after its leak is gone is a permanent exemption
        # wearing this docstring's "temporary" label. This must fail,
        # loudly, naming the node.
        return [
            f"[FR-007 leak guard] {node_id} is pinned ({pin.issue}) for: {pin.note} -- but "
            "this run left NOTHING dirty. The pinned leak no longer reproduces. This is not a "
            "quiet pass: remove this node's entry from _PINNED_LEAKS in tests/sync/conftest.py "
            "to prove the fix -- do not let a fixed leak keep its pin."
        ]

    # dirty is non-empty and every line is accounted for by SOME marker --
    # but strictness also requires the reverse (reviewer MEDIUM): EVERY
    # marker must be accounted for by SOME line, or a partially-fixed leak
    # (some symptoms gone, others remaining) reads as a full, unchanged
    # reproduction.
    missing_markers = [marker for marker in pin.markers if not any(marker in line for line in dirty)]
    if missing_markers:
        # Per-marker requires_clean_baseline (reviewer round-5): a missing
        # marker is excused -- unobservable this run, not evidence the
        # symptom stopped -- ONLY if pin.marker_baselines names it AND the
        # watched entry's own before-state matches that marker's declared
        # unobservable_when polarity. Anything else is a genuine miss.
        truly_missing: list[str] = []
        unobservable_markers: list[str] = []
        for marker in missing_markers:
            spec = pin.marker_baselines.get(marker)
            if spec is not None and _baseline_state_for(spec.baseline_watch, before) == spec.unobservable_when:
                unobservable_markers.append(marker)
            else:
                truly_missing.append(marker)

        if truly_missing:
            lines = [
                f"[FR-007 leak guard] {node_id} is pinned ({pin.issue}) for: {pin.note} -- but "
                "this run's dirty state does not account for every marker this pin declares. "
                "A partially-fixed leak is not a fixed leak: remove ONLY the markers that no "
                "longer reproduce from this pin's markers in tests/sync/conftest.py (after "
                f"re-verifying against {pin.issue}), or investigate why a marker that should "
                "still be present is not:",
                f"  missing markers (genuinely absent): {truly_missing!r}",
            ]
            if unobservable_markers:
                lines.append(
                    f"  missing markers excused as unobservable this run (baseline state "
                    f"matched their declared polarity, not the cause of this failure): "
                    f"{unobservable_markers!r}"
                )
            lines += ["  dirty lines observed this run:", *dirty]
            return lines

        # Every "missing" marker is accounted for as unobservable-this-run
        # (baseline state matched its declared polarity) -- the leak is
        # still accepted as reproducing, but the excused markers are
        # recorded separately so a reader of a clean run can tell "fully
        # observed" from "partially observed, rest excused" instead of
        # both reading identically as ACCEPTED.
        for marker in unobservable_markers:
            _MARKER_LEVEL_UNOBSERVED.append((node_id, marker))
        _ACCEPTED_PINNED_LEAKS.append((node_id, list(dirty)))
        return None

    _ACCEPTED_PINNED_LEAKS.append((node_id, list(dirty)))
    return None
