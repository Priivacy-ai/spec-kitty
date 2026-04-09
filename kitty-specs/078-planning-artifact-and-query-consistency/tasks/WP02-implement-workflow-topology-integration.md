---
work_package_id: WP02
title: Implement, Workflow, and Topology Integration
dependencies:
- WP01
requirement_refs:
- C-001
- C-002
- C-005
- FR-006
- FR-008
- FR-010
- FR-019
- NFR-001
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "opencode:gpt-5.4:orchestrator:orchestrator"
history:
- timestamp: '2026-04-08T15:01:02Z'
  event: created
  actor: opencode
authoritative_surface: src/specify_cli/cli/commands/implement.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/core/execution_context.py
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/next/prompt_builder.py
- tests/agent/test_implement_command.py
- tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py
- tests/specify_cli/core/test_worktree_topology.py
tags: []
---

# WP02: Implement, Workflow, and Topology Integration

## Objective

Make every execution-facing caller consume the canonical workspace resolver so planning-artifact WPs can start, render prompts, and appear in topology output without any lane-membership hard failure.

## Success Criterion

After WP01 lands, a planning-artifact WP can be:

- started through `spec-kitty agent action implement <wp-id>` without a lane error
- surfaced in workflow prompts with repository-root workspace guidance
- included in mixed-mission topology output without forcing the workflow layer to silently drop topology information

## Context

This WP is where the new resolver becomes real behavior instead of an internal helper.

Current failure modes:

- `src/specify_cli/cli/commands/implement.py` still treats `lane_for_wp()` as the universal admission check.
- `src/specify_cli/lanes/implement_support.py` is lane-only.
- `src/specify_cli/core/execution_context.py` and `src/specify_cli/next/prompt_builder.py` assume branch and lane metadata are always present.
- `src/specify_cli/core/worktree_topology.py` raises when a planning-artifact WP is absent from `lanes.json`.
- `src/specify_cli/cli/commands/agent/workflow.py` currently swallows topology failures, so one bad planning-artifact WP can make mixed-mission topology disappear.

