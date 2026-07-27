---
work_package_id: WP02
title: 'Red-first repro: rollback/resume incoherence + duplicate done (#2711)'
dependencies: []
requirement_refs:
- FR-002
tracker_refs:
- '2711'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-squash-provenance-and-rollback-coherence-01KXRRB7
base_commit: a4e481b5761e573077cf7c53390ef1bbc41e896e
created_at: '2026-07-17T21:39:54.030521+00:00'
subtasks:
- T003
- T004
phase: Phase 1 - Red-first (#2711 chain)
assignee: ''
agent: "claude"
shell_pid: '3388769'
shell_pid_created_at: '1784324383.02'
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/regression/
create_intent:
- tests/regression/test_issue_2711_merge_rollback_resume_coherence.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/regression/test_issue_2711_merge_rollback_resume_coherence.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Red-first repro: rollback/resume incoherence + duplicate done (#2711)

## Objective
Author a committed **failing, non-vacuous** reproduction that witnesses #2711: on a
target-advance failure after `approved → done` events are committed to the coord branch,
rollback reverts only working bytes (committed `done` opposed to reverted `approved`), and
`spec-kitty merge --resume` re-emits a **duplicate** `done`. RED on the mission base.

## Red-first ATDD (test-only)
- File: `tests/regression/test_issue_2711_merge_rollback_resume_coherence.py`, `pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]`.
- Entry point: real `_run_lane_based_merge`; failure injection: `patch("specify_cli.lanes.merge.integrate_mission_into_target", side_effect=RuntimeError(...))` — the **canonical source-module target** (NOT `specify_cli.merge.executor.*`, a lazy local import that never fires).
- Harness: **fixture fusion** — combine the coord-branch/meta-on-coord shape of `test_merge_coord_topology_1772.py` with worktree materialization from `tests/merge/test_merge_target_resolution.py` (`CoordinationWorkspace.worktree_path` + `git worktree add`). Reconcile the two (the target-resolution fixture deletes coord `meta.json`; keep it here).
- Seed WP frontmatter `review_status: approved` + non-empty `reviewed_by` so the real `approved → done` transition fires. Extend `_real_merge_external_mocks` to leave `_record_merged_wps_done_for_merge`/reconcile REAL (`real_baseline_recording`-style seam).

## Acceptance criteria (FR-002, SC-001/003, US1-S2/S3, US3)
1. **Non-vacuous preconditions (assert BEFORE the act):** `is_under_worktrees_segment(...)` /
   `done_marked_before_target` is True, AND the committed coord branch shows a `done` event
   per WP — so the coherence check cannot pass via "no `done` was ever committed".
2. **Coherence assertion:** reduce the committed coord ref via
   `read_event_log(EventLogReadContract.coordination_branch_ref(...))` + `wp_lane_actor_from_events()`
   and compare to the working reduction — **split-brain (RED) today** (committed `done` vs working `approved`).
3. **Duplicate assertion:** after `--resume`, exactly one `done` event per WP on the committed
   coord ref (read via the same contract) — **RED today** (duplicate `done`).
4. Contract-routed reads only — do NOT hard-code `git show <branch>:kitty-specs/.../status.events.jsonl`.
5. **RED-for-the-right-reason (SC-001):** the first FAILING assertion must be the coherence/duplicate
   contract, not a precondition/setup/fixture failure.

## Validation
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2711_merge_rollback_resume_coherence.py -n0 -q` → FAIL on the coherence/duplicate assertion.

## Ownership
Owns ONLY `tests/regression/test_issue_2711_merge_rollback_resume_coherence.py`. Import the
1772 + `test_merge_target_resolution.py` harness helpers **read-only**; put the fusion helpers
(coord-worktree materialization, real-done mock, `approved` seeding) **inside this test module**
— do NOT edit the shared harness files in place (WP01 also uses 1772; in-place edits collide).
Do not touch production `src/`.

## Notes
Rebase-first (C-003). The canonical committed-ref reduce authority already exists
(`coordination/status_service.py`) — consume it; do NOT author a `reduce_lane_by_wp`.

## Activity Log

- 2026-07-18T05:49:12Z – claude – shell_pid=3388769 – Moved to for_review
- 2026-07-18T05:57:14Z – claude – shell_pid=3388769 – reviewer-renata APPROVE: non-vacuity triple-guarded; binding contract = resume idempotency/event_id byte-stability (not vacuous count); contract-routed reads; scope-clean.
