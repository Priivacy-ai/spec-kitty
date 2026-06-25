---
work_package_id: WP06
title: Lifecycle families II — setup_plan + accept/merge
dependencies:
- WP05
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 3 - Command seams
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "3367138"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_setup_plan.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/mission_accept_merge.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
- tests/specify_cli/cli/commands/agent/test_mission_accept_merge.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/mission_accept_merge.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
- tests/specify_cli/cli/commands/agent/test_mission_accept_merge.py
tags: []
---

# Work Package Prompt: WP06 – Lifecycle families II (setup_plan + accept/merge)

## Do This First

1. Confirm WP05 merged; golden test green.
2. Read research.md §2 (`setup_plan` mega-function, 507 LOC; phases enumerated) and §3 Seam B, O-3.
3. `setup_plan` is imported by `lifecycle.py` — stays re-exportable at `mission.<name>` (WP09).
   `accept`/`merge` are thin delegators — keep their `top_level_accept`/`top_level_merge` imports
   function-local so the seam does not pull the full accept/merge graph at module top level (A-3).

## Objective

Move `setup_plan` (decomposed to ≤15-CC phase helpers) into `mission_setup_plan.py` with its commit
helpers, and the thin delegators `accept_feature`/`merge_feature` into `mission_accept_merge.py`.

## Implementation

### T022 — setup_plan family (decompose)
Create `mission_setup_plan.py`; move `setup_plan` and decompose its 507 LOC into phase helpers: SaaS/auth
preflight → git preflight → feature-dir resolution → branch-contract injection → plan commit
(`_commit_to_branch`) → coord commits (`commit_for_mission`). Each helper ≤15 CC.

### T023 — Commit helpers
Move into the setup-plan seam: `_commit_to_branch`, `CommitToBranchResult` (exported — imported by tests),
`_kind_for_artifact`, `_artifact_has_no_git_changes`, `_artifact_absent_at_placement`,
`_print_artifact_unchanged`, `_warn_commit_failed`. Keep `commit_for_mission` lazy.

### T024 — accept/merge family
Create `mission_accept_merge.py`; move `accept_feature`, `merge_feature`, `_find_latest_feature_worktree`,
`_find_feature_worktree`. Confirm `top_level_accept`/`top_level_merge` imports stay function-local.

### T025 — Tests + repoint
Author `test_mission_setup_plan_phases.py` (per phase helper) and `test_mission_accept_merge.py`; extend
`test_agent_mission_commit_to_branch.py`, `test_kind_for_artifact.py`, and accept/merge tests. Documented
import edits in `mission.py`.

### T026 — Gates
Golden test green; ruff (C901 ≤15) + mypy --strict clean.

## Acceptance

- Two seam modules + tests; `setup_plan` ≤15 CC with phase-helper tests; `CommitToBranchResult` still
  importable; golden green.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only.

## Activity Log

- 2026-06-24T21:58:33Z – claude:opus:randy-reducer:implementer – shell_pid=3367138 – Assigned agent via action command
- 2026-06-24T22:35:44Z – claude:opus:randy-reducer:implementer – shell_pid=3367138 – Lifecycle families II: setup_plan decomposed into phase helpers + relocated with commit helpers to mission_setup_plan.py; accept/merge delegators to mission_accept_merge.py (merge_feature decomposed to CC<=15); mission.py 2630 to 1742 LOC; golden + full suites green; ruff C901<=15 + mypy --strict clean
- 2026-06-24T22:49:22Z – user – shell_pid=3367138 – Self-review pass: acceptance met (2 seam modules + 25 focused tests; setup_plan decomposed to phase helpers all <=15 CC; CommitToBranchResult/_commit_to_branch/_kind_for_artifact still importable from mission); behavior-preserving (golden + full agent/commit/setup_plan suites green; sole repo-wide failure is pre-existing WP04 record_analysis shim gap, deferred WP09); re-exports + mission.<name> patch seams + lifecycle.py setup_plan resolve; merge_feature CC<=15. ruff + mypy --strict clean.
