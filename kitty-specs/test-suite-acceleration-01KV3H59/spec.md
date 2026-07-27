# Test Suite Acceleration

**Mission ID**: 01KV3H590RHSQHF8XV843X5YHA
**Mission slug**: test-suite-acceleration-01KV3H59
**Mission type**: software-dev
**Status**: Draft

## Overview

The Spec Kitty pytest suite (~1,457 test files) is the slowest gate on every
change. Two structural problems cap its speed:

1. **No parallelism where it would help most.** The per-directory CI "fast"
   shards run single-process, and developers cannot safely run `pytest` across
   multiple processes locally because some tests read and truncate a **real**
   home-directory–backed queue database (`~/.spec-kitty/queue.db`). Running
   parallel workers today would corrupt that shared state.
2. **Redundant and over-scaled work.** A handful of tests explode into hundreds
   of collected items, rebuild expensive read-only state per test, repeat real
   `git init`, or run the same slow test in more than one CI job.

This mission executes a verified, adversarially-checked acceleration plan
(`architecture/test-suite-acceleration-plan.md`) to make the suite run **much
faster in both CI and local development** while guaranteeing **no real assertion
path or regression guard is weakened**. The plan was produced by a 43-agent
audit in which every recommendation passed an independent coverage-safety
verification pass.

The keystone is a **per-worker home/state isolation** capability: once each
parallel worker has its own home and config directories, both safe local
multi-process runs and the CI fast-shard parallelization become unblocked.

## User Scenarios & Testing

### Primary scenario — Developer runs the suite locally in parallel

1. A developer finishes a change and wants to validate it before pushing.
2. They run the single documented parallel command.
3. The suite distributes across all available CPU cores; OS-global resource
   tests (real ports/daemons) run in a dedicated serial pass.
4. The run completes in well under half the previous single-process wall-clock.
5. The developer's real `~/.spec-kitty` state is never read, written, or
   truncated by the run.

### Primary scenario — CI runs the fast shards in parallel

1. A pull request triggers CI.
2. The fast shards (charter, cli, sync, doctrine, agent, …) execute across
   multiple cores instead of single-process.
3. The same set of tests (identical collected node IDs) runs as before.
4. The slowest shard's wall-clock is at least halved, shortening the critical
   path that gates downstream jobs.

### Exception / edge scenarios

- **Worker collision attempt:** Two parallel workers must never share the real
  home-backed queue DB; each must resolve a distinct, isolated home.
- **CPU contention:** Timing-floor assertions (`elapsed < 0.1`) that flake under
  load are replaced by generous timeout guards that still trip a pathological
  regression.
- **Volume-sensitive guards:** Reduced-scale default tests must retain a
  full-volume variant (nightly / env-gated) so corruption- and
  uniqueness-detection power is not silently lost.
- **Integrity tests:** Idempotency, file-existence, and freshness tests must NOT
  be routed through any shared/cached fixture.
- **Distribution mode:** Parallel distribution must be file-pinned; bare
  work-stealing distribution would break file-local autouse resets.

### Rule playback (must always hold)

- The parallel suite collects the **identical node set** as the serial suite —
  no test is silently dropped.
- Coverage quality never decreases: no genuine assertion path or regression
  guard is deleted or weakened.
- A parallelization flip ships only after the affected shard is green on a
  repeated-run stability ratchet.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Developers can run the full test suite across multiple processes locally via one documented command, completing without corrupting any real home-directory state. | Draft |
