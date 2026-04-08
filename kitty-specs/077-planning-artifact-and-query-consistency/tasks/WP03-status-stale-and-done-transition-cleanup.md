---
work_package_id: WP03
title: Status, Stale, and Done Transition Cleanup
dependencies:
- WP01
requirement_refs:
- C-003
- C-005
- C-008
- FR-005
- FR-007
- FR-009
- FR-019
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
agent: "opencode:gpt-5.4:python-implementer:implementer"
history:
- timestamp: '2026-04-08T15:01:02Z'
  event: created
  actor: opencode
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/stale_detection.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py
- tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py
- tests/specify_cli/cli/commands/agent/test_tests_stale_check.py
tags: []
---

# WP03: Status, Stale, and Done Transition Cleanup

## Objective

Make status and stale reporting tell the truth for planning-artifact work, while also aligning `move-task --to done` with the new lifecycle contract.

This WP owns two related user-facing promises:

1. planning-artifact work in repository root is not stale or fresh; it is explicitly `not_applicable`
2. planning-artifact WPs can reach `approved` and `done` through artifact acceptance, not branch merge ancestry

## Success Criterion

A planning-artifact WP in progress produces this behavior consistently:

- `spec-kitty agent tasks status --json` includes a nested `stale` object with `status = not_applicable` and `reason = planning_artifact_repo_root_shared_workspace`
- legacy flat fields (`is_stale`, `minutes_since_commit`, `worktree_exists`) remain present and are derived from the nested object during the transition window
- human-readable status output says `stale: n/a (repo-root planning work)`
- `spec-kitty agent tasks move-task <wp-id> --to done` does not require merge ancestry for planning-artifact work, while a code-change WP still does

## Context

Current state:

- `src/specify_cli/core/stale_detection.py` assumes the resolved workspace path is a worktree with commit-heartbeat semantics.
- `src/specify_cli/cli/commands/agent/tasks.py` serializes stale output as flat booleans and minute counts.
- the `done` guard in `tasks.py` still uses branch merge ancestry for every WP, regardless of execution mode.

