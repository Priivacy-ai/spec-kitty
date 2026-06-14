# Phase 1 Behavioral Contracts — Test Suite Acceleration

This mission exposes no network API. The "contracts" are the behavioral
guarantees the work packages must satisfy and that reviewers verify. Each is
stated as a testable invariant with its acceptance check.

## C-ISO — Worker Home Isolation Contract

- **Guarantee**: Under xdist, each worker resolves a unique home; no test
  touches the real `~/.spec-kitty`.
- **Acceptance check**: A regression test spawns/simulates two worker IDs and
  asserts (a) distinct `Path.home()` results, (b) the real `~/.spec-kitty` is
  never created/modified during the run (assert real path mtime/inode unchanged
  or path absent). Maps to FR-002, SC-006.

## C-EQUIV — Collection Equivalence Contract

- **Guarantee**: For every flipped shard, the parallel run collects the exact
  same nodeid set as the serial run.
- **Acceptance check**: `pytest <shard> --collect-only -q` serial vs
  `-n auto --dist loadfile` produce identical sorted nodeid lists (or an
  explicitly asserted, reviewed delta). Maps to FR-004, NFR-007.

## C-RATCHET — Stability Ratchet Contract

- **Guarantee**: A parallelization flip is accepted only after N consecutive
  green parallel runs of the shard.
- **Acceptance check**: CI (or a local helper) runs the shard N=2–3 times under
  `-n auto`; all must pass with no new flakes before the flip merges. Maps to
  FR-012, NFR-005.

## C-VOLUME — Volume Gate Contract

- **Guarantee**: Default run uses reduced scale; full scale is reachable via env
  gate / nightly; assertion logic is identical across scales.
- **Acceptance check**: Test passes with env unset (reduced) and with env set
  (full); a CI/nightly path exercises the full scale. Maps to FR-008, C-004.

## C-READONLY — Read-Only Sharing Contract

- **Guarantee**: Shared/cached fixtures are never mutated by consumers;
  integrity/idempotency/freshness and counter/rollback tests are excluded.
- **Acceptance check**: The cached artifact's state is asserted unchanged after
  the shared tests run; excluded tests still use pristine per-test state. Maps to
  FR-009, C-007.

## C-SERIAL — Serial Pass Contract

- **Guarantee**: OS-global resource tests (real ports, daemons) run in a
  dedicated serial pass, not under parallel workers.
- **Acceptance check**: The port/daemon tests (e.g. `tests/sync/test_orphan_sweep.py`,
  ports 9400–9449) are invoked with `-n0` in their own step and are excluded
  from the parallel selector. Maps to FR-005.

## C-LOCAL — Local Command Contract

- **Guarantee**: The documented local command runs the suite in parallel safely
  and is at least 2× faster on a ≥4-core machine.
- **Acceptance check**: `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider`
  completes green (with the serial daemon pass run separately) and the real home
  is untouched. Maps to FR-001, FR-011, NFR-001, SC-001.

## C-NOPROD — No Production Signature Change Contract

- **Guarantee**: Test-speed changes do not alter production code signatures
  (e.g. sleep elimination is module-scoped patching).
- **Acceptance check**: Diff review confirms no `src/` public signature change
  attributable to test-speed work. Maps to C-006.
