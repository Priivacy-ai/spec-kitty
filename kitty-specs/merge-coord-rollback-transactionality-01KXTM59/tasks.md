# Tasks: Merge coord-write rollback transactionality (#2786 + #2367-B)

**Mission**: `merge-coord-rollback-transactionality-01KXTM59`
**Planning base / merge target**: `fix/merge-coord-rollback-transactionality` → consolidate → local `main` → `pr/<slug>` PR
**Inputs**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md)

Five work packages. **Single-PR landing unit** — WP01's red repros stay red until WP03 lands; do NOT
split the repros from the fix (a lone WP01 would open a red-`main` window). Ownership is file-disjoint:
executor.py's mark + heal + restore-primitive all land in one WP (WP03) because a file cannot be
co-owned.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Modify existing `test_issue_2786_*` assertion → assert coherence AFTER heal (SC-006) | WP01 | | [D] |
| T002 | New `test_issue_2367_bake_strand.py` — inject failure inside `_record_merged_wps_done_for_merge` after ≥1 committed `done` (≥2-WP fixture) | WP01 | [D] |
| T003 | Assert committed-ref split-brain via `_durable_done_wps_on_coordination_ref` (git-reducible reds only; NO marker/doctor asserts here) | WP01 | | [D] |
| T004 | Add `MergeState.pending_coord_reconcile: dict[str,Any]\|None` + `from_dict` passthrough; canonical runtime state path | WP02 | | [D] |
| T005 | New `coordination/coherence.py` — `coord_incoherent_done_wps(coord_ref, candidate_wps)` (committed-ref authority) | WP02 | | [D] |
| T006 | Coordination-homed `git revert` repair primitive (env via `_make_merge_env`; NOT `advance_branch_ref`) | WP02 | | [D] |
| T007 | `tests/coordination/test_coherence.py` — ≥2-WP fixture: `stranded_wp_ids == [the_stranded_one]`, coherent WP excluded | WP02 | [D] |
| T008 | Extract `_persist_coord_reconcile_marker(run, error)` (CC≤15); mark at BOTH strand sites (≈500-514 revert-fail AND ≈406-408 bake); mark-not-raise | WP03 | | [D] |
| T009 | `_heal_pending_coord_reconcile` at resume startup — strand-gated (committed-ref DONE), atomic clear, idempotent; delegate revert to WP02 primitive | WP03 | | [D] |
| T010 | Co-locate the mark at a `_restore_and_guard_coord_coherence` restore primitive (inner-only, INV-5-safe); refactor `_revert_coord_done_commit` to delegate | WP03 | | [D] |
| T011 | `tests/merge/test_executor_coord_reconcile.py` — mark/heal integration + marker-names-specific-WP; make WP01 repros green | WP03 | | [D] |
| T012 | Register `_check_stranded_coord_revert` into `_collect_coordination_findings` (loads MergeState, re-verifies via `coord_incoherent_done_wps`, stable `error_code`, exit 1) | WP04 | | [D] |
| T013 | `_fix_stranded_reverts` into the existing `--fix` dispatch (delegates to WP02 repair primitive) | WP04 | | [D] |
| T014 | Doctor tests: positive (marker+strand→exit 1) AND negative (marker present + ref-coherent→exit 0) | WP04 | [D] |
| T015 | Behavioral class-closing guard — reds under a runtime-stubbed mark driving a real bake strand | WP05 | | [D] |
| T016 | Enumerate (AST) the seven `_restore_final_bookkeeping_snapshots` sites; assert ≈691 dead-for-coord AND ≈701 coord-reachable-and-routed | WP05 | [D] |

---

## Phase 1 — Red-first reproduction

### WP01 — Red-first repros (git-reducible reds only)

