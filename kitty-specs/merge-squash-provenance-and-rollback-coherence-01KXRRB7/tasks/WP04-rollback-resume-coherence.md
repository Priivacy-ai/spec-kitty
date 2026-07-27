---
work_package_id: WP04
title: 'Rollback/resume coherence (#2711): Option A coord-done-revert + durable-log resume'
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-007
- NFR-002
tracker_refs:
- '2711'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
phase: Phase 2 - Fix (#2711 chain)
assignee: ''
agent: "claude"
shell_pid: "3874028"
shell_pid_created_at: "1784354365.14"
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/executor.py
- src/specify_cli/merge/done_bookkeeping.py
- src/specify_cli/merge/state.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Rollback/resume coherence (#2711), Option A

## Objective
Make WP02 green: on a target-advance failure, rollback must leave committed and working
per-WP status coherent, and `--resume` must derive progress from the durable event log
without duplicating transitions.

## Open question — resolve FIRST (T009)
Confirm, by reading the code: (a) the pre-target `done` commit is made via `git commit`
inside `BookkeepingTransaction` (vs an `update-ref` path) — governs whether AC-B3 binds the
revert; and (b) `_read_contract_from_transaction_target` (`status_transition.py:680-693`)
reads the coord **worktree** leg when the worktree exists — Option A's "coherence restores
dedup for free" depends on this. Record findings in the tracer/design-decisions file.

## Fix (Option A — decided; Option B rejected: it fights the INV-5 #1827 ordering ratchet)
- **T010 — coherent rollback (FR-006).** Capture the coord-branch ref SHA **before** the
  pre-target `done` emit (not captured today; `pre_target_bookkeeping_snapshots` holds working
  bytes only). Source the ref-to-revert from `resolve_placement_only(repo_root, slug, kind=MissionArtifactKind.STATUS_STATE).ref`
  — the canonical write-target the `done` commit used; **NOT** an inline `meta.get("coordination_branch")`
  (retired D-2 CWD-divergence class). On rollback (`_restore_pre_target_if_at_baseline`), revert
  the coord `done` commit to the captured SHA via `git/ref_advance.py::advance_branch_ref` or a
  coord-worktree `git revert` — **never raw `git update-ref`** (AC-B3), subprocess env via
  `_make_merge_env` (AC-F1).
- **T011 — durable-log resume (FR-007).** Demote `MergeState.completed_wps` to an advisory
  hint; derive resume progress by consuming `read_event_log(EventLogReadContract.coordination_branch_ref(...))`
  + `wp_lane_actor_from_events()` (`coordination/status_service.py`) — do NOT author a new
  reducer, do NOT re-route the `status_transition.py` read contract (Option A makes the existing
  worktree-first dedup correct once coherence is restored).

## Acceptance criteria
- WP02's `tests/regression/test_issue_2711_merge_rollback_resume_coherence.py` flips RED → GREEN.
- **SC-003:** committed==working per-WP after rollback; and `--resume` is **idempotent** — the committed `done` event identity (`event_id`) per WP is byte-stable across resume (NOT a tip-count assertion — WP02 empirically proved count stays 1 because safe-commit replaces the tip; the discriminating contract is `event_id` stability / no churn).
- **NFR-002:** `--resume` run N times → byte-stable coord event log (zero `event_id` churn).
- **Edge:** an already-`done` WP resumes as already-done (not re-emitted, not reverted); a `single_branch`/`lanes` mission (no coord worktree) is a proven no-op.

## Validation
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2711_merge_rollback_resume_coherence.py -n0 -q` (GREEN)
- INV-5 ratchets stay green: `PWHEADLESS=1 uv run pytest tests/merge/test_executor_phase_boundary.py tests/specify_cli/merge/test_1827_baseline_regression.py tests/architectural/test_merge_pipeline_ratchets.py -q`
- `ruff check` + `mypy` clean; extract `_revert_coord_done_commit` helper (CC ≤ 15).

## Ownership
Owns: `merge/executor.py` (add the coord-`done`-revert in `_restore_pre_target_if_at_baseline` + capture the ref SHA before the pre-target emit), `merge/done_bookkeeping.py` (resume reconcile), `merge/state.py`. Consumes read-only: `git/ref_advance.py::advance_branch_ref`, `coordination/status_service.py` (`read_event_log`/`wp_lane_actor_from_events`), `mission_runtime.resolve_placement_only`. **Coordination:** WP03 owns `merge/bookkeeping_projection.py` (the working-byte restore `_restore_final_bookkeeping_snapshots` stays as-is — Option A ADDS a coord-ref revert in `executor.py`, it does not rewrite the byte-restore). If WP04 must touch that file, do it under a WP03 dependency to avoid an ownership clash.

## Notes
Rebase-first (C-003) — this surface was freshly refactored; re-resolve every symbol.

## Activity Log

- 2026-07-18T06:54:34Z – claude – shell_pid=3874028 – Moved to for_review
- 2026-07-18T06:55:34Z – claude – shell_pid=3874028 – reviewer-renata APPROVE: Option A correct (coord-worktree revert, ref from resolve_placement_only, AC-B3/F1 safe); durable-log resume via coordination_branch_ref; ratchets 18 green; scope-clean.
