---
work_package_id: WP03
title: 'Executor: mark both sites + resume heal + restore primitive'
dependencies: 
- WP02
requirement_refs:
- FR-002
- FR-005
- FR-006
- FR-008
- FR-010
tracker_refs: []
planning_base_branch: fix/merge-coord-rollback-transactionality
merge_target_branch: fix/merge-coord-rollback-transactionality
branch_strategy: Planning artifacts for this mission were generated on fix/merge-coord-rollback-transactionality. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-coord-rollback-transactionality unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 3 - Integration
assignee: ''
agent: "claude"
shell_pid: "805610"
shell_pid_created_at: "1784394010.93"
history:
- at: '2026-07-18T14:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/executor.py
create_intent:
- tests/merge/test_executor_coord_reconcile.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/executor.py
- tests/merge/test_executor_coord_reconcile.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Executor: mark both sites + resume heal + restore primitive

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Wire the marker into the executor: mark-not-raise at **both** strand sites, a strand-gated resume
heal, and co-locate the mark at the restore **primitive** so a future restore site cannot strand
silently. This WP makes WP01's repros GREEN.

- **FR-005**: rollback marks on any strand (revert-failure ≈500-514 AND bake ≈406-408) via one `_persist_coord_reconcile_marker`; does NOT raise; leg-b byte-restore still runs.
- **FR-006**: dedicated `_heal_pending_coord_reconcile` at resume startup — strand-gated, atomic clear, idempotent; repair delegates to WP02's coordination primitive.
- **FR-008 (structural half)**: co-locate the mark at a `_restore_and_guard_coord_coherence` restore primitive (inner-only; the FR-008 *guard test* is WP05).
- **SC-006**: WP01's modified #2786 test now GREEN after the heal.
- **NFR-001**: non-aborting merge byte-identical; **INV-5 #1827** (`test_executor_phase_boundary.py`) green.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-005, FR-006, FR-008 (structural), FR-010 (SaaS fence — do NOT add a compensating emit); research [D2 (grain/INV-5), D4 (mark-not-raise), D5 (coherence-gated), D11 (enumeration)](../research.md).
- **Depends on WP02** — imports `MergeState.pending_coord_reconcile`, `coord_incoherent_done_wps`, and the repair primitive from `coordination/coherence.py`.
- **INV-5 #1827 inner-only**: all new logic lives inside existing phases / `_restore_*` sites, or at resume startup BEFORE the phase list. Do NOT wrap the phase driver. If the heal is inserted *within* the driver, do NOT add it to the frozen `expected_order` list in `tests/merge/test_executor_phase_boundary.py` (it would flip the ratchet red on a correct change).
- **AC-B3 / AC-F1**: repair is `git revert` via `_make_merge_env`; never raw `update-ref`; never `advance_branch_ref`.

### Code anchors (verified on base)
- `_record_merged_wps_done_for_merge` failure branch ≈406-408 (bake — byte-restore-without-revert).
- `_revert_coord_done_commit` failure branch ≈500-514 (revert swallowed) — refactor to delegate revert to WP02's primitive.
- `_restore_final_bookkeeping_snapshots` restores **primary** paths (`bookkeeping_projection.py`), not the coord worktree — so the marker derives the strand from the committed ref (via `coord_incoherent_done_wps`), NOT a worktree diff.
- `done_marked_before_target` ≈350-352 gates coord topology to the pre-target ordering (why the third restore site ≈691 is dead-for-coord).
- Resume path: `_reconcile_completed_wps_for_resume` — do NOT overload it; add a dedicated `_heal_pending_coord_reconcile`.

## Branch Strategy

- **Planning base branch**: `fix/merge-coord-rollback-transactionality`
- **Merge target branch**: `fix/merge-coord-rollback-transactionality`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T008 – Extract `_persist_coord_reconcile_marker`; mark at both strand sites

