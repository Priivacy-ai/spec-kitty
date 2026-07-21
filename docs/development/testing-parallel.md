---
title: Running the test suite in parallel
description: 'How to run the Spec Kitty test suite in parallel locally and in CI: the one correct command, why it is shaped that way, and reproducing the coverage-neutrality gates.'
doc_status: active
updated: '2026-07-12'
type: how-to
related:
- docs/development/testing-flakiness.md
- docs/plans/testing/test-suite-acceleration-plan.md
- docs/plans/testing/ci-job-timings.md
- docs/plans/testing/ci-coverage-union-audit.md
---
# Running the test suite in parallel

The Spec Kitty test suite runs safely in parallel locally and in CI, typically
at least 2× faster on a machine with four or more cores. This page explains the
one correct local command, why it is shaped the way it is, and how to reproduce
the coverage-neutrality gates CI uses.

For what to do when a test goes red on CI *unrelated to your diff* — budget gates
vs. correctness flakes vs. environmental flakes, and why we never retry-to-green —
see the [test-flakiness handling policy](testing-flakiness.md).

## The local command

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
# daemon/real-port tests run serially:
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

The first command runs the bulk of the suite across worker processes. The second
command runs the daemon/real-port tests serially. Run both; the parallel command
deliberately leaves the serial-only tests for the second pass.

## Why `--dist loadfile` (never bare `--dist load`)

`pytest-xdist` supports several distribution modes. We always use `loadfile`:

- **`loadfile`** keeps every test that lives in the same file on a single
  worker. File-scoped fixtures (`scope="module"`, file-level collection
  ordering, shared module state) keep working exactly as they do serially.
- **`load`** (the bare default) scatters a single file's tests across multiple
  workers. That breaks file-scoped fixtures and any test that relies on
  collection order within a file.

For that reason: **always pass `--dist loadfile`; never use bare `--dist
load`.** CI uses `loadfile` for the same reason.

`-p no:cacheprovider` disables pytest's cache plugin so a parallel run never
races on the shared `.pytest_cache` directory.

## Per-worker HOME isolation (the master enabler)

A parallel run **never touches the real `~/.spec-kitty`**. Each `pytest-xdist`
worker — and the serial "master" run when you omit `-n auto` — gets its own
isolated home directory. The isolation is set up in `tests/conftest.py`:

- `pytest_configure` points `HOME` / `USERPROFILE` and the XDG dirs
  (`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`) at a per-worker base
  **before collection**, so modules that bind a home-derived path at import time
  (for example `specify_cli.sync.daemon.SPEC_KITTY_DIR`) resolve into the
  isolated home.
- An autouse, function-scoped fixture re-asserts the `HOME` / `USERPROFILE` / XDG
  env vars for every test, keyed by worker id, so call-time `Path.home()` reads
  are isolated too. It does **not** monkeypatch `Path.home` (that approach was the
  cycle-1 regression that broke ~16 `tests/sync` cases — the fixture relies on
  `Path.home()` natively resolving `HOME` via `expanduser`), so a test that sets
  up its own tmp home via `setenv('HOME', ...)` cleanly overrides the per-worker
  baseline.

The per-worker base is keyed by the xdist test-run UID and the worker id, so two
workers in the same run get distinct homes (no collision) and successive runs do
not reuse stale state. The regression guard
`tests/architectural/test_real_home_isolation_guard.py` (SC-006) and
`tests/test_worker_home_isolation.py` prove this invariant.

Because the real `~/.spec-kitty` is never bound, you do not need to back it up or
worry about a parallel run truncating your real `queue.db`.

## The serial daemon pass

Per-worker HOME isolation protects per-user state, but it does **not** protect
OS-global resources such as real TCP ports or singleton daemons. Tests that bind
the reserved daemon port range (9400–9449) — `tests/sync/test_orphan_sweep.py` —
must run in their own serial pass:

