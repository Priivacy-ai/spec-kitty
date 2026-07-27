---
work_package_id: WP05
title: Behavioral class-closing invariant guard
dependencies: 
- WP03
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: fix/merge-coord-rollback-transactionality
merge_target_branch: fix/merge-coord-rollback-transactionality
branch_strategy: Planning artifacts for this mission were generated on fix/merge-coord-rollback-transactionality. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-coord-rollback-transactionality unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 4 - Class-closing guard
assignee: ''
agent: "claude"
shell_pid: "858430"
shell_pid_created_at: "1784395465.77"
history:
- at: '2026-07-18T14:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_coord_rollback_coherence_guard.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_coord_rollback_coherence_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Behavioral class-closing invariant guard

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `reviewer-renata`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Prove the whole defect class is closed — **behaviorally**. The guard must red when the mark is
stubbed out, not merely check that a mark call exists in source.

- **FR-008 / SC-005**: the guard reds under a **runtime-stubbed** mark (stub `_persist_coord_reconcile_marker`/`coord_incoherent_done_wps` to a no-op, drive a real bake-path strand, assert `strand-on-ref ∧ marker-absent`). A source-grep-for-the-call guard is a tautology and is **rejected**.
- Enumerate all six `_restore_final_bookkeeping_snapshots` sites (≈406/536/670/691/757/786) and assert site ≈691 is dead-for-coord only via `done_marked_before_target` (≈350-352) — so a future refactor that flips that invariant is caught.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-008, SC-005; data-model [INV-COORD-ROLLBACK + enumeration](../data-model.md); research [D11](../research.md).
- **Depends on WP03** — the mark behavior + restore primitive it exercises must exist.
- INV-COORD-ROLLBACK is **behavioral**, so the guard must be behavioral. Do not assert on source text of the mark call.

### Code anchors
- The six restore sites in `src/specify_cli/merge/executor.py`; `done_marked_before_target` ≈350-352.
- Reuse the bake-strand harness pattern from WP01 / `tests/merge/test_executor_coord_reconcile.py`.

## Branch Strategy

- **Planning base branch**: `fix/merge-coord-rollback-transactionality`
- **Merge target branch**: `fix/merge-coord-rollback-transactionality`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T015 – Behavioral falsifier

- **Purpose**: The guard proves the marker path actually fires — by breaking it and observing the class reopen.
- **Steps**:
  1. New `tests/architectural/test_coord_rollback_coherence_guard.py`.
  2. Drive a real bake-path strand (reuse the WP03 harness). Assert the invariant checker finds coherence (marker written → strand healed/recorded) with the real mark.
  3. `monkeypatch` `_persist_coord_reconcile_marker` (and/or `coord_incoherent_done_wps`) to a no-op, re-drive the strand, and assert the checker now finds `strand-on-ref ∧ marker-absent` → the guard REDs. This is the non-vacuity proof.
- **Files**: `tests/architectural/test_coord_rollback_coherence_guard.py` (NEW)

### Subtask T016 – Restore-site enumeration + topology-gating assertion

- **Purpose**: Make the guard class-closing over the enumeration, not just the two hand-picked sites.
- **Steps**:
  1. Enumerate the `_restore_final_bookkeeping_snapshots` call-sites **programmatically** — AST/regex over `executor.py`, NEVER a hardcoded count or line numbers (they drift as WP03 inserts helpers). There are **SEVEN** today (≈407/536/670/691/701/757/786).
  2. Assert every site that can run under coord topology routes through `_restore_and_guard_coord_coherence` (the marking primitive).
  3. Assert site ≈691 is reachable for coord only when `done_marked_before_target` is False (dead-for-coord); **assert site ≈701 (`_project_status_bookkeeping_to_target` failure) IS coord-reachable and IS routed through the primitive** — it is the live same-shape site my six-site list missed (double-confirmed). A new same-shape site added later that is NOT routed must red this test.
- **Files**: `tests/architectural/test_coord_rollback_coherence_guard.py`

## Definition of Done

- [ ] Guard REDs under a runtime-stubbed mark and GREENs with the real mark (behavioral non-vacuity).
- [ ] Restore sites enumerated **programmatically** (AST/regex, no hardcoded count/line-numbers); ≈691 asserted dead-for-coord AND ≈701 asserted coord-reachable-and-routed.
- [ ] `@pytest.mark.regression` (+ appropriate arch marker); references FR-008.
- [ ] `pytest tests/architectural/test_pytest_marker_convention.py` green; `ruff`/`mypy` clean.
- [ ] Tests only — no production edits.

## Reviewer Guidance

The single most important check: does the guard actually RED when the mark is stubbed to a no-op? If
it stays green under a stubbed mark, it is a tautology — reject. Confirm the enumeration is programmatic
(seven sites today), ≈701 is asserted coord-reachable-and-routed (not omitted like the original
six-site list), and ≈691's dead-for-coord gating is asserted — so the guard closes the class, not just
the two known sites.

## Activity Log

- 2026-07-18T17:12:33Z – claude – shell_pid=831250 – Assigned agent via action command
- 2026-07-18T17:24:35Z – claude – shell_pid=831250 – Behavioral class-closing guard: reds under stubbed mark, AST enumeration (7 sites, 701 routed, 691 dead-for-coord); 10 passed
- 2026-07-18T17:24:43Z – claude – shell_pid=858430 – Started review via action command
- 2026-07-18T17:31:02Z – user – shell_pid=858430 – Review passed (pedro): non-vacuity independently verified (reds under stubbed/deleted mark), AST enumeration drift-proof (7 sites, 701 routed, 691 dead-for-coord)
