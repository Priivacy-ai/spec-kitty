# Phase 1 Contracts — Guard Invariants

This mission's "contracts" are the **architectural-guard invariants** enforced in CI (there is no HTTP/API surface). Each is a committed test that fails the build on violation.

## GC-1 — Shard partition (per group)
`test_<group>_shard_marker_completeness.py` (parametrized over the E1 registry):
- Every eligible collected item under the group's roots carries **exactly one** `<prefix>_<n>` marker.
- `shard_for(relpath)` is `None` outside the group's roots.
- Arch's assignment is unchanged (regression guard).

## GC-2 — Coverage preservation (execution, not just assignment)
`_gate_coverage.same_tier_shard_counts` + orphan ratchet + `test_required_selection_structures_present`:
- Each test in a sharded tier is selected by **exactly one** shard leg (parsed from the workflow YAML).
- Every `<prefix>_<n>` appears as a **required matrix leg** (`_REQUIRED_*_SHARDS`) — a shard with no leg fails.
- **Baseline diff (GC-2b):** post-change executed union == committed E3 baseline (symmetric-difference == ∅) for every re-scoped/sharded job — 0 dropped, 0 double-run.
- **Cross-job disjointness:** the serial `-n0` orphan-sweep job's selection ∩ the parallel pool's selection == ∅.

## GC-3 — Serial real-port isolation
`test_serial_port_preservation.py` (consumes E2):
- No file in `FIXED_RANGE_SUITES` is collected under any `-n auto` job.
- A serial `-n0` pass covering the family exists.
- No bare `--dist load` (fault-injected negative case).

## GC-4 — Workflow distribution lint (C-001/C-002/C-007)
`test_workflow_dist_lint.py` (parses `.github/workflows/*.yml`):
- No bare `--dist load`.
- Every `-n auto` run carries `--dist loadfile`.
- Fixed-range suites (E2) never appear under `-n auto`.
- Every sharded matrix sets `strategy.fail-fast: false` (C-006).

## GC-5 — Marker-baseline stability (C-005)
`test_marker_baseline.py`:
- The count/identity of `@slow` / `@stress` / `@quarantine`-marked tests does **not grow** vs a committed baseline during this mission (budget-motivated re-marking is surfaced for review).

## GC-6 — Coverage-exclusion scope (WP-J)
- `sonar.coverage.exclusions` contains only the E5 glob set; a review check confirms no core-Python path is added. (Enforced by review + the exclusion list's own comment rationale, not a runtime test.)

**Consumer**: GitHub Actions `quality-gate` job aggregates `needs.*.result == 'success'` (fail-closed). All guards run in the architectural gate.
