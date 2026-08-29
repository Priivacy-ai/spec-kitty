---
title: Test-flakiness handling policy
description: "Spec Kitty's suite-wide flaky-test policy: how to detect a flake, what is and isn't allowed (never retry-to-green), and the disposition of each known flake surface."
doc_status: active
updated: '2026-08-11'
audience: docs/context/audience/internal/lead-developer.md
type: explanation
related:
- docs/development/testing/testing-parallel.md
---
# Test-flakiness handling policy

A *flaky* test is one whose pass/fail outcome changes between runs **without any
change to the code under test** — it sometimes goes red on CI for reasons
unrelated to the diff under review. Flakes waste review cycles and, left
unmanaged, normalise a red CI that everyone learns to ignore.

This page is the suite-wide policy for handling them: how we **detect** a flake,
what we are allowed to do about it (and explicitly *not* allowed to do), and the
current disposition of every known flake surface in this repo.

> **The one rule that governs everything below:** we never make a test pass by
> *retrying it until it goes green*. A green-after-retry is the
> "fixed because it looks fixed" trap — it hides genuine regressions and is
> incompatible with this repo's live-evidence / anti-laziness discipline. Retry
> plugins (`pytest-rerunfailures`, the PyPI `flaky` plugin) are therefore **not
> adopted**, and are not present in the dependency set.

## ⚠️ Naming: `flaky` the marker is *not* "flaky" the concept

This repo already registers a `flaky` pytest marker, and it means something
**narrow and unrelated** to this policy. Per
[ADR 2026-04-20-1](../../adr/3.x/2026-04-20-1-mutation-testing-as-local-only-quality-gate.md),
`@pytest.mark.flaky` means *"passes reliably in the main suite but is
non-deterministic **under `mutmut` / forking pipelines**"* — it is a deselection
bucket for the mutation-testing sandbox, **not** a CI-quarantine mechanism.

Do not reach for the `flaky` marker to deal with a CI flake. If a genuine
quarantine mechanism is ever needed, it must use a **different** name
(`quarantine`, see below) so the two never get conflated.

## The three tiers

Every flake in this suite falls into one of three tiers, and each tier has a
single sanctioned response.

| Tier | What it is | Example | Sanctioned response |
|---|---|---|---|
| **1. Threshold / budget gate** | A test that asserts a measurement stays under a wall-clock / size budget. CI runners are shared and noisy, so a generous gate occasionally trips with no real regression. | NFR-002 latency (`tests/architectural/test_wp_prompt_build_latency.py`), the `-m timing` gate. | **Tune the budget — never retry.** Widen the budget to absorb runner variance. A *real* regression adds time **consistently** and still trips a generous gate; a retry would mask exactly that. Investigate before bumping; the budget is the gate, not the regression. |
| **2. Correctness test** | A test of logical behaviour that should be 100% deterministic. If it flakes, the test (or the code) has a hidden nondeterminism — shared global state, ordering assumptions, fixture-teardown races, monkeypatch leakage, import-time side effects. | `tests/specify_cli/shims/test_registry.py` (parallel-collection nondeterminism). | **Fix the root cause — never retry.** A correctness test that needs a retry is lying. Find the nondeterminism and remove it. |
| **3. Genuinely environmental** | A test that depends on an OS-global resource — real TCP ports, singleton daemons, the real filesystem — that cannot be fully isolated per worker. | Real-port / daemon suites (`tests/sync/test_orphan_sweep.py`, ports 9400–9449). | **Surgical handling only.** First serialise (`-n0`) and isolate (per-worker HOME) — see [testing-parallel.md](testing-parallel.md). Only if a residual, irreducible environmental flake remains do we **quarantine** (below) — never a blanket retry. |

## Detection: confirm a flake before you treat it

One red run is a single data point — pytest alone cannot tell *flaky* from
*broken*. Before declaring a test "flaky" and applying any of the responses
above, **reproduce the nondeterminism**:

- Re-run the test in isolation, and under the parallel runner it failed on:
  ```bash
  PWHEADLESS=1 pytest <path> -n auto --dist loadfile -p no:cacheprovider
  ```
- For ordering / hash-seed flakes, re-run under different `PYTHONHASHSEED`
  values and diff the collected node IDs.
