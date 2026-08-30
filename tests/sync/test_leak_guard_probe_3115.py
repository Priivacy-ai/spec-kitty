"""FR-007 leak-guard probe (#3115, WP05).

Proves the guard added to ``tests/sync/conftest.py``
(``pytest_runtest_setup`` / ``pytest_runtest_teardown``) actually bites,
using the order of preference FR-007 (spec.md) and WP05-leak-guard.md's
T018 make binding.

**Marked ``slow``, not ``fast`` (post-merge CI finding, draft PR #3144).**
``tests/architectural/test_pytest_marker_correctness.py``'s Rule 2 --
enforced at the FILE level, by design, regardless of which specific test
within the file uses ``subprocess`` -- forbids the ``fast`` marker on any
file that invokes ``subprocess.<callable>``. This file's own
``test_leak_guard_bites_a_synthetic_leak_via_subprocess`` does (see its
own docstring for why the isolation is deliberate), so the whole file
cannot carry ``fast``; ``slow`` is what its real cost actually is (~45-55s
per run, dominated by pytest's own collection/plugin-load overhead, not
sub-second). The architecturally "correct" fix Rule 2's own failure
message names -- split the fast portion into its own file -- is not
available this round (owned-files constraint: only this file and
``tests/sync/conftest.py``); a future WP that can create a third file
should do that split instead of leaving this note here permanently.

**Coverage-timing consequence, stated rather than left implicit**: this
moves ALL THREE tests in this file -- including
``test_leak_guard_does_not_flag_a_clean_selection``, which is genuinely
sub-second and does not itself touch ``subprocess`` -- out of
``fast-tests-sync`` (triggers on every PR touching ``tests/sync/``) and
into the dedicated ``slow`` CI job, which triggers only on push (i.e.
post-merge) or an explicit ``workflow_dispatch`` with
``run_extended``/``run_all``. That job's own path list already includes
``tests/sync`` (``"it hosts 2 real @slow tests"``, per its own comment),
so this file does NOT stop running in CI -- but it loses per-PR
feedback until a future split restores the fast portion to the fast
lane. Recorded here so this is a known, chosen tradeoff, not a silent
coverage gap.


**Order of preference, attempted in order**:

1. *Bite a real inventoried leak from WP04.* Investigated first. The four
   WP04-inventory "no reset seam" thread-spawning entries judged most likely
   to actually leave a live thread behind under a timed-out, unchecked
   ``join()`` --

   - ``tests/sync/test_daemon.py::TestDaemonFileLock::test_concurrent_spawn_serialised`` (E3)
   - ``tests/sync/test_diagnostic_dedup.py::test_report_once_deduplicates_across_threads`` (E6)
   - ``tests/sync/test_runtime.py::TestGetRuntime::test_thread_safe_concurrent_access`` (E10)
   - ``tests/sync/test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_final_sync_thread_is_daemon`` (E23/E24)

   -- were run together in one foreground pytest session under a
   ``threading.enumerate()`` census taken immediately before and after each
   test's own teardown. All four left the live-thread set unchanged
   (``leaked=[]`` for every one; MainThread only, before and after). None of
   the remaining "no reset seam" mutable-global entries (E28-E52) has an
   in-place mutation call site in its own file today either -- WP04's own
   inventory verified this with a targeted grep before classifying them
   "does not depend". Exhausting the rest of the 27 "no reset seam" entries
   under CI-representative concurrency (the condition under which a bare
   ``join(timeout=N)`` could plausibly time out) was judged out of
   proportion for this WP against the coordinator's explicit "do not let it
   block the guard" instruction.

2. *Synthetic probe, with the limitation recorded verbatim.* Per WP05's
   fallback clause: **"the only demonstrated bite is the synthetic case."**

The synthetic leak targets exactly one WP04-inventoried entry -- E31,
``tests/sync/test_daemon_intent_gate.py::ALLOWED_CALL_SITES`` (a
``set[str]`` allow-list) -- chosen because that file's own test
(``test_no_unauthorized_daemon_call_sites``) computes
``unauthorized = hits - ALLOWED_CALL_SITES``: a set-difference against
statically-discovered call sites. Adding one synthetic, never-a-real-call-
site token to the allow-list can only ever shrink or leave ``unauthorized``
unchanged, never grow it -- so this probe's mutation is provably inert for
that file's own assertions, regardless of test ordering.

**Isolated in a subprocess, on purpose.** An earlier draft ran the leaking
test directly, marked ``xfail(strict=True)``, expecting the mark to absorb
the guard's failure and keep this file green. Measured, not assumed: pytest
reports the guard's ``pytest.fail`` (raised from ``pytest_runtest_teardown``,
i.e. during *teardown*) as a **separate teardown-phase
failure** from the call-phase outcome the ``xfail`` marker actually governs
-- the call phase, having raised nothing itself, was reported ``XPASS``,
which ``strict=True`` correctly turned into its own hard failure. Net
result: two failure reports for one test and a red file, the opposite of
the intent. ``xfail`` does not cover teardown-phase failures; recorded here
so the next reader does not re-attempt it. The fix is process isolation:
the leaking scenario runs in a throwaway ``sys.executable -m pytest``
subprocess selecting only its own node-id, so (a) its mutation of
``ALLOWED_CALL_SITES`` evaporates with the subprocess and can never reach
another test in this worker, and (b) the wrapper test below -- which stays
in the normal collected suite and must pass -- asserts on the subprocess's
exit code and failure text instead of relying on a marker that cannot see
teardown.

**The probe carries the failure, not a later victim**: the assertion below
checks the *subprocess's own report* names
``test_leak_guard_bites_a_synthetic_leak_on_the_probe_itself`` -- the
leaking test's own node-id -- not some other test that happened to run
afterward.

**Control case (T017), recorded here because it was not recorded anywhere
committed the first time.** T017 requires the guard be pointed at
``tests/specify_cli/invocation/test_propagator_consent_gate_3030.py``'s
``wiring`` fixture -- the known ``reset_adapters()`` leak -- before any
other verdict is trusted, and its outcome quoted. Two things need stating
plainly, because the first WP05 report asserted "clean" without a
committed artefact and that assertion does not survive scrutiny as
recorded:

1. **The installed guard cannot run there at all**, and this is verified,
   not assumed: ``pytest_runtest_setup``/``pytest_runtest_teardown`` above
   are ``conftest.py`` hook implementations, and pytest only calls a
   ``conftest.py``'s hook implementations for items collected under that
   ``conftest.py``'s own subtree (reproduced with a two-directory example:
   a sibling directory's tests never triggered a hook defined in another
   directory's ``conftest.py``). ``test_propagator_consent_gate_3030.py``
   lives under ``tests/specify_cli/invocation/``, not ``tests/sync/``, so
   the control case is **structurally unrunnable by this guard** -- not a
   gap to close, a fact about what "installed at
   ``tests/sync/conftest.py``" means.
2. **The substitute evidence -- an ad-hoc script pointing the same
   ``_WatchedGlobal``/``_snapshot_watched_globals`` primitives at
   ``specify_cli.invocation.adapters._egress_consent_resolver`` from
   outside the installed guard -- was run once, against one test in that
   file, in a throwaway scratchpad script never committed to this repo.**
   That single run reported "clean" (before/after both the same registered
   closure). It is **not** a reliable characterization: an independent
   reviewer pointed an equivalent census at the *whole* file (all 8 tests,
   not one) and found 5 of 8 nodes flagged -- one a genuine unrestored
   clear (the historical leak shape, reproduced by suppressing the
   restore), the other four **closure-identity churn**:
   ``register_default_handlers()`` builds a brand-new closure object on
   every call, including the production one this resolver slot holds when
   nothing is under test, so an identity/``repr()``-based comparison of
   THIS symbol legitimately differs from one test to the next even when
   each test's own restore is individually correct. This is exactly why
   ``_egress_consent_resolver`` was deliberately excluded from
   ``_WATCHED_GLOBALS`` above (it is outside the ``tests/sync/`` inventory
   in any case) and exactly why the two in-scope dict-of-callables entries
   (``LEVEL_RESOLVERS``, ``ENDPOINT_CALLS``) are fingerprinted by ``id()``
   per dict *value*, not by ``repr()`` of the callable itself --
   ``_content_fingerprint``'s docstring in ``conftest.py`` names this
   choice. The reviewer's fuller, file-wide, source-verified reproduction
   is the evidence that should be trusted for "is the historical leak
   fixed", not the single-run scratchpad script; both agree the leak
   *mechanism* (restore vs. no restore) is what determines the outcome,
   not the specific single measurement this WP first quoted as "clean".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.sync.test_daemon_intent_gate import ALLOWED_CALL_SITES

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_SYNTHETIC_LEAK_TOKEN = "__fr007_leak_guard_probe_3115_synthetic_token__"
_RUN_LEAK_CASE_ENV = "_FR007_PROBE_RUN_LEAK_CASE_3115"
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    _RUN_LEAK_CASE_ENV not in os.environ,
    reason=(
        "runs only when driven by test_leak_guard_bites_a_synthetic_leak_via_subprocess "
        "below, in an isolated subprocess -- direct collection (any normal "
        "CI run of this file) skips it so the mutation never reaches another "
        "test in this worker"
    ),
)
def test_leak_guard_bites_a_synthetic_leak_on_the_probe_itself() -> None:
    """The only demonstrated bite is the synthetic case.

    Mutates exactly one inventoried entry (E31) and nothing else, and does
    not restore it -- the guard must be the one to notice, on this test's
    own teardown, not a later victim.
    """
    assert _SYNTHETIC_LEAK_TOKEN not in ALLOWED_CALL_SITES, "probe precondition: must start clean"
    ALLOWED_CALL_SITES.add(_SYNTHETIC_LEAK_TOKEN)  # deliberate, unrestored leak -- E31
    # No cleanup here by design: C-002 ("restore, do not clear") binds
    # fixtures that own state, not this probe, and the guard itself must not
    # repair what it finds dirty (WP05, "it detects and fails; it does not
    # repair"). Leaving this uncleaned is what lets the guard's own teardown
    # observe the dirty state and fail THIS test on it. The subprocess this
    # runs in exits immediately after, so nothing else ever observes it.


def test_leak_guard_bites_a_synthetic_leak_via_subprocess() -> None:
    """Red-first (T018): drive the leaking case in isolation and check the verdict.

    This test itself must stay green in the normal suite -- it is the proof
    that the guard fired, not the leak itself.
    """
    env = dict(os.environ)
    env[_RUN_LEAK_CASE_ENV] = "1"
    env.setdefault("PYTHONPATH", f"{_REPO_ROOT / 'src'}:{_REPO_ROOT}")
    node_id_relative = f"{Path(__file__).resolve().relative_to(_REPO_ROOT)}::test_leak_guard_bites_a_synthetic_leak_on_the_probe_itself"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            node_id_relative,
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = result.stdout + result.stderr

    assert result.returncode != 0, (
        "FR-007 guard did not fail the leaking probe -- expected the guard to "
        f"catch the synthetic E31 leak; subprocess exited {result.returncode}:\n{combined}"
    )
    assert "FR-007 leak guard" in combined, f"guard's own failure banner missing from output:\n{combined}"
    assert "E31" in combined, f"guard did not name the inventoried entry (E31):\n{combined}"
    assert "ALLOWED_CALL_SITES" in combined, f"guard did not name the symbol:\n{combined}"
    assert "test_leak_guard_bites_a_synthetic_leak_on_the_probe_itself" in combined, (
        f"guard's failure must be attributed to the probe's own node-id, not a later victim:\n{combined}"
    )


def test_leak_guard_does_not_flag_a_clean_selection() -> None:
    """Positive control: a test that only reads a watched entry is not flagged.

    Runs in the normal (non-subprocess) session, where the leaking case
    above is skipped, so ``ALLOWED_CALL_SITES`` is exactly as
    ``test_daemon_intent_gate.py`` defined it -- clean. This test must pass.
    """
    assert isinstance(ALLOWED_CALL_SITES, set)
    assert "src/specify_cli/sync/daemon.py" in ALLOWED_CALL_SITES
    assert _SYNTHETIC_LEAK_TOKEN not in ALLOWED_CALL_SITES