- **Goal**: Prove both strands (#2786 revert-failed, #2367-B revert-never-called) with assertions whose surfaces exist today; un-break the permanently-red existing #2786 assertion.
- **Priority**: P0 · **Profile**: debugger-debbie
- Dependencies: none (first)
- **Independent test**: `PWHEADLESS=1 pytest tests/regression/test_issue_2786_revert_failure_split_brain.py tests/regression/test_issue_2367_bake_strand.py` — RED on the mission base for the *product* reason (not `AttributeError`).
- **Subtasks**: T001, T002, T003
- **Risk**: marker/doctor asserts do NOT belong here (surfaces absent → setup-red, forbidden by ADR 2026-07-17-1). Expected-red until WP03. #2367-B must inject on the **bake** path only.

## Phase 2 — Foundations (marker + coherence owner + repair primitive)

### WP02 — MergeState marker + single coherence owner + repair primitive

- **Goal**: Add the durable marker field, the ONE coordination-layer coherence owner, and the coordination-homed `git revert` repair primitive — consumed by WP03 (executor) and WP04 (doctor).
- **Priority**: P0 · **Profile**: python-pedro
- Depends on WP01
- **Independent test**: `pytest tests/coordination/test_coherence.py` — ≥2-WP fixture; `coord_incoherent_done_wps` returns exactly the stranded WP (coherent excluded), falsifying a hardcoded `["WP01"]` and an over-broad `all_wp_ids`.
- **Subtasks**: T004, T005, T006, T007
- **Risk**: `stranded_wp_ids` derives from the **committed coord ref** over *this merge's* write-set — never a live worktree diff (empty at the #2786 mark point). Repair is `git revert`, NOT `advance_branch_ref`.

## Phase 3 — Integration (parallel: executor + doctor)

### WP03 — Executor: mark both sites + resume heal + restore primitive

- **Goal**: Mark-not-raise at both strand sites, strand-gated resume heal, and co-locate the mark at the restore primitive so a future restore site cannot strand silently. Makes WP01's repros green.
- **Priority**: P0 · **Profile**: python-pedro
- Depends on WP02
- **Independent test**: `pytest tests/merge/test_executor_coord_reconcile.py` + WP01 repros now GREEN; `tests/merge/test_executor_phase_boundary.py` (INV-5) stays green.
- **Subtasks**: T008, T009, T010, T011
- **Risk**: INV-5 #1827 inner-only — do NOT add the heal to the frozen `expected_order` list; repair delegates to WP02's primitive (no raw `update-ref`, AC-B3); NFR-001 happy-path byte-identical.

### WP04 — Doctor: canonical coordination check + `--fix`

- **Goal**: Register the stranded-revert detector + fix into the canonical `_coordination_doctor.py` surface (NOT a new `doctor/` home), re-verifying incoherence from the committed ref.
- **Priority**: P1 · **Profile**: implementer-ivan · parallel with WP03
- Depends on WP02
- **Independent test**: `pytest tests/specify_cli/cli/commands/test_coordination_doctor.py` — positive (marker+strand→exit 1 stable `error_code`) AND negative (marker present + ref-coherent→exit 0).
- **Subtasks**: T012, T013, T014
- **Risk**: canonical surface only (DIR-044 — no second authority); `--fix` delegates to WP02's repair primitive; the negative AC is the one that separates re-verification from marker-presence.

## Phase 4 — Class-closing guard

### WP05 — Behavioral class-closing invariant guard

- **Goal**: Prove the whole class is closed — any rollback leaving a stranded `done` on the committed ref MUST leave a durable marker — behaviorally, not by source-grep.
- **Priority**: P1 · **Profile**: reviewer-renata
- Depends on WP03
- **Independent test**: `pytest tests/architectural/test_coord_rollback_coherence_guard.py` — reds under a runtime-stubbed mark driving a real bake strand; green with the real mark.
- **Subtasks**: T015, T016
- **Risk**: must be a runtime behavioral falsifier (a source-grep-for-the-call guard is a tautology and is rejected); enumerate the six restore sites + assert ≈691's topology-gating.

---

## Dependencies

```
WP01 ─→ WP02 ─→ WP03 ─→ WP05
                └→ WP04            (WP04 ∥ WP03; both depend only on WP02)
```

## MVP scope

WP01→WP02→WP03 is the split-brain fix (closes #2786 + #2367-B). WP04 (operator detectability) and
WP05 (class-closing proof) complete the durable safety net. All five land in **one PR**.
