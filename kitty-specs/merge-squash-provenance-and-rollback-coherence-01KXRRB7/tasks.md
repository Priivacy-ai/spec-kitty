# Tasks: Merge squash provenance + rollback/resume coherence (P0 #2709/#2711)

**Mission**: `merge-squash-provenance-and-rollback-coherence-01KXRRB7`
**Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)
**Base/target branch**: `fix/red-handling-policy-and-drg-regression-marks`

Two **decoupled chains** under one mission (squad re-slice). Red-first per chain; either
chain lands independently. Critical path = the #2711 chain.

```
#2709:  WP01 ── WP03 ── WP05
#2711:  WP02 ── WP04 ── WP06
```

## Work Packages

| WP | Title | Chain | Depends on | Key FR/IC |
|----|-------|-------|-----------|-----------|
| WP01 | Red-first repro: squash clobbers target-newer provenance | #2709 | — | FR-001, IC-01 |
| WP02 | Red-first repro: rollback/resume incoherence + duplicate `done` | #2711 | — | FR-002, IC-01 |
| WP03 | Squash artifact reconciliation (meta.json field-driver spike-first, traces union, projection union + status.json, driver wiring) | #2709 | WP01 | FR-003/004/005, C-006, IC-02/03 |
| WP04 | Rollback/resume coherence — Option A coord-`done`-revert + durable-log resume | #2711 | WP02 | FR-006/007, IC-04 |
| WP05 | Class-closing guard: driver-registry-completeness + no-blind-copy lint | #2709 | WP03 | FR-008, IC-05 |
| WP06 | Class-closing guard: resume non-reemission invariant | #2711 | WP04 | FR-008, IC-05 |

## Work Package Sections

### WP01 — Red-first repro: squash clobbers target-newer provenance (#2709)
Chain #2709 root. Test-only. Depends on: none. FR-001, IC-01. See `tasks/WP01-red-repro-squash-provenance.md`.

### WP02 — Red-first repro: rollback/resume incoherence + duplicate done (#2711)
Chain #2711 root. Test-only. Depends on: none. FR-002, IC-01. See `tasks/WP02-red-repro-rollback-resume.md`.

### WP03 — Squash artifact reconciliation (#2709)
meta.json field-driver (spike-first), traces union, projection union + status.json, driver wiring. Depends on: WP01. FR-003/004/005, C-006, IC-02/03. See `tasks/WP03-squash-reconciliation.md`.

### WP04 — Rollback/resume coherence (#2711), Option A
Coord-`done`-revert via `resolve_placement_only(...).ref` + `advance_branch_ref`; durable-log resume via `coordination_branch_ref`. Depends on: WP02. FR-006/007, IC-04. See `tasks/WP04-rollback-resume-coherence.md`.

### WP05 — Class-closing guard (#2709)
Driver-registry-completeness + no-blind-copy AST lints. Depends on: WP03. FR-008, IC-05. See `tasks/WP05-class-guard-2709.md`.

### WP06 — Class-closing guard (#2711)
Resume non-reemission invariant. Depends on: WP04. FR-008, IC-05. See `tasks/WP06-class-guard-2711.md`.

## Shared-surface coordination (resolved)

`src/specify_cli/merge/bookkeeping_projection.py` is owned **wholly by WP03** (the FR-005
projection change). **WP04 does NOT edit this file** — Option A's coord-`done`-revert and
ref-SHA capture both land in `merge/executor.py` (`_restore_pre_target_if_at_baseline` +
snapshot-capture site), and WP04 consumes `bookkeeping_projection.py`'s capture/restore
functions read-only. `owned_files` are therefore file-level disjoint — no overlap, no missing
WP04→WP03 edge. (If an implementer chooses to fold the ref-SHA capture INTO
`_capture_bookkeeping_snapshots`, that would touch WP03's file — in that case add a WP04→WP03
dependency; the default plan avoids it.)

## Cross-cutting constraints (all WPs)

- **Rebase-first (C-003)** and **re-resolve every cited `file:line` by SYMBOL** — the merge
  core was freshly refactored (#2057/#2173/#2632/#2675).
- **Terminology canon (C-005):** `Mission` not `feature`; `--mission`.
- **Route through canonical seams:** coord-ref via `resolve_placement_only(..., kind=MissionArtifactKind.STATUS_STATE).ref`;
  committed-ref reduce via `read_event_log(EventLogReadContract.coordination_branch_ref(...))`
  + `wp_lane_actor_from_events()`; target write-back via the `trusted_*` paths from
  `_target_bookkeeping_status_paths`. Do NOT author new resolvers/reducers/path grammars.
- **INV-5 #1827 ratchet homes** (`tests/merge/test_executor_phase_boundary.py`,
  `tests/specify_cli/merge/test_1827_baseline_regression.py`) and **AC-B3/AC-F1 lints**
  (`tests/architectural/test_merge_pipeline_ratchets.py`) must stay green.
- **Tracker:** #2709/#2711 assigned to HiC; issue-matrix records the #2770-unrelated
  verification and the recommend-single-priority note.