| FR-002 | Test execution isolates per-worker home, config, and state directories so parallel workers never share or clobber the real `~/.spec-kitty` queue database or other home-backed state. | Draft |
| FR-003 | The CI fast test shards execute in parallel across available cores instead of single-process, beginning with the critical-path (charter) shard and rolling out shard-by-shard. | Draft |
| FR-004 | The parallelized suite collects and executes the identical set of tests (same node IDs) as the serial suite for each affected shard; a collection-equivalence check enforces this. | Draft |
| FR-005 | Tests depending on OS-global resources (real ports, daemons) run in a dedicated serial pass rather than under parallel workers. | Draft |
| FR-006 | Wall-clock timing-floor assertions that flake under CPU contention are converted to timeout-based guards that still catch pathological performance regressions, without deleting the functional assertions they accompany. | Draft |
| FR-007 | Redundant test execution is eliminated so that any given slow/performance test runs in exactly one CI job, with no orphaning of negative-path or NFR guard tests. | Draft |
| FR-008 | High-volume iteration tests (ULID generation volume, FSM parity matrix, sync concurrency loops) are reduced to a representative scale for the default run, with the full-volume variant preserved behind an environment gate or nightly path. | Draft |
| FR-009 | Expensive read-only setup (migrated-project state, whole-tree AST parse, dependency-graph load) is computed once and shared across tests that only read it, explicitly excluding integrity, idempotency, and freshness tests. | Draft |
| FR-010 | A cached/templated baseline git-repository fixture replaces repeated real `git init` for tests needing only a standard repo, while bespoke setups (unborn, detached, bare, worktree) retain their own initialization. | Draft |
| FR-011 | The documented local default test command and contributor guidance (CLAUDE.md) are updated to the parallel-capable invocation, including the serial-pass caveat for daemon/port tests. | Draft |
| FR-012 | Each parallelization change rolls out one shard at a time, gated by a repeated-run (run-twice or run-thrice) stability ratchet that must pass before the next shard is flipped. | Draft |
| FR-013 | The safe-now coverage-neutral quick wins (volume reduction, timing→timeout conversion, slow-test de-duplication, deterministic sleep elimination, verbose-flag removal in CI) ship as an initial wave independent of any parallelization dependency. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Local full-suite wall-clock improves on a multi-core developer machine. | ≥ 2× faster than the single-process baseline on a ≥4-core machine. | Draft |
| NFR-002 | The slowest CI shard's wall-clock is reduced. | Critical-path (charter) shard drops from ~9 min to ≤ 5 min. | Draft |
| NFR-003 | Per-push CI CPU time is reduced by the safe-now wave alone. | ≥ 60 s removed per push (volume reduction + slow-test de-dup), before any parallelization. | Draft |
| NFR-004 | Coverage quality is preserved. | New-code coverage stays ≥ 90%; overall line/branch coverage does not decrease versus baseline. | Draft |
| NFR-005 | Parallel runs are deterministic. | Affected suite passes on 3 consecutive parallel runs with zero new flaky tests. | Draft |
| NFR-006 | Added test infrastructure meets project quality gates. | `mypy --strict` and `ruff` pass with zero new issues; complexity ≤ 15. | Draft |
| NFR-007 | Collected test count is conserved across each change. | Per-shard collected node count is identical (or changes only by an explicitly asserted, reviewed delta) before vs. after. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | No real assertion path or regression guard may be deleted or weakened; every reduction must be coverage-neutral, verified by collection-count equivalence plus an equivalence or mutation check where behavior is restructured. | Draft |
| C-002 | All changes land via pull request to `origin/main`; no direct pushes to `origin/main` (repository policy). | Draft |
| C-003 | Parallel test distribution must be file-pinned (`--dist loadfile`), never bare work-stealing distribution, because file-local autouse registry/cache resets assume same-file co-location. | Draft |
| C-004 | Volume-sensitive stress/corruption/uniqueness guards must continue to run somewhere in CI (nightly or environment-gated); their high-volume power may not be silently removed. | Draft |
| C-005 | Per-worker isolation must function cross-platform (Linux, macOS, Windows), covering `HOME`, `USERPROFILE`, and `LOCALAPPDATA`. | Draft |
| C-006 | Production code signatures must not be altered merely to satisfy tests (e.g., deterministic sleep elimination is achieved by module-scoped patching, not by changing production behavior). | Draft |
| C-007 | Integrity, idempotency, file-existence, and freshness tests are excluded from any shared/cached fixture or de-duplication. | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A developer runs one documented command and the full suite finishes in under half the previous wall-clock on a 4-core machine, with their real `~/.spec-kitty` state untouched. |
| SC-002 | The slowest CI shard's wall-clock is at least halved relative to the pre-mission baseline. |
| SC-003 | Coverage percentage does not drop and no test is silently dropped: per-shard collected node counts are equal (or differ only by a reviewed, asserted amount). |
| SC-004 | Three consecutive parallel CI runs of the affected shards are green with no new flaky tests. |
| SC-005 | The safe-now wave removes ≥ 60 s of CI CPU per push with zero change to coverage. |
| SC-006 | Running the suite in parallel with no worker isolation is demonstrably prevented from touching real home state (a regression test proves two workers resolve distinct homes). |

## Key Entities

- **Per-worker isolation fixture** — redirects each parallel worker's home and
  state directories to a worker-unique temporary location; the master enabler
  for both local and CI parallelism.
- **CI shard** — a CI job running a subset of tests; "fast" shards (currently
  serial) and "integration" shards (already parallel) are the two families.
- **Templated baseline git-repo fixture** — a once-built repo template cloned
  per test to replace repeated real `git init`.
- **Volume gate** — an environment switch (e.g. a `*_FULL` flag) that restores
  full-volume iteration for nightly/opt-in runs while the default run uses a
  representative scale.
- **Stability ratchet** — a repeated-run gate that must pass before a
  parallelization flip is accepted.
- **Coverage-equivalence check** — a collection-count/mutation safeguard proving
  a change is coverage-neutral.

## Assumptions

- `pytest-xdist` is already a project dependency and the `-n auto --dist
  loadfile` pattern is already proven in production on the integration shards;
  this mission extends that proven pattern, it does not introduce it.
- `architecture/test-suite-acceleration-plan.md` (the 43-agent verified audit)
  is the authoritative source for the specific files, hazards, and safeguards;
  this spec captures the WHAT/WHY and that document captures the evidence.
- The numeric timing figures in the audit (e.g. charter ~9.1 min, ULID ~36 s)
  are estimates to be **re-measured** during implementation; the NFR thresholds
  are the binding targets.
- The repository's no-direct-push and 90%-new-code-coverage policies remain in
  force throughout.

## Out of Scope

- Rewriting or re-architecting production (non-test) code for performance.
- Changing the set of behaviors the suite verifies (adding or removing product
  features).
- Migrating to a different test runner or CI provider.
- Converting the 315 subprocess-based tests to in-process wholesale; only the
  specifically identified, coverage-safe conversions are in scope.