- For a confidence signal, use the existing **stability ratchet** — N consecutive
  green parallel runs, the same gate CI uses for shard flips. The authoritative
  invocation lives in
  [testing-parallel.md → Running the stability ratchet locally](testing-parallel.md#running-the-stability-ratchet-locally);
  point it at the suspect `<path>` instead of fabricating a new command.
  (Full harness: `tests/_support/coverage_safety/README.md`.)

A test that cannot be made to fail again under these probes is **not** confirmed
flaky — do not annotate it.

## Tooling decision

**No retry tooling — ever.** `pytest-rerunfailures` / PyPI `flaky` are
deliberately not in the dependency set (see the rule at the top). Detection and
isolation reuse what the repo already has; the only thing built specifically for
this policy is the `quarantine` marker.

- **No retry plugin.** See the rule at the top.
- **Detection** uses the existing stability ratchet
  (`tests._support.coverage_safety.ratchet`), not a new confidence tool.
- **Isolation** (the first line of defence for Tier 3) is the existing
  per-worker HOME isolation + serial `-n0` pass documented in
  [testing-parallel.md](testing-parallel.md).

### `quarantine` — built, env-gated, non-blocking

The sanctioned mechanism for an irreducible Tier-3 flake is a dedicated
`quarantine` marker — **not** a retry, and **not** the existing `flaky` marker.
It is implemented as a single, un-bypassable chokepoint:

1. **Registered** canonically in `pytest.ini`'s `markers` block — the single
   source of truth for the marker registry (#2034) — sufficient for
   `--strict-markers`.
2. **Held out of every normal run.** `tests/conftest.py`'s
   `pytest_collection_modifyitems` skips any `@pytest.mark.quarantine` test
   **unless `SPEC_KITTY_RUN_QUARANTINE=1`**. Because this is collection-time and
   global, no `-m` selector in any CI job (present or future) can accidentally
   run a quarantined test — the gate cannot be forgotten. The opt-in is strict
   (only the literal `"1"`); the pure decision lives in
   `tests/_support/quarantine.py` and is unit-tested.
3. **Visible, never blocking.** The `quarantine-visibility` job in
   `ci-quality.yml` sets `SPEC_KITTY_RUN_QUARANTINE=1` and runs `-m quarantine`
   for real, so a quarantined flake is still **seen failing** — never silently
   retried to green. The job is deliberately **excluded from the `quality-gate`
   aggregation** (and must stay out of branch-protection required checks), so it
   can never turn `main` red or block an unrelated PR. It tolerates an empty
   quarantine set (pytest exit code 5) so "nothing quarantined" is green. The
   architectural CI guard scans every Python test for direct
   `pytest.mark.quarantine` usage and requires the job's owner manifest to match
   the discovered file set exactly; an empty manifest therefore cannot hide a
   newly quarantined test elsewhere in `tests/`.

**To quarantine a test:** mark it `@pytest.mark.quarantine` with a one-line
reason **and a tracking-issue link** — every quarantined test is tech debt with
an owner. The wiring above (`test_quarantine_marker.py`) is enforced.

As of this writing **no test is quarantined** (see the disposition table — every
known surface is fixed or correctly handled). The mechanism exists so the first
irreducible flake has a sanctioned home instead of a retry.

## Audit + disposition of known flake surfaces

| Surface | Tier | Disposition |
|---|---|---|
| `tests/architectural/test_wp_prompt_build_latency.py` (NFR-002 latency) | 1 | **Resolved — keep tuning.** Budget already widened 8.0 → 10.0s after a shared runner measured 8.50s with no code regression (PR #2036). The file carries inline rationale that *is* the Tier-1 policy. No further change. |
| `doctor restart-daemon` issue #1153 / NFR-002 wall-clock gate | 3 | **Retired as a portable CI performance claim in PR #3285.** The original ≤10-second end-to-end requirement depended on OS-global daemon and port state and repeatedly failed during hosted-macOS control-plane bootstrap without a corresponding product regression. The controlled Linux lane now enforces the replacement functional contract: the old daemon stops, a distinct PID starts, and the control plane becomes healthy within bounded subprocess and readiness timeouts. macOS remains supported through platform-independent tests and local smoke evidence; a future cross-platform restart performance SLO requires a controlled developer/canary harness because shared-runner wall clock is not accepted as evidence. |
| `tests/sync/test_orphan_sweep.py` and `tests/_real_port_suites.py`'s `FIXED_RANGE_SUITES` (real fixed ports 9400–9449, daemons) | 3 | **Retired — this surface no longer exists.** The sync transport that owned it was deleted (issue #5): `tests/sync/` and `tests/_real_port_suites.py` are gone from the repo, so there is nothing left to serialise or quarantine here. `make test-full`'s current topology (one parallel pass plus dedicated `-n0` serial passes for `stress`/`timing`) is described in `CLAUDE.md`'s Commands section. |
| `tests/specify_cli/shims/test_registry.py` (parallel-collection nondeterminism) | 2 | **Fixed at root cause.** Parametrising over `list(<frozenset>)` produced a `PYTHONHASHSEED`-dependent case order, so xdist workers collected different orders ("Different tests were collected between gw0 and gwN"). Changed to `sorted(<frozenset>)`, making collection order deterministic across workers. Verified: identical node-id order under different hash seeds. |
| `tests/sync/tracker/test_egress_single_authority.py`, `tests/sync/test_transport_revocation_matrix.py`, `tests/sync/tracker/test_saas_client*.py` and siblings (module-level accumulator / thread-identity state under bare `-n <N>`) | 2 | **Fixed at root cause (TEST-M2-03).** A bare `pytest tests/ -n <N>` — no explicit `--dist` — silently gets xdist's own `"no"` → `"load"` auto-upgrade (`xdist/plugin.py::pytest_cmdline_main`, which runs before every `pytest_configure`, including this repo's own). `load` scatters one file's parametrized cases and test classes across workers with no file-scoping guarantee, which this repo's own docs already warned against (testing-parallel.md's "Always `--dist loadfile`, never bare `--dist load`") — but that rule was previously enforced only by CI's explicit flag and by developers remembering to type it locally. Two concrete failures reproduced this: `test_egress_single_authority.py::TestT001EnforcementEquivalenceMatrix::test_matrix_ran_every_cell_incl_permit_row_and_every_precedence_level` (a module-level accumulator only sees the subset of cells that land on its own worker — "ran 9 of 48 declared cells") and `test_transport_revocation_matrix.py`'s `_project_b_progress` helper (a `patch.object`'d `__init__` recording opens process-wide, racing a concurrent opt-out thread it does not own). `tests/conftest.py::_upgrade_unspecified_xdist_load_to_loadfile` promotes the *default* the same way xdist promotes `"no"` — only when the user asked for neither serial nor an explicit `--dist` — closing the gap for every such file at once instead of opting each one in individually; an explicit `--dist load/loadscope/loadgroup/worksteal/each` is never overridden. Verified: `test_egress_single_authority.py` reds reliably under bare `-n5` before the fix (2/2 runs) and passes clean after (2/2 runs); `test_transport_revocation_matrix.py` and the `saas_client` family (230 tests) pass clean under bare `-n5` after the fix (2/2 runs each); `tests/sync` as a whole (3439 tests, `FIXED_RANGE_SUITES` excluded) passes under bare `-n5` after the fix with 0 failures in this family across 2 consecutive runs. |
| `tests/sync/test_daemon_self_retirement.py` (4 failures reported against the M0 baseline and the pre-`cff82ad84` M2-canonical-integration baseline; `docs/bootstrap/M2-CANONICAL-INTEGRATION.json`) | 2 | **Not reproduced post-fix (TEST-M2-03); tracked as covered by the same root-cause fix above, not independently repaired.** The integration receipt classifies these 4 as "fail on M0 too" (i.e. present on a baseline predating `tests/conftest.py`'s `--dist loadfile` default), which is consistent with — not contrary to — the row above: an M0 baseline run via bare `pytest tests/ -n <N>` would hit the identical `"load"`-scattering default, and this file's own module-global `monkeypatch.setattr(daemon, "DAEMON_STATE_FILE"/"DAEMON_TICK_SECONDS", ...)` seams and cross-thread `threading.enumerate()` leak assertions (`TestRunSyncDaemonWiring`) are exactly the shape that scattering breaks. All 26 tests in the file were run and passed in every configuration probed on this evidence run: serial (`-n0`), forced `-n5 --dist loadfile` standalone, and — with the fix applied — bare `-n5` both standalone and as part of the full `tests/sync` batch (2/2 consecutive runs, 0 failures in this file either time). No independent defect in `daemon.py` or the test file itself was found or changed. If a future run reproduces a failure here under the fixed default, re-open as a new, separately-evidenced defect rather than assuming this disposition covers it. |

## Adding a new test? Avoid the common root causes

When a correctness (Tier 2) test flakes, it is almost always one of these — fix
the cause, do not retry:

- **Unordered data used where order matters.** Iterating a `set`/`frozenset`/`dict`
  for parametrize IDs or assertion sequences → `PYTHONHASHSEED`-dependent order.
  Wrap in `sorted(...)`.
- **Fixture-teardown races / leaked global state** between tests sharing a module
  or process.
- **`monkeypatch` / env-var leakage** across tests (rely on the per-worker HOME
  isolation; don't mutate process-global state without restoring it).
- **Import-time side effects** that bind a path or singleton before fixtures run.
- **Time-sensitive assertions** in a non-timing test — move the timing concern to
  a Tier-1 budget gate with a generous threshold, or remove the wall-clock
  dependency.
- **`patch.dict(sys.modules, ...)`** — snapshot-restores the whole dict on exit,
  evicting any module first-imported inside the patched window (spec-kitty#89/#99;
  ratcheted by `tests/architectural/test_no_sys_modules_patch_dict.py`). Use
  `monkeypatch.setitem(sys.modules, key, value)` per key instead — it is the only
  accepted `sys.modules` seam.

## Test-run baseline-red gotcha

A red test is not automatically *your* red. A local or backgrounded `pytest` run over
anything broad (the full suite, `tests/merge/`, `tests/architectural/`, the regression job)
will surface failures you did not cause. **Classify every failure before you act on it** —
misattribution wastes effort and, worse, tempts an agent to green-wash a signal the project
deliberately keeps red.

Three baseline-red categories that are **not yours to fix**:

1. **Pre-existing known-P0 reds.** Per [ADR 2026-07-17-1](../../adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md),
   an open P0 bug is *expected* to red mainline (e.g. #2736 batch poisoning, #2772 charter
   clobber, #1834 accept-overwrite). They carry `@pytest.mark.regression` and reference a
   tracking issue. **Leave them red** — do not deselect, quarantine, or "fix" them in an
   unrelated change (that is the fold-first policy in [pr-landing.md](../how-to/pr-landing.md)).
2. **CI-environment failures.** Auth state (`logged_out_on_connected_teamspace` during
   `upgrade`) and the sync disable toggles — `SPEC_KITTY_SYNC_MINIMAL_IMPORT` /
   `SPEC_KITTY_SYNC_DISABLE`, which the pre-review gate honors as a *skip* — make some CI jobs
   red while the same tests pass locally. These are configuration, not your diff.
3. **Stale-install false reds.** Product code that shells out to `spec-kitty` (e.g. the
   `merge-driver-meta`/`-traces` commands) only fires when an up-to-date `spec-kitty` is
   installed. Between landing a change and `pip install -e .`, coverage/gate jobs report
   false reds for lines that are actually exercised via subprocess.

**The attribution test:** a failure is yours to fold only if it is **red on your branch and
green on the base**. Confirm the base state by running the same node id against
`upstream/main` — e.g. from a throwaway worktree with
`PYTHONPATH="$(pwd)/src" python -m pytest <nodeid>` — or by checking the tracker for a P0
label. When you *do* add a red-first P0 reproduction on purpose (per the ADR), mark it
`regression`, docstring the issue, and make sure it fails for the product reason, not setup.

This applies to **dispatched subagents** as much as the orchestrator: an implementer that runs
the suite in its worktree must not report the baseline reds as regressions or try to fix them.

## See also

- [Running the test suite in parallel](testing-parallel.md) — per-worker HOME
  isolation, the serial marker passes, and the stability ratchet.
- [ADR 2026-04-20-1](../../adr/3.x/2026-04-20-1-mutation-testing-as-local-only-quality-gate.md)
  — the `flaky` / `non_sandbox` markers (mutmut deselection; distinct from this
  policy).
- [How-to: run mutation tests](run-mutation-tests.md).
