# Tracer — Approach

Seeded at planning; appended during implementation; assessed at close.

## Planned approach

- **Pre-spec dual squad** (paula-patterns + python-pedro) verified all four issues un-drifted against HEAD
  `4e1e8ed34`, found 2 extra rosters (folded in) and a sequencing correction (#2667 before #2666), and mapped
  the exact consumers / blast radius / CI-gate coupling. Findings drove the spec directly.
- **Delivery in IC order** IC-1 (#2669) → IC-2 (#2667) → IC-3 (#2666) → IC-4 (#2668). IC-1a (accessor) is a
  tidy-first enabler; the roster derivations depend on it. IC-2 precedes IC-3 so the wired gate is non-vacuous.
  IC-4 (pure campsite refactor) lands last to absorb churn on shared lines.
- **ATDD red-first** per WP: the failing test goes in first through the pre-existing entry point (the roster
  consumers, `load_action_index`, `doctor doctrine`, the accessor call sites).
- **CI-only gate discipline:** reproduce the arch_shard_1 pole + terminology guard locally before push;
  DRG freshness check if discovery/graph changes.

## Deviations (append during implementation)

- _(none yet)_

## What actually happened (assess at close)

- All 6 WPs landed ATDD red-first, each independently reviewed (reviewer-renata). WP01 took one
  reject-cycle (a test-file ruff UP035 the source-only gate missed).
- The IC order held; the terminal WP06's aggregate arch pole surfaced a **cross-lane symbol collision**
  (WP05's new gate test imported the `CANONICAL_MISSION_TYPES` WP02 retired — invisible per-lane because
  WP05's lane predated WP02's retirement). Fixed at the merge pass.
- The **pre-merge aggregate review** earned its keep: it caught 3 aggregate-only regressions the per-lane
  reviews structurally could not see — a doctor RC=1 test made vacuous by WP06's accessor-seam change; an
  NFR-001 import-time-I/O regression from the C-012 module-scope derivation colliding with the eager
  `charter/__init__` chain; and a CI-scope ruff E501. The `__getattr__` true-zero fix was attempted and
  rejected (dead-symbol gate can't span a PEP-562 attribute) → honest ≤1-cached bound documented in the spec.
- Operator directed folding the residual `runtime/` rosters (home.py, show_origin.py) rather than deferring;
  done in an isolated worktree in parallel with the blocker fix. Only `kernel/paths.py` remains literal.
- Delivered as a clean 10-commit linear PR rebased on upstream/main (which had moved; its own #2651 landing
  fold overlapped our shard-map registration — reconciled during rebase).