This WP must fix both the stale semantics and the done-transition semantics together. Otherwise planning-artifact WPs will look valid at startup but still fail or lie at completion time.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty implement WP03`
- Execution worktree allocation: this WP is `code_change`; `/spec-kitty.implement` will allocate or reuse the finalized lane workspace for it from `lanes.json`
- Dependency note: WP01 must land first so stale detection can rely on the canonical resolver

## Scope

Allowed files are limited to the frontmatter `owned_files` list.

Primary surfaces:

- `src/specify_cli/core/stale_detection.py`
- `src/specify_cli/cli/commands/agent/tasks.py`

Test surfaces:

- `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py`
- `tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py`
- `tests/specify_cli/cli/commands/agent/test_tests_stale_check.py`

## Implementation Guidance

### Subtask T012: Refactor stale detection to emit a structured stale payload

**Purpose**: Replace boolean-only stale reporting with a shape that can represent `fresh`, `stale`, or `not_applicable` safely.

**Files**:

- `src/specify_cli/core/stale_detection.py`

**Steps**:

1. Update the stale result model to carry a nested `stale` object plus workspace-kind metadata.
2. Preserve enough information for both machine JSON output and human-readable status rendering.
3. Keep the code-change stale path unchanged in spirit: commit heartbeat still determines `fresh` vs `stale`.

**Validation**:

- [ ] stale detection can express `not_applicable` without overloading `unknown`
- [ ] code-change stale behavior remains intact

### Subtask T013: Mark repo-root planning work as `not_applicable`

**Purpose**: Shared repository-root activity is not a WP-scoped freshness signal.

**Files**:

- `src/specify_cli/core/stale_detection.py`

**Steps**:

1. Detect the repository-root planning case from the canonical resolved workspace.
2. Emit the canonical reason code: `planning_artifact_repo_root_shared_workspace`.
3. Ensure minute and commit timestamp fields are null in this case.
4. Keep the result explicit rather than omitting the field.

**Validation**:

- [ ] planning-artifact repo-root WPs produce `status = not_applicable`
- [ ] shared repo activity is never treated as freshness proof for planning work

### Subtask T014: Preserve deprecated flat stale fields during the transition

**Purpose**: Current machine consumers still read flat stale fields from `spec-kitty agent tasks status --json`.

**Files**:

- `src/specify_cli/cli/commands/agent/tasks.py`

**Steps**:

1. Make the nested `stale` object the source of truth.
2. Derive `is_stale`, `minutes_since_commit`, and `worktree_exists` from the canonical nested object during the transition window.
3. Do not maintain separate stale logic in parallel.
4. Keep the mapping exactly as documented in `data-model.md`.

**Validation**:

- [ ] JSON output contains the nested object
- [ ] deprecated flat fields are still present and consistent with the nested object

### Subtask T015: Update human-readable task status output

**Purpose**: Human output must stop implying that planning-artifact WPs are stale or missing a lane.

**Files**:

- `src/specify_cli/cli/commands/agent/tasks.py`

**Steps**:

1. Show planning-artifact WPs as valid repository-root work in the lifecycle board.
2. Render `stale: n/a (repo-root planning work)` instead of stale warnings for those WPs.
3. Keep stale warnings for code-change WPs only.
4. Avoid introducing lane-membership failure language in status output.

**Validation**:

- [ ] human-readable output distinguishes repository-root planning work from stale code work
- [ ] planning-artifact WPs remain visible in lifecycle status output

### Subtask T016: Bypass merge ancestry for planning-artifact `--to done`

**Purpose**: Planning-artifact completion is artifact acceptance, not branch merge ancestry.

**Files**:

- `src/specify_cli/cli/commands/agent/tasks.py`

**Steps**:

1. Keep the existing ancestry guard for `code_change` WPs.
2. Short-circuit that guard for planning-artifact WPs so `approved -> done` works without a branch merge.
3. Preserve the rest of the lane transition safety checks as appropriate.
4. Keep reviewer evidence and history recording intact.

**Validation**:

- [ ] planning-artifact WPs can move to `done` without `--done-override-reason`
- [ ] code-change WPs still require merge ancestry or an explicit override

### Subtask T017: Add tests for stale compatibility and lifecycle transitions

**Purpose**: Lock in the machine-facing stale compatibility shape and the planning-artifact completion path.

**Files**:

- `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py`
- `tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py`
- `tests/specify_cli/cli/commands/agent/test_tests_stale_check.py`

**Steps**:

1. Add JSON assertions for nested stale plus legacy flat fields.
2. Add lifecycle tests for planning-artifact `approved` and `done` transitions.
3. Add a regression proving code-change `done` still requires merge ancestry.
4. Keep tests targeted at the documented transition behavior, not incidental formatting.

**Validation**:

- [ ] tests cover both machine JSON and human status output behavior
- [ ] tests prove the code-change guardrail still exists

## Definition of Done

- Nested stale status is the canonical machine contract
- Deprecated flat stale fields are still present during the transition window
- Planning-artifact WPs render as repository-root planning work in status output
- Planning-artifact `--to done` bypasses merge ancestry while code-change `--to done` does not
- Status and lifecycle tests cover the new behavior

## Risks and Guardrails

- Do not accidentally make code-change WPs exempt from merge ancestry checks.
- Do not maintain two independent stale truth sources. The nested object must drive the flat fields.
- Keep the reason code stable: `planning_artifact_repo_root_shared_workspace`.

## Reviewer Guidance

Verify the following during review:

1. `stale.status = not_applicable` appears only for repository-root planning work.
2. JSON output still contains the deprecated flat fields during the transition window.
3. Human output shows `n/a` for planning-artifact stale state.
4. `move-task --to done` behavior now branches on execution mode, not on a blanket ancestry rule.

## Activity Log

- 2026-04-08T18:26:04Z – opencode:gpt-5.4:python-implementer:implementer – Moved to in_progress