```bash
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

`-n0` forces serial execution even when xdist is installed. These tests are
excluded from the parallel pool so two workers never contend for the same port.

## Volume env gates (`SPEC_KITTY_ULID_VOLUME_FULL`)

Some tests exercise large-volume ULID generation. By default they run at a
**reduced** scale so the local default stays fast; the full scale is reachable
via an env gate (and is exercised on the nightly/full path). The assertion logic
is identical across scales — only the volume changes.

```bash
pytest <ulid_test> -q                               # reduced (fast, default)
SPEC_KITTY_ULID_VOLUME_FULL=1 pytest <ulid_test> -q  # full (nightly parity)
```

## Running the stability ratchet locally

Before any shard is flipped to parallel, it must pass the stability ratchet
(C-RATCHET): N consecutive green parallel runs with no new flakes. The same
entrypoint CI uses is available locally (the WP02 coverage-safety harness):

```bash
python -m tests._support.coverage_safety.ratchet -n 3 -- tests/agent -m "not slow"
```

Exit code `0` means all N runs were green and the flip is accepted; `1` means it
was rejected and the summary names any new or flaky failures. The Python API is
`run_ratchet(...)` from `tests._support.coverage_safety`. See
`tests/_support/coverage_safety/README.md` for the full harness (collection
equivalence and anti-vacuity mutation checks).

## Validate the acceleration (copy-pasteable)

These are the mission's reproducible validation steps. Run them from the repo
root to confirm the parallel run is coverage-neutral and at least 2× faster than
serial. (`.venv/bin/pytest` is the synced project interpreter; substitute
`pytest` if you run it directly.)

```bash
# 1. Serial baseline (whole-suite wall clock) and a per-shard nodeid reference.
time .venv/bin/pytest tests/ -q -p no:cacheprovider     # serial baseline
.venv/bin/pytest tests/charter --collect-only -q | sort > /tmp/charter-serial.nodeids

# 2. Collection equivalence: serial vs parallel must collect identical nodeids.
.venv/bin/pytest tests/charter -n auto --dist loadfile --collect-only -q \
  | sort > /tmp/charter-par.nodeids
diff /tmp/charter-serial.nodeids /tmp/charter-par.nodeids   # must be empty

# 3. Stability ratchet: 3 consecutive green parallel runs (the same gate CI uses).
python -m tests._support.coverage_safety.ratchet -n 3 -- \
  tests/charter -m "fast and not windows_ci"

# 4. Parallel-vs-serial timing: target ≥2× faster on a ≥4-core machine.
time PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider \
  --deselect tests/sync/test_orphan_sweep.py
time PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -n0 -q   # serial pass

