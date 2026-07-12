---
work_package_id: WP05
title: Tasks-family consolidated guard + lighter-seam retirement
dependencies: []
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
base_branch: kitty/mission-dev-assist-retire-path-hardening-01KXAVR0
base_commit: 4e129fc35c2c4d8ee3b87208b14e6c2be7c9c237
created_at: '2026-07-12T11:55:09.371955+00:00'
subtasks:
- T001
- T002
- T003
phase: Compat-surface consolidation
shell_pid: "336065"
agent: "claude"
history:
- at: '2026-07-12T10:40:00Z'
  actor: claude
  action: Split from WP05 per post-tasks squad (Lens B — WP05 undersized 2-3x). WP05a = consolidated guard + lighter seams; WP05b = heavy seams + wave1 reconcile.
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
- tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py
role: implementer
tags: []
task_type: implement
---

# WP05a — Tasks-family consolidated guard + lighter-seam retirement

## Context

The `tasks.py` wave-2 decomposition left 6 `test_tasks_*_seam.py` files, each with a private-symbol re-export identity battery (`test_tasks_binding_is_<seam>_object` over a `_MOVE_SET`), an exact-set `test_move_set_matches_<seam>_defs` pin, and `assert_called` internal-call-graph interception proofs. The re-export identity coverage is unique (not in any golden) → preserve by folding into ONE consolidated guard covering **all 6 seams**; the exact-set pins and interception proofs are fragile shape → retire. WP05a authors the guard (the coverage authority WP05b depends on) and retires the three lighter seams (`finalize`, `map_requirements`, `shared`). WP05b retires the three heavy seams (`status_cmd`, `move_task`, `mark_status`). Keep the guard self-contained (no cross-family shared helper — codebase convention).

## Approach

1. **T001 — author `test_tasks_compat_surface.py`**: iterate a `{symbol → residual-module}` map covering ALL 6 seams' relocated `_mt_*`/binding symbols (read all six `_MOVE_SET`s + the production `tasks_*.py` modules to enumerate — reading non-owned files is fine), asserting each resolves on `tasks` as the seam object (identity). Confirm each symbol is a genuine identity re-export (not a native redefine) before adding it to the `is`-assertion set. Assert the guard's key-set is a strict superset of the union of all 6 retired binding batteries so a dropped symbol fails. This guard is the standing authority that satisfies coverage-before-deletion for WP05b.
2. **T002 — retire the lighter seams' scaffolding** (`finalize`, `map_requirements`, `shared`): remove each `test_tasks_binding_is_*` identity battery (folded into T001), the `test_move_set_matches_*_defs`/`_public_defs` exact-set pin, and the `assert_called` seam-bridge interception proofs (15+18+18). KEEP any genuine observable-contract test in these files.
3. **T003 — verify**: prove the consolidated guard covers these 3 seams' symbols; plant a broken re-export for one of their symbols → the consolidated guard fails → revert; `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py -q` green.

## Acceptance

- One consolidated tasks compat guard (symbol→residual map, identity-verified, superset-asserted) covering all 6 seams.
- The 3 lighter seams' identity batteries + exact-set pins retired; **interception proofs KEPT** as unique routing coverage (the identity guard does not subsume "the seam is still patchable" — retirement deferred to WP06's reconcile / sibling mission #2075, per the WP05 review ruling); observable-contract tests preserved.
- Planted regression caught; the touched suites green; `ruff` clean.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main`). Worktree per computed lane from `lanes.json`.

## Activity Log

- 2026-07-12T12:08:44Z – claude – shell_pid=336065 – Moved to for_review
- 2026-07-12T12:16:25Z – claude – shell_pid=336065 – LAND review a062de8d (interception proofs accept-as-narrowed → WP06)
