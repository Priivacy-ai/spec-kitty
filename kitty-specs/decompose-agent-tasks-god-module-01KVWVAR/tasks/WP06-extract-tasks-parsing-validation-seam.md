---
work_package_id: WP06
title: Extract tasks_parsing_validation seam
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
merge_target_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-decompose-agent-tasks-god-module-01KVWVAR. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-decompose-agent-tasks-god-module-01KVWVAR unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - Seam extraction
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2503927"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Extract `tasks_parsing_validation` seam (+ sub-split the 348-LOC validator)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_parsing_validation.py`.

---

## Objective

Extract the **readiness / verdict / issue-matrix validation** helpers into
`tasks_parsing_validation.py`, and **sub-split the 348-LOC `_validate_ready_for_review` god-function**
into ≤15-CC helpers (FR-003, FR-004, NFR-001). Largest seam. Behavior-preserving. Depends on WP03
(uses outline+materialization).

## Context

- `research.md §1,§2`: `_validate_ready_for_review` (lines ~1377–1724) is itself a god-function with
  four orthogonal concerns. Existing coverage of parsing-validation is STRONG — lean on it.
- **Ownership**: own the new files; minimal out-of-map edit to `tasks.py` (move helpers + wire import).
  `tasks.py` owned by WP07.

## Helpers to move + the sub-split

Move: `_issue_matrix_evaluation`, `_issue_matrix_row_issues`, `_issue_matrix_in_mission_rows`,
`_issue_matrix_diagnostic_lines`, `_issue_matrix_approval_blocker`, `_primary_issue_matrix_satisfies`,
`_self_review_fallback_option_error`, `_get_latest_review_cycle_verdict`, `_apply_review_status_flags`,
and `_validate_ready_for_review`.

**Sub-split `_validate_ready_for_review`** into named helpers, each maxCC ≤15:
`_validate_research_artifacts(...)`, `_validate_worktree_state(...)`, `_check_merge_ancestry(...)`,
`_check_kitty_specs_contamination(...)`, with a thin orchestrator that composes them. Preserve the
exact validation order and messages.

## Subtasks

### T022 — Create `tasks_parsing_validation.py`; move the issue-matrix/verdict helpers
Move the listed helpers verbatim. Bring needed imports. One-way imports; may import outline/materialization.

### T023 — Sub-split `_validate_ready_for_review` into ≤15-CC helpers
Decompose into the four concern-helpers + orchestrator. Behavior-preserving — same gates, same order,
same messages, same return shape. Verify each helper's complexity with `ruff check` (C901).

### T024 — Wire `tasks.py` (out-of-map)
Delete moved defs; import from the seam; re-export any path-imported names (grep first). Record rationale.

### T025 — Add unit tests
Create `test_tasks_parsing_validation.py`. Test the issue-matrix approval-blocker logic, verdict
extraction, and each of the four sub-split validators directly (research-artifact / worktree-state /
merge-ancestry / contamination). ≥90% on the new module.

### T026 — Prove suites green
`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider`; golden green.

## Branch Strategy

- Lanes merge into the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (PRs to `main` at mission end; `main` is protected). Depends on **WP03**. Worktree per lane.

## Definition of Done

- [ ] `tasks_parsing_validation.py` created; listed helpers moved verbatim.
- [ ] `_validate_ready_for_review` sub-split into ≤15-CC helpers + orchestrator; order/messages preserved.
- [ ] `test_tasks_parsing_validation.py` covers issue-matrix, verdicts, and all four sub-validators; ≥90%.
- [ ] Every function in the new module maxCC ≤15 (`ruff check` clean — C901).
- [ ] Golden contract test green; full `agent/` suite green; mypy --strict clean; no new suppressions.

## Risks

- **The 348-LOC sub-split is the subtle part** — easy to drift validation order or messages. The golden
  test + existing strong coverage are your guards; add direct tests per sub-validator.
- **Git subprocess + spec.md parsing coupling** — pass inputs explicitly; keep fallbacks.

## Reviewer guidance

Verify the sub-split is behavior-preserving (same gates/order/messages), every new function is ≤15 CC,
direct tests exist per sub-validator, and the golden contract test is green. This is the highest-risk
seam — review the validator diff carefully.

## Activity Log

- 2026-06-24T15:39:55Z – user – shell_pid=2448463 – Moved to planned
- 2026-06-24T15:39:58Z – claude:opus:randy-reducer:implementer – shell_pid=2453114 – Started implementation via action command
- 2026-06-24T15:41:44Z – user – shell_pid=2453114 – Moved to planned
- 2026-06-24T15:41:48Z – claude:opus:randy-reducer:implementer – shell_pid=2456855 – Assigned agent via action command
- 2026-06-24T16:04:36Z – claude:opus:randy-reducer:implementer – shell_pid=2456855 – tasks_parsing_validation seam + 348-LOC validator sub-split into 9 helpers all <=15 CC, behavior byte-identical, 467 tests green, 93% coverage, tasks.py 4220->3587
- 2026-06-24T16:04:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=2503927 – Started review via action command
- 2026-06-24T16:14:07Z – user – shell_pid=2503927 – Review passed (cycle 3): validator sub-split byte-identical (80 guidance messages + return shape + gate order verified vs original 348-LOC; KITTY_SPECS_DIR==kitty-specs). 9 helpers C901-clean at maxCC=15; mypy --strict clean; one-way imports; thin wrapper injects tasks-resident collaborators preserving @patch contracts with no duplicated logic. 467 agent tests pass incl golden contract (27); 90% seam coverage; per-sub-validator tests drive real gate logic. Scope: 3 files, no dep/lock change, no new suppressions. Override of review-cycle-2 stale rejection: that was an orchestration dependency-base reset ('code unchanged'), not a code-quality reject; see review-cycle-3.md.
- 2026-06-24T17:14:37Z – user – shell_pid=2503927 – Moved to done