WP01 should already have introduced nullable branch/lane fields in `ResolvedWorkspace`. Use that contract here instead of reinventing new branches.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty implement WP02`
- Execution worktree allocation: this WP is `code_change`; `/spec-kitty.implement` will allocate or reuse the finalized lane workspace for it from `lanes.json`
- Dependency note: do not start until WP01 is complete because this WP assumes the canonical resolver exists

## Scope

Allowed files are limited to the frontmatter `owned_files` list.

Primary execution surfaces:

- `src/specify_cli/cli/commands/implement.py`
- `src/specify_cli/lanes/implement_support.py`
- `src/specify_cli/cli/commands/agent/workflow.py`
- `src/specify_cli/core/worktree_topology.py`

Supporting consumers:

- `src/specify_cli/core/execution_context.py`
- `src/specify_cli/next/prompt_builder.py`

Test surfaces:

- `tests/agent/test_implement_command.py`
- `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py`
- `tests/specify_cli/core/test_worktree_topology.py`

## Implementation Guidance

### Subtask T006: Replace lane-only validation in `implement.py`

**Purpose**: Stop rejecting planning-artifact WPs before the canonical resolver has a chance to classify them.

**Files**:

- `src/specify_cli/cli/commands/implement.py`

**Steps**:

1. Remove the assumption that every implementable WP must resolve to a lane before workspace resolution runs.
2. Use the canonical resolver from WP01 to determine the execution mode and workspace contract.
3. Keep lane validation for `code_change` WPs where it is still required.
4. Make sure planning-artifact WPs reach the implementation flow instead of failing during the validate step.

**Validation**:

- [ ] `code_change` implement behavior is unchanged
- [ ] planning-artifact WPs no longer fail early on `lane_for_wp() is None`

### Subtask T007: Update `implement_support.py` for repo-root planning execution

**Purpose**: Branch between lane worktree creation and repository-root planning execution without creating fake context files.

**Files**:

- `src/specify_cli/lanes/implement_support.py`

**Steps**:

1. Keep the existing lane-worktree path for `code_change` WPs.
2. Add the planning-artifact branch that reuses repository root and does not create a lane workspace context file.
3. Ensure the returned result is still rich enough for `implement.py` to print clear next-step information.
4. Do not synthesize lane ids or branch names for planning-artifact work.

**Validation**:

- [ ] `code_change` WPs still create or reuse a lane worktree
- [ ] planning-artifact WPs return repository root cleanly
- [ ] planning-artifact execution does not create lane-only workspace context artifacts

### Subtask T008: Update action context and prompt builder for nullable lane/branch data

**Purpose**: Make non-top-level callers consume the richer resolver contract without crashing on null branch/lane fields.

**Files**:

- `src/specify_cli/core/execution_context.py`
- `src/specify_cli/next/prompt_builder.py`

**Steps**:

1. Update any caller assumptions that `branch_name`, `lane_id`, or similar fields are always strings.
2. Keep repository-root workspace paths printable and explicit for planning-artifact WPs.
3. Avoid sprinkling execution-mode branches everywhere; normalize once, then branch only where the output needs a different label.

**Validation**:

- [ ] action-context resolution works for both execution modes
- [ ] prompt builder does not crash on nullable branch/lane values

### Subtask T009: Update workflow prompt generation for repo-root planning work

**Purpose**: Make workflow prompts teach the correct working directory and execution surface for planning-artifact WPs.

**Files**:

- `src/specify_cli/cli/commands/agent/workflow.py`

**Steps**:

1. Ensure workflow prompts show repository root as the working directory for planning-artifact WPs.
2. Keep code-change prompt behavior unchanged.
3. Preserve the existing informational topology injection, but make it resilient to mixed-mission topology entries.
4. Avoid silent loss of planning-artifact context in the prompt output.

**Validation**:

- [ ] planning-artifact workflow prompts instruct agents to work in repository root
- [ ] code-change workflow prompts still point at the lane workspace

### Subtask T010: Update `worktree_topology.py` for mixed missions

**Purpose**: Mixed missions must still render topology instead of failing because one planning-artifact WP is intentionally outside the lane graph.

**Files**:

- `src/specify_cli/core/worktree_topology.py`

**Steps**:

1. Extend the topology entry model so repo-root planning entries can exist with nullable lane and branch fields.
2. Stop raising on planning-artifact WPs that are absent from `lanes.json`.
3. Keep lane-backed topology unchanged for `code_change` WPs.
4. Ensure rendered JSON/text communicates that the planning-artifact entry is repository-root work, not a missing assignment bug.

**Validation**:

- [ ] mixed-mission topology includes repo-root planning entries explicitly
- [ ] workflow no longer loses all topology output because one planning-artifact WP lacks lane membership

### Subtask T011: Add mixed-mission caller tests

**Purpose**: Lock in the integration behavior across implement, workflow, and topology.

**Files**:

- `tests/agent/test_implement_command.py`
- `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py`
- `tests/specify_cli/core/test_worktree_topology.py`

**Steps**:

1. Add an implement test for a planning-artifact WP that resolves to repository root.
2. Add a workflow prompt test for repo-root planning guidance.
3. Add topology tests proving a mixed mission renders planning-artifact entries instead of raising.
4. Keep tests focused on the canonical resolver contract, not incidental text formatting.

**Validation**:

- [ ] tests cover implement, workflow, and topology
- [ ] topology tests cover the prior failure mode explicitly

## Definition of Done

- Implement, workflow, action-context, prompt-builder, and topology consumers all use the canonical resolver
- Planning-artifact WPs can start without lane-membership failures
- Mixed-mission topology renders repo-root planning entries explicitly
- No fake lane ids or fake branch names are introduced for planning-artifact work
- Mixed-mission caller tests pass

## Risks and Guardrails

- Keep repository-root planning behavior explicit; do not let null branch/lane fields leak into string formatting accidentally.
- Topology is informational, but this WP must still fix the specific silent-drop behavior triggered by planning-artifact WPs.
- Do not create workspace context files for planning-artifact WPs just to satisfy existing assumptions.

## Reviewer Guidance

Verify the following during review:

1. `implement.py` no longer hard-fails solely because a planning-artifact WP lacks lane membership.
2. `implement_support.py` still preserves the old lane-worktree path for `code_change` WPs.
3. `worktree_topology.py` can represent repo-root planning entries without raising.
4. Workflow prompts show a correct repository-root working directory for planning-artifact WPs.

## Activity Log

- 2026-04-08T15:58:07Z – opencode:gpt-5.4:python-implementer:implementer – Moved to in_progress
- 2026-04-08T17:47:39Z – opencode:gpt-5.4:python-implementer:implementer – Ready for review
- 2026-04-08T18:25:37Z – opencode:gpt-5.4:python-reviewer:reviewer – Arbiter decision: review concerns resolved or not reproducible against the canonical event-log model; WP02 meets acceptance criteria
- 2026-04-08T19:14:25Z – opencode:gpt-5.4:orchestrator:orchestrator – Done override: Changes already landed directly on main during orchestrated bootstrap implementation
