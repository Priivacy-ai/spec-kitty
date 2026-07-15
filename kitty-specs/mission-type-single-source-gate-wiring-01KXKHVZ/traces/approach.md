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

- _(to be filled at mission close)_
