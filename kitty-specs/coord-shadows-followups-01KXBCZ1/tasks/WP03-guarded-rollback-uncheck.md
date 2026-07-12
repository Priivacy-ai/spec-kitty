---
work_package_id: WP03
title: Guarded rollback-uncheck
dependencies: []
requirement_refs:
- FR-007
- C-001
- C-004
tracker_refs: []
planning_base_branch: rework/coord-shadows-followups
merge_target_branch: rework/coord-shadows-followups
branch_strategy: Planning artifacts for this mission were generated on rework/coord-shadows-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/coord-shadows-followups unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 3 - Rollback robustness
assignee: ''
agent: "claude"
shell_pid: "698445"
history:
- at: '2026-07-12T15:14:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_move_task_rollback_uncheck_robust.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_move_task_rollback_uncheck_robust.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Guarded rollback-uncheck

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role: implementer) before parsing the rest of this prompt.

## Objectives & Success Criteria

Closes **#2576**. Harden `_mt_uncheck_rollback_subtasks` so a WP rolled back to `planned` reliably loses its `- [x]` rows even when the out-of-lock write errors — so #2513 cannot silently re-manifest. Do NOT fold under the status lock.

Done when:
- The uncheck read/write routes through `write_text_within_directory` (house guard).
- A write failure is **surfaced** (recorded on `_MoveTaskState` / reflected in the `move-task` result + error log), never silently leaving `- [x]` rows on a `planned` WP.
- The surfacing does NOT abort `_mt_release_review_lock`; out-of-lock ordering preserved.
- `ruff` + `mypy` clean.

## Context & Constraints

- **C-001**: `_mt_reset_for_planned_rollback` (`tasks_move_task.py:1522-1541`) documents that the uncheck runs OUT-OF-LOCK by design (it does its own commit; must not hold the status lock). Do NOT widen `feature_status_lock`.
- **D2 ordering:** in `_mt_execute` (`:1576-1596`), the lock closes after `_mt_persist_wp_file`; then `_mt_reset_for_planned_rollback` (`:1595`) runs, then `_mt_release_review_lock` (`:1596`). A bare uncaught `raise` in the uncheck would skip the lock release — so surface via state/result, not an early raise.
- **C-004**: keep `owned_files` at the `_mt_uncheck_rollback_subtasks` seam ONLY. Do NOT touch `_mt_run_pre_review_gate` (#2573 shares this module — fork-PR merge-collision risk).
- `write_text_within_directory` is already imported/used in this module (e.g. `:1465`) — consistent house pattern.

## Subtasks

- [ ] T019 [P] Failure-mode test (`tests/specify_cli/cli/commands/agent/test_move_task_rollback_uncheck_robust.py`): simulate a write failure in the uncheck → assert rows NOT silently left checked on `planned` + the result reflects incomplete rollback.
- [ ] T020 Route the uncheck read/write through `write_text_within_directory`.
- [ ] T021 Surfaced-not-swallowed failure mode (record on `_MoveTaskState`/result + error log) without aborting `_mt_release_review_lock`.
- [ ] T022 [P] Test: out-of-lock ordering preserved; review-lock release still fires on failure.
- [ ] T023 Confirm owned_files scope (C-004); `ruff` + `mypy` clean.

## Campsite & Coverage Notes (post-tasks squad — fold into the listed subtasks)

- **Effect-free-except watch (T021):** the existing `except Exception: # pragma: no cover - defensive` at `tasks_move_task.py:1513` swallows COMMIT failures (a warning). The NEW read/write-failure handler must be **SEPARATE** from it and must **record on `_MoveTaskState`/result** — do NOT copy the swallow pattern, or Sonar flags an effect-free handler AND #2513 silently re-manifests. Keep the two handlers from tangling.
- `write_text_within_directory` is already imported in this module (`~L91`) and used at `1316/1380/1386/1465` — routing the uncheck write onto it (T020) is the house pattern, not a new import.
- Complexity: `_mt_uncheck_rollback_subtasks` +2/3 → ~7, under 15.

## Definition of Done

All 5 subtasks checked; `pytest tests/specify_cli/cli/commands/agent/ -q -k rollback` green; the write-failure handler records on state (does NOT swallow, and is separate from the commit `except`); `_mt_run_pre_review_gate` untouched; `ruff` + `mypy` clean.

## Dependencies

None.

## Activity Log

- 2026-07-12T15:29:12Z – claude – shell_pid=698445 – Assigned agent via action command
- 2026-07-12T15:40:51Z – claude – shell_pid=698445 – Ready for review: rollback-uncheck guarded write + surfaced failure mode; 182 passed, ruff/mypy clean
- 2026-07-12T15:54:40Z – user – shell_pid=698445 – APPROVED by reviewer-renata (opus): 7/7 checks pass
