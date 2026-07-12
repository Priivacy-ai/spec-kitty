---
work_package_id: WP06
title: Tasks-family heavy-seam behavioral triage + wave1 reconcile
dependencies:
- WP05
requirement_refs:
- FR-005
- FR-006
- NFR-002
- C-002
- C-003
tracker_refs:
- '2565'
planning_base_branch: feat/dev-assist-retire-path-hardening
merge_target_branch: feat/dev-assist-retire-path-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/dev-assist-retire-path-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dev-assist-retire-path-hardening unless the human explicitly redirects the landing branch.
created_at: '2026-07-12T10:40:00Z'
subtasks:
- T001
- T002
- T003
phase: Compat-surface consolidation
shell_pid: "405312"
agent: "claude"
history:
- at: '2026-07-12T10:40:00Z'
  actor: claude
  action: Split from WP05 per post-tasks squad (Lens B). Heavy seams (status_cmd/move_task/mark_status) + wave1 orchestration reconcile; depends on WP05's consolidated guard.
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_status_cmd_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py
role: implementer
tags: []
task_type: implement
---

# WP06 — Tasks-family heavy-seam behavioral triage + wave1 reconcile

## Context

Depends on **WP05**, which authors `test_tasks_compat_surface.py` — the standing consolidated guard whose symbol coverage satisfies coverage-before-deletion (C-002) for THIS WP's retirements. This WP handles the three heaviest tasks seams (`status_cmd` 18, `move_task` 22, `mark_status` 27 `assert_called`) and reconciles the wave1 orchestration files. `move_task` alone carries a 51-symbol `_MOVE_SET` (456 LOC).

## Approach

1. **T001 — retire the heavy seams' scaffolding** (`status_cmd`, `move_task`, `mark_status`): remove each `test_tasks_binding_is_*` identity battery (now covered by WP05's consolidated guard — cite it), the `test_move_set_matches_*_defs` exact-set pins, and the `assert_called` internal-call-graph interception proofs (18+22+27 = 67 assertions). Each interception-proof removal is a per-scenario C-002 judgment, NOT a mechanical delete — for each, confirm the scenario's observable behavior is preserved by a behavioural test before deleting.
2. **T002 — reconcile wave1 ↔ wave2** (read-only analysis of the NOT-owned behavioural files `test_tasks_coreless_orchestration.py`, `test_tasks_core_backed_orchestration.py`, `test_tasks_ports.py`): confirm no observable-contract assertion for these seams is dropped — i.e. every scenario an interception proof covered is either (a) a re-export identity now in WP05's guard, or (b) an observable side-effect/return already asserted by a wave1 orchestration test. Record any genuine gap (a scenario covered ONLY by an interception proof) and KEEP a narrow observable-contract test for it rather than dropping coverage. These files should need no edits; a genuinely-required edit is recorded with a one-line out-of-map rationale.
3. **T003 — verify + anti-vacuity**: prove WP05's consolidated guard covers all symbols these seams' batteries did (no dropped private symbol); plant a broken re-export for a `move_task`/`mark_status`/`status_cmd` symbol → the consolidated guard fails → revert; `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/ -q` green.

## Acceptance

- The 3 heavy seams' identity batteries + exact-set pins + 67 interception proofs retired, each citing its coverage source (WP05 guard or a preserved behavioural test).
- Wave1↔wave2 reconcile complete; no observable-contract coverage dropped.
- Planted regression caught; agent tasks suite green; `ruff` clean.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main`). Worktree per computed lane from `lanes.json`. Executes after WP05 (dependency).

## Activity Log

- 2026-07-12T12:28:36Z – claude – shell_pid=405312 – Moved to for_review
- 2026-07-12T12:36:38Z – claude – shell_pid=405312 – LAND review afe81ef8 (interception proofs correctly kept)
