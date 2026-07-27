---
work_package_id: WP04
title: 'Doctor: canonical coordination check + --fix'
dependencies: 
- WP02
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: fix/merge-coord-rollback-transactionality
merge_target_branch: fix/merge-coord-rollback-transactionality
branch_strategy: Planning artifacts for this mission were generated on fix/merge-coord-rollback-transactionality. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-coord-rollback-transactionality unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
phase: Phase 3 - Integration
assignee: ''
shell_pid_created_at: "1784392503.55"
agent: "claude"
shell_pid: "749761"
history:
- at: '2026-07-18T14:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/_coordination_doctor.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_coordination_doctor.py
- tests/specify_cli/cli/commands/test_coordination_doctor.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Doctor: canonical coordination check + --fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Make the strand operator-detectable and repairable via the **canonical** coordination-doctor surface,
re-verifying incoherence from the committed ref (never trusting marker-presence).

- **FR-007**: register `_check_stranded_coord_revert` into `_collect_coordination_findings` (loads `MergeState`, re-verifies via `coord_incoherent_done_wps`, stable `error_code`, exit 1); `_fix_stranded_reverts` into the existing `--fix` dispatch.
- **US2-S5 (negative AC)**: marker present but the committed ref re-derives coherent → exit 0 / no finding. This is the AC that separates re-verification from marker-presence — a doctor reporting on marker-presence alone FAILS it.
- **DIR-044**: canonical surface only — no second coordination-doctor home under `src/specify_cli/doctor/`.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-007, US2 scenarios 4–5; research [D6 (re-verify), D9 (canonical surface)](../research.md).
- **Depends on WP02** — imports `coord_incoherent_done_wps` + the repair primitive from `coordination/coherence.py`. Does NOT depend on WP03 (doctor is an independent detection/fix surface); can run in parallel with WP03.
- The doctor tests may construct a `pending_coord_reconcile` marker directly in a fixture (no full merge needed).

### Code anchors (verified on base)
- `src/specify_cli/cli/commands/_coordination_doctor.py` — `run_coordination_health` (≈611), `_collect_coordination_findings` (≈525), `_emit_coordination_findings` + `DoctorFinding.error_code` (≈56/595), `--fix` dispatch `_fix_never_created_branches` (≈550) — mirror this for `_fix_stranded_reverts`.
- Existing tests: `tests/specify_cli/cli/commands/test_coordination_doctor.py` — extend, don't fork.

## Branch Strategy

- **Planning base branch**: `fix/merge-coord-rollback-transactionality`
- **Merge target branch**: `fix/merge-coord-rollback-transactionality`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T012 – `_check_stranded_coord_revert` detection

- **Purpose**: A coordination finding that re-verifies the strand from git, not from the marker.
- **Steps**:
  1. Enumerate markers via WP02's `iter_pending_coord_reconcile_markers(repo_root)` — do NOT call `load_state(mission_id=None)` (it *raises* `MergeAmbiguousStateError` on ≥2 markers) and do NOT re-implement the runtime-path scan (that is a second path authority / DIR-044 breach). For each `pending_coord_reconcile`, re-derive `coord_incoherent_done_wps(coord_ref, marker.stranded_wp_ids)`.
  2. If a strand remains → emit a `DoctorFinding` with a stable `error_code` (e.g. `COORDINATION_STRANDED_COORD_REVERT`) and exit 1. If the ref is coherent → NO finding (stale marker).
  3. Register into `_collect_coordination_findings` (do NOT create a new module).
- **Files**: `src/specify_cli/cli/commands/_coordination_doctor.py`

### Subtask T013 – `_fix_stranded_reverts` repair

- **Purpose**: `doctor coordination --fix` heals the strand via the shared primitive.
- **Steps**:
  1. Add `_fix_stranded_reverts` to the existing `--fix` dispatch, delegating to WP02's coordination repair primitive (strand-gated; atomic marker clear).
  2. `run_coordination_health` already carries an inline fix/re-collect block — extract `_apply_coordination_fixes(findings, repo_root)` so adding this second fixer keeps the dispatch ≤ CC-15.
- **Files**: `src/specify_cli/cli/commands/_coordination_doctor.py`

### Subtask T014 – Doctor tests (positive + negative)

- **Purpose**: Pin the re-verification contract.
- **Steps**:
  1. Positive: marker + a still-`DONE`-on-ref strand → `doctor coordination --json` exits 1 with the stable `error_code`; `--fix` restores `committed == working`.
  2. **Negative (the separator)**: marker present but ref re-derives coherent → exit 0, no finding. A marker-presence-only implementation fails this.
  3. Idempotency: `--fix` twice → byte-stable coord log, marker cleared once.
- **Files**: `tests/specify_cli/cli/commands/test_coordination_doctor.py`

## Definition of Done

- [ ] Check + fix registered in the canonical `_coordination_doctor.py` (no new `doctor/` home).
- [ ] Markers enumerated via WP02's `iter_pending_coord_reconcile_markers` (NOT `load_state(None)`, NOT a re-implemented runtime-path scan); a ≥2-marker case is tested.
- [ ] Positive AND negative doctor tests green; `--fix` idempotent.
- [ ] Re-verification reads the committed ref (via `coord_incoherent_done_wps`), never marker-presence.
- [ ] `_apply_coordination_fixes` extracted; `ruff`/`mypy` clean; fix-dispatch ≤ CC-15.
- [ ] No executor.py / state.py / coherence.py edits (owned by WP02/WP03).

## Reviewer Guidance

The load-bearing check is the **negative** AC — confirm a marker-present-but-coherent case exits 0.
Confirm the finding uses a stable `error_code`, the fix delegates to the shared primitive (no
re-implemented revert), and everything lands in the canonical surface (no second authority).

## Activity Log

- 2026-07-18T16:11:45Z – claude – shell_pid=699757 – Assigned agent via action command
- 2026-07-18T16:27:14Z – claude – shell_pid=699757 – Doctor check+fix: positive/negative/idempotency green (52 passed)
- 2026-07-18T16:27:39Z – claude – shell_pid=735356 – Started review via action command
- 2026-07-18T16:34:42Z – user – Moved to planned
- 2026-07-18T16:35:18Z – claude – shell_pid=749761 – Started implementation via action command
- 2026-07-18T16:37:34Z – claude – shell_pid=749761 – review-cycle-1 fix applied
- 2026-07-18T16:40:32Z – user – shell_pid=749761 – review-cycle-2 APPROVED: noqa MUST-FIX resolved (0 noqa, ruff/mypy clean, 52 passed)
