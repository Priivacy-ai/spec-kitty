# Tracer — Approach

Seeded at planning; append during implement; assess at close.

## Planned approach

- **Two-phase, single-subsystem** (`src/doctrine/drg`), **edges-first** (see research.md D-0 / DD-0 for why
  the order was reversed by the post-plan squad).
- **Phase 1 — edges (#2677), against the monolith.** IC-1 generator edge pass + regenerate; IC-2 tests/re-pin
  + orphan gate green + residual-doc reconcile. ATDD red-first: commit the edge/orphan assertions + the
  inverted `test_mission_type_nodes` first, then `extract_mission_type_edges`, then regenerate + commit
  `graph.yaml`. ~2 tight WPs.
- **Phase 2 — sharding (#2680), the migration.** IC-3, WP-split: (a) canonical `load_built_in_graph()` seam
  first, route ~22 readers; (b) generator per-populated-kind fragments + atomic monolith delete; (c) equality
  (merge-order contract) + partition-totality + 3 silent-degrade output proofs; (d) ~16 test-fixture +
  snapshot + docstring sweep. ATDD red-first: the equality/silent-degrade assertions before the monolith is
  deleted. Runs after Phase 1 so the orphan gate is already green when its reader is re-pointed. ~4 WPs.
- **Squad history:** pre-spec (architect) + post-spec (renata + paula) READY-TO-PLAN on the edges (18→10
  reproduced live; 21-edge + residual-10 folded); **post-plan** (architect + paula + renata) forced the
  resequence + the ~22-site sharding inventory (DD-0, DD-6..DD-10).

## Deviations (append during implementation)

- _(none yet)_

## What actually happened (assess at close)

- _(to be filled)_
