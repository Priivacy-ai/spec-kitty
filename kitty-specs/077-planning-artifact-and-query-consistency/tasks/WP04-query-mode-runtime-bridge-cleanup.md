---
work_package_id: WP04
title: Query Mode Runtime Bridge Cleanup
dependencies: []
requirement_refs:
- C-003
- C-004
- C-007
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-019
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
agent: "opencode:gpt-5.4:python-implementer:implementer"
history:
- timestamp: '2026-04-08T15:01:02Z'
  event: created
  actor: opencode
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/decision.py
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/next/test_next_command_integration.py
- tests/next/test_query_mode_unit.py
tags: []
---

# WP04: Query Mode Runtime Bridge Cleanup

## Objective

Turn query mode into an explicit, read-only status surface:

- no `--agent` required when `--result` is omitted
- fresh runs return `mission_state = not_started` plus `preview_step`
- no state advancement in query mode
- actionable validation failure if a mission has no issuable first step

## Success Criterion

The following behaviors all hold at once:

1. `spec-kitty next --mission-run <slug> --json` succeeds without `--agent`
2. a fresh run returns `mission_state = not_started` and a non-null `preview_step`
3. repeated query calls leave the run state unchanged
4. `spec-kitty next --agent <name> --mission-run <slug> --result success` still advances normally

## Context

Current state:

- `src/specify_cli/cli/commands/next_cmd.py` still requires `--agent` even though query mode is read-only
- `src/specify_cli/next/runtime_bridge.py` already has `query_current_state()`, but it reports `unknown` for fresh runs
- `src/specify_cli/next/decision.py` has no `preview_step` field and assumes `agent` is always present

This WP is independent of the resolver work and can run in parallel with WP01.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty implement WP04`
- Execution worktree allocation: this WP is `code_change`; `/spec-kitty.implement` will allocate or reuse the finalized lane workspace for it from `lanes.json`
- Dependency note: none; this is the independent query-contract stream

## Scope

Allowed files are limited to the frontmatter `owned_files` list.

Primary surfaces:

- `src/specify_cli/next/decision.py`
- `src/specify_cli/next/runtime_bridge.py`
- `src/specify_cli/cli/commands/next_cmd.py`

Test surfaces:

- `tests/next/test_next_command_integration.py`
- `tests/next/test_query_mode_unit.py`

## Implementation Guidance

### Subtask T018: Make `--agent` optional only for query mode

**Purpose**: Remove meaningless ceremony from read-only query mode without weakening advancing-mode identity requirements.

**Files**:

- `src/specify_cli/cli/commands/next_cmd.py`

**Steps**:

1. Make `--agent` optional when `--result` is omitted.
2. Keep `--agent` required for advancing and answer flows.
3. Keep compatibility support for callers that still pass `--agent` in query mode.
4. Make the CLI validation branch explicit and easy to test.

**Validation**:

- [ ] query mode succeeds without `--agent`
- [ ] advancing mode still rejects missing `--agent`

### Subtask T019: Extend `Decision` with `preview_step` and nullable `agent`

**Purpose**: Make the query contract explicit in one shared response model.

**Files**:

- `src/specify_cli/next/decision.py`

**Steps**:

1. Add `preview_step` to the decision model and serialization.
2. Allow `agent` to be null for query mode.
3. Keep the rest of the decision payload stable for existing callers.
4. Make the new fields easy to assert on in contract tests.

**Validation**:

- [ ] serialized query decisions can include `agent = null`
- [ ] fresh-run query decisions can include `preview_step`

### Subtask T020: Implement `not_started + preview_step` in `runtime_bridge.py`

**Purpose**: Replace the misleading fresh-run `unknown` state with an honest read-only preview.

**Files**:

- `src/specify_cli/next/runtime_bridge.py`

**Steps**:

1. Keep query mode read-only; do not call the advancing runtime path.
2. Detect the fresh-run case where no step has been issued yet.
3. Compute and return `mission_state = not_started` plus the first issuable step as `preview_step`.
4. Preserve the existing started-run behavior where issued step ids are returned directly.

**Validation**:

- [ ] fresh runs no longer report `unknown`
- [ ] started runs still report the issued step id

### Subtask T021: Fail clearly when there is no issuable first step

**Purpose**: An invalid mission definition should not degrade into an empty or misleading success response.

**Files**:

- `src/specify_cli/next/runtime_bridge.py`
- `src/specify_cli/cli/commands/next_cmd.py`

**Steps**:

1. Detect the no-issuable-first-step condition in the query path.
2. Return or raise an actionable validation error instead of falling back to `unknown`.
3. Keep the error precise: name the mission and the invalid condition.
4. Make the failure shape easy to test in JSON and human output.

**Validation**:

- [ ] invalid mission definitions fail clearly in query mode
- [ ] no fabricated step id is returned

### Subtask T022: Update human-readable query output

**Purpose**: The human-facing output must match the new machine contract and stop teaching `unknown` as valid fresh-run state.

**Files**:

- `src/specify_cli/cli/commands/next_cmd.py`

**Steps**:

1. Keep the query label explicit and read-only.
2. Print `Mission: <type> @ not_started` for fresh runs.
3. Print `Next step: <preview_step>` for fresh runs.
4. Keep progress and run id output intact where available.

**Validation**:

- [ ] fresh-run human output names `not_started`
- [ ] fresh-run human output names the preview step

### Subtask T023: Add query-contract tests

**Purpose**: Lock in the machine contract, human output, and non-mutating behavior.

**Files**:

- `tests/next/test_next_command_integration.py`
- `tests/next/test_query_mode_unit.py`

**Steps**:

1. Add a non-mutating query regression test.
2. Add a fresh-run JSON contract test for `not_started + preview_step`.
3. Add a compatibility test where `--agent` is still supplied in query mode.
4. Add a failure test for a mission with no issuable first step.
5. Add an advancing regression test so `--result success` behavior is preserved.

**Validation**:

- [ ] tests cover JSON and human output expectations
- [ ] tests prove query mode does not advance runtime state
- [ ] tests prove advancing mode still works

## Definition of Done

- Query mode no longer requires `--agent`
- Fresh runs return `not_started + preview_step`
- Invalid first-step definitions fail clearly
- Human-readable output matches the new contract
- Query tests prove non-mutation and advancing regression safety

## Risks and Guardrails

- Keep query and advancing validation paths separate so advancing mode does not become weaker accidentally.
- Do not hide the fresh-run preview inside a compound state string.
- Be explicit about private runtime snapshot dependencies in code comments and tests.

## Reviewer Guidance

Verify the following during review:

1. Query mode succeeds with `spec-kitty next --mission-run <slug>` and no agent.
2. Fresh runs return `not_started` and `preview_step` in JSON.
3. Human-readable output names the next step for fresh runs.
4. Advancing mode still requires `--agent` and `--result`.

## Activity Log

- 2026-04-08T15:42:19Z – opencode:gpt-5.4:python-implementer:implementer – Moved to in_progress