# 5. Real home untouched: mtime/inode unchanged (or path still absent) after the run.
ls -la ~/.spec-kitty 2>/dev/null
```

## Status: local default vs CI shard flips

- **Local parallel command — validated and safe now.** Per-worker HOME isolation
  (WP04) is in place, so the local command above runs without touching your real
  `~/.spec-kitty`. Use it today.
- **This mission's CI shard flips (`ci-test-topology-performance-01KXBJRT`,
  §"CI shard topology" below) — shipped, no real CI run yet.** Collection
  equivalence for `integration-tests-next`, `slow-tests`, and the rebalanced
  `fast-tests-core-misc` was verified locally before landing, but (unlike
  the older flips below) this branch has not yet run in real CI at all — see
  [`docs/plans/testing/ci-job-timings.md`](../plans/testing/ci-job-timings.md)
  for the honest PENDING wall-clock record, filled in once a real run
  exists.
- **Older shard flips (a separate, earlier mission: `test-suite-acceleration`,
  [`docs/plans/testing/test-suite-acceleration-plan.md`](../plans/testing/test-suite-acceleration-plan.md))
  — landed, pending 3×-green confirmation.** `fast-tests-doctrine`,
  `fast-tests-cli`, `fast-tests-charter`, `fast-tests-agent`, and
  `fast-tests-status`'s re-route each carry a `PENDING-CI` comment in
  `.github/workflows/ci-quality.yml` noting collection-equivalence was
  verified locally but three consecutive green CI runs (the stability
  ratchet, C-RATCHET below) have not yet confirmed the flip under real
  runner contention. These are a distinct, still-open item from the current
  mission and are not resolved by it. The full "≥2× faster" claim for both
  sets of flips is host-dependent; locally you should still see a clear
  speedup on a multi-core machine regardless of either flip's CI-confirmation
  status.

## CI shard topology (`ci-test-topology-performance-01KXBJRT`)

The project's PR-gating CI (`ci-quality.yml`) re-topologized its slowest jobs
in mission `ci-test-topology-performance-01KXBJRT`, generalizing the
`arch-adversarial` shard mechanism (`tests/_arch_shard_map.py` +
`tests/conftest.py`'s collection hook + a parametrized completeness guard)
into a shared **N-group registry** so `arch` and `next` are two rows of one
mechanism, not two cloned ones (FR-002/C-003).

### `integration-tests-next` — the headline `next_shard_N` matrix

Previously a single, fully-serial job (69.2 min, 441 tests, no
`-n auto`/`--durations`). It is now a 3-leg matrix
(`next_shard_1`/`next_shard_2`/`next_shard_3`, `strategy.fail-fast: false`)
driven by `tests/_next_shard_map.py`'s registration into the shared
`SHARD_GROUPS` registry, covering the same 3 roots
(`tests/next`, `tests/specify_cli/next`, `tests/runtime`) across all three
legs — the `next_shard_N` pytest marker (applied at collection time by the
shared hook), not `paths`, partitions the work. Each leg runs
`-n auto --dist loadfile -p no:cacheprovider --durations=25`. **Known gap:**
the 3-way file assignment is still WP01's placeholder greedy bin-pack (by a
`def test_` count proxy) — it has not yet been rebalanced from a real
`--durations=25` run the way `fast-tests-core-misc` below was; see
[`ci-job-timings.md`](../plans/testing/ci-job-timings.md) §4 for the
follow-up once real per-leg minutes exist.

### `slow-tests` — narrowed paths + parallel

Path-narrowed to the directories that actually hold `@slow`-marked tests
(derived via `git grep -rl "pytest.mark.slow" tests/`), with the pre-existing
`--ignore=tests/e2e --ignore=tests/cross_cutting` pair kept verbatim, plus
`--ignore=` entries for all 4 `FIXED_RANGE_SUITES` real-port members
(structural exclusion, not marker-only — see below) and `-n auto --dist
loadfile` added. Collection-equivalence verified locally against the
pre-narrowing selection (identical 45-test set at time of writing).

### Orphan-sweep hoisted to its own concurrent job

`test_orphan_sweep.py` (the fixed-range daemon/real-port suite) used to be a
serial `-n0` *step* inside `fast-tests-sync`, sitting on that job's critical
path even though it never touched the parallel worker pool. It is now its own
job, `fast-tests-sync-orphan-sweep`, triggered by the same `sync` path filter
so it runs *concurrently* with `fast-tests-sync` instead of after it — still
serial (`-n0`, real ports are not protected by per-worker HOME isolation),
just no longer blocking a sibling job's completion. The equivalent serial
split exists on the integration side too:
`integration-tests-sync-real-port` carries the 3 other
`FIXED_RANGE_SUITES` members out of `integration-tests-sync`, which is
otherwise parallelized.

### `fast-tests-core-misc` — rebalanced 3-shard matrix

Already a shard matrix, but imbalanced (`specify-cli-rest` 12.2 min vs
`core-misc` 4.7 min). Rebalanced by splitting the heavy `specify-cli-rest`
leg's real subdirectories/files (measured via a real
`-m "fast and not windows_ci"` collect-only pass: 3241 of 6320 combined
tests) into a sibling `specify-cli-rest-2` shard — a plain path/`--ignore=`
bin-split (like the job's own existing `core-misc` residual pattern), not a
new `SHARD_GROUPS` registry row. `specify-cli-rest` keeps its
WP02-`_REQUIRED_CORE_MISC_SHARDS`-required name. Union verified unchanged
(3241 + 3079 == the pre-split 6320-test selection).

### `fast-tests-charter` / `fast-tests-agent` — split into concurrent jobs

`fast-tests-charter` (12.0 min) ran two sequential `-n auto` steps (charter,
then agent) that summed on one job's wall-clock despite each already being
parallel. `fast-tests-agent`'s historical `needs: fast-tests-charter` edge
was an ordering artifact, not a true cross-job data dependency (the two run
on separate runners with separate checkouts); it now mirrors
`fast-tests-charter`'s own upstream `needs` so both run concurrently.

### The serial `integration-tests-*` sweep

14 single-directory `integration-tests-*` jobs (`agent`, `charter`, `cli`,
`dashboard`, `doctrine`, `lanes`, `merge`, `missions`, `next`,
`post-merge`/`post_merge`, `release`, `review`, `status`, `sync`, `upgrade`)
now run `-n auto --dist loadfile -p no:cacheprovider`. `integration-tests-sync`
was split real-port-first the same way `fast-tests-sync` was: a parallel
residual plus a dedicated serial `integration-tests-sync-real-port` job.

### Real-port serial isolation is structural, not marker-only (closes #2590)

The fixed-range daemon family (`tests/_real_port_suites.FIXED_RANGE_SUITES`,
4 files under `tests/sync/` that bind `find_free_port_in_range`) is excluded
from every parallel pool with an explicit `--ignore=` entry, not just relying
on a module-level marker mismatching the job's `-m` filter — a marker-only
guarantee is not structural, and #2590 tracked exactly that gap. This is
enforced by `tests/architectural/test_serial_port_preservation.py` (GC-3,
generalized to consume the whole registry) and
`tests/architectural/test_workflow_dist_lint.py` (GC-4, C-002/C-007).

### Coverage-preservation guard (GC-2b)

Every re-topologized job's selection is checked against a **committed,
frozen pre-change baseline** of real `pytest --collect-only` node-ids
(`tests/architectural/baselines/<job>-nodeids.txt`,
`tests/architectural/test_gate_coverage.py`'s
`test_gc2b_current_selection_matches_baseline`) — 0 dropped, 0 double-run,
not merely "the same number of tests." See
[`ci-coverage-union-audit.md`](../plans/testing/ci-coverage-union-audit.md)
for the mission's own cross-cutting run of this guard, including one found
(non-coverage) gap.

### Sonar coverage-denominator exclusions

`sonar-project.properties`' `sonar.coverage.exclusions` now removes
one-shot migration/backfill glue (`src/specify_cli/migration/**`, the
singular sibling the plural-only `**/migrations/**` `sonar.exclusions` glob
misses), non-Python dashboard assets (`**/static/**`), and thin CLI
entrypoints (`**/__main__.py`) from the coverage percentage denominator
(files stay in issue/duplication/hotspot analysis — only the coverage% is
affected). **Known drift from the original spec:** `spec.md`'s FR-012 also
named `src/specify_cli/next/**` (the 3.3.0 deprecation shim) as a 4th
exclusion target; the shipped change only carries the first 3. Re-add
`src/specify_cli/next/**` in a follow-up if it is still an uncovered
deprecation shim at merge time — do not assume this doc drift is
intentional without checking.

### UI-e2e coverage feed

`ui-e2e.yml` now runs its Playwright-driven `tests/ui/` suite with
`--cov=src/specify_cli/dashboard`, producing `coverage-ui-e2e.xml`. Two
scope decisions are documented in that file rather than silently left
incomplete:
- **Python coverage is produced but not yet Sonar-consumed** — `ci-quality.yml`'s
  `sonarcloud` job only discovers artifacts from its own workflow run
  (`download-artifact@v8`, including its `prev_run` fallback scoped to
  `workflow_id: 'ci-quality.yml'`), which cannot see an artifact uploaded by
  the separate `ui-e2e.yml` workflow run. Wiring a `ui-e2e.yml`-scoped
  download step into `ci-quality.yml`'s `sonarcloud` job is a tracked
  fast-follow, not yet done.
- **JS coverage (`dashboard.js`, ~720 lines) is deferred** — no
  Playwright-CDP or nyc/istanbul instrumentation was wired in this mission
  (judged out of budget for the job's 15-minute timeout); the interim
  mitigation is the `**/static/**` Sonar coverage exclusion above, which
  removes `dashboard.js` from the denominator rather than crediting it with
  real coverage.