- **Purpose**: One helper writes the marker at both strands so neither is silently swallowed.
- **Steps**:
  0. **FIRST add a `_MergeRunState` field capturing this merge's pre-target done write-set** (the WPs it committed `done` during THIS merge), populated at the `_record_merged_wps_done_for_merge` bake site. This is the `candidate_wps` — do NOT pass `run.all_wp_ids` (on a resume it includes WPs a prior attempt legitimately baked `done` → the heal would revert a legitimately-done WP; see data-model derivation contract).
  1. `_persist_coord_reconcile_marker(run, error)` (CC≤15): compute `stranded_wp_ids = coord_incoherent_done_wps(coord_ref, run.pre_target_done_write_set)`; if non-empty, build the marker dict (coord_ref, captured_sha, coord_worktree, stranded_wp_ids, revert_error=str(error), detected_at) and `save_state`. Call `coordination.coherence.coord_incoherent_done_wps` — do NOT re-derive the coord reduction locally (that reopens the three-way drift → #2786-C).
  2. Reached via the T010 restore primitive at the ≈500-514 revert-failure branch AND the ≈406-408 bake branch (T010 is the primary mechanism — see there; no double-mark).
  3. **Mark-not-raise**: on the revert-failure branch, log+mark+continue (leg-b restore still runs). On the bake branch, mark BEFORE the re-raise so the strand is recorded.
- **Files**: `src/specify_cli/merge/executor.py`

### Subtask T009 – `_heal_pending_coord_reconcile` at resume startup

- **Purpose**: Heal the strand deterministically and idempotently on `--resume`.
- **Steps**:
  1. At resume startup, load `MergeState`; if `pending_coord_reconcile` present, call the WP02 repair primitive (strand-gated: it re-derives via `coord_incoherent_done_wps` and no-ops if already coherent).
  2. Clear the marker **atomically** with the heal (persist cleared state only after the revert commits). A crash between heal and clear → next resume re-derives coherent → no-op → clears (NFR-002).
  3. Dedicated entry — NOT an overload of `_reconcile_completed_wps_for_resume`.
- **Files**: `src/specify_cli/merge/executor.py`

### Subtask T010 – Restore-primitive co-location (FR-008 structural)

- **Purpose**: Convert "mark at two hand-picked callers" into "mark by construction at the restore seam" so a future restore site cannot strand silently. **This is the PRIMARY marking mechanism — T008's two marks are reached THROUGH this primitive, not added independently.**
- **Steps**:
  1. Introduce a thin `_restore_and_guard_coord_coherence(run, ...)` that wraps `_restore_final_bookkeeping_snapshots` and, when coord topology, invokes `_persist_coord_reconcile_marker` on any residual strand.
  2. Route **every** `_restore_final_bookkeeping_snapshots` call-site through it. There are **SEVEN** (≈407/536/670/691/701/757/786) — enumerate by grep, don't trust a remembered count. Site ≈691 is dead-for-coord (inside `if not run.done_marked_before_target:` ≈679); **site ≈701 (`_project_status_bookkeeping_to_target` failure) is OUTSIDE that guard → coord-reachable and MUST be routed + markable** (double-confirmed live strand). This is **inner** (not the phase-driver wrapper INV-5 forbids).
  3. Refactor `_revert_coord_done_commit` to delegate the actual `git revert` to WP02's coordination primitive (single repair authority).
- **Files**: `src/specify_cli/merge/executor.py`

### Subtask T011 – Executor integration tests

- **Purpose**: Cover the mark/heal branches directly + confirm the marker names the specific WP.
- **Steps**:
  1. New `tests/merge/test_executor_coord_reconcile.py`: drive a revert-failure strand and a bake strand; assert the marker is written with the correct `stranded_wp_ids` (specific WP, ≥2-WP fixture); include the **pre-existing-done exclusion** case (a WP `done` before this merge is NOT in `stranded_wp_ids`); assert mark-not-raise (leg-b restore ran).
  2. Assert `_heal_pending_coord_reconcile` heals to `committed == working` and clears the marker; run resume twice → byte-stable coord `status.events.jsonl`.
  3. Confirm WP01's repros now pass; confirm `test_executor_phase_boundary.py` still green.
- **Files**: `tests/merge/test_executor_coord_reconcile.py` (NEW)

## Definition of Done

- [ ] `_MergeRunState` carries this merge's pre-target done write-set; the marker's `candidate_wps` is that field, NOT `run.all_wp_ids`.
- [ ] Marker `stranded_wp_ids == [the_stranded_one]` on a ≥2-WP fixture (coherent WP excluded) AND a pre-existing-done WP is excluded — falsifies a hardcoded list and `all_wp_ids`.
- [ ] mark + heal call `coordination.coherence.coord_incoherent_done_wps`; executor.py does NOT re-derive the coord reduction locally (no inline `_durable_done_wps_on_coordination_ref`).
- [ ] Marker written via the `_restore_and_guard_coord_coherence` primitive; ALL seven `_restore_final_bookkeeping_snapshots` sites routed through it (incl. ≈701); mark-not-raise; leg-b byte-restore preserved.
- [ ] `_heal_pending_coord_reconcile` heals + clears atomically; resume-twice byte-identical (NFR-002).
- [~] `_revert_coord_done_commit` delegates to the WP02 primitive — **DEFERRED to [#2797]** (documented deviation, both reviewers concur). Full delegation breaks the pre-existing pinned `test_executor_option_a_revert_helpers_2711.py`, and a clean shared-transport helper crosses WP ownership boundaries (coherence.py is WP02-owned). The anti-drift invariant is still met: the single strand-**derivation** authority (`coord_incoherent_done_wps`) is shared by mark+heal+doctor; only the raw `git revert` *transport* is duplicated across two differently-gated legs. #2797 tracks unifying the transport.
- [ ] WP01 repros GREEN; `tests/merge/test_executor_phase_boundary.py` + `tests/specify_cli/merge/test_1827_baseline_regression.py` GREEN; heal NOT added to `expected_order`.
- [ ] Happy-path merge byte-identical (NFR-001); `ruff`/`mypy` clean; touched functions ≤ CC-15.
- [ ] No compensating SaaS emit added (FR-010 fence honored).

## Reviewer Guidance

Confirm the strand set is derived from the committed ref (not a worktree diff); mark-not-raise on the
revert branch (leg-b runs); heal is strand-gated and atomic-clear (a blind `git revert
captured_sha..HEAD` would re-apply `done` — reject that); INV-5 ratchet green and the heal is not in
`expected_order`; happy path byte-identical.

## Activity Log

- 2026-07-18T16:10:56Z – claude – shell_pid=696516 – Assigned agent via action command
- 2026-07-18T16:59:58Z – claude – shell_pid=696516 – Executor mark/heal/primitive: WP01 repros GREEN, 661 sweep pass, 7 sites routed (incl 701). Two deviations flagged (see review).
- 2026-07-18T17:00:19Z – claude – shell_pid=805610 – Started review via action command
- 2026-07-18T17:11:54Z – user – shell_pid=805610 – Dual-lens APPROVED (renata contracts + alphonso git-safety): DONE-coherence faithful, reset--hard bounded-safe, 7-site routing incl 701, WP01 repros green. DIR-044 transport-dedup documented+deferred to #2797.
