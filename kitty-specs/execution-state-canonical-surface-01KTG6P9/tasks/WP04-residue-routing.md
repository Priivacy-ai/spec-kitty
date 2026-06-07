---
work_package_id: WP04
title: Residue routing — runtime_bridge + workflow + mode branch
dependencies:
- WP01
- WP03
requirement_refs:
- FR-007
- FR-008
- FR-012
- C-001
- C-002
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 3 - Strangle
assignee: ''
agent: ''
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: 'src/runtime/next/runtime_bridge.py'
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/runtime/next/runtime_bridge.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/mission_runtime/resolution.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Residue routing (runtime_bridge + workflow + mode branch)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Route the residue surfaces through the canonical façade and **delete** what they duplicated. No surface keeps a private path-builder "just in case". Behavior-preserving; ratchet is the envelope.

## Objectives & Success Criteria

Route the primary residue surfaces through `mission_runtime.resolve_action_context` and make the gate observe the **mode-correct** target branch.

- FR-007/008/012. C-001/C-002. SC-002 (ratchet incl. direct-to-target).

## Context & Constraints

- Plan IC-04. Contract: [contracts/mission_runtime_api.md](../contracts/mission_runtime_api.md).
- `runtime/next/runtime_bridge.py` is the residue hotspot **and** the #1663 field-drop site (WP11 follows).
- Operator ruling: planning→coord branch; direct-to-target→declared target, no worktree; never mainline unauthorized (C-001).
- **Ownership note (`scope: codebase-wide`)**: this WP legitimately co-edits `mission_runtime/resolution.py` with WP03 and `runtime_bridge.py` with WP11. Per the `tasks-finalize` doctrine, dependency/linearization does not bypass the ownership overlap check — only `codebase-wide` does. As the broadly-overlapping cross-cutting residue-routing WP, it carries the exemption; WP03/WP11 stay narrow. Still linearize (WP04 after WP03; WP11 after WP04) so the shared files are edited sequentially in one lane.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T015 – Route runtime_bridge query-mode
- **Steps**: Replace the slug-derived `feature_dir`/workspace/branch construction in `runtime_bridge.py` query-mode with a `resolve_action_context(...)` call; consume the returned context object.
- **Files**: `src/runtime/next/runtime_bridge.py`.

### Subtask T016 – Route workflow.py fix-mode
- **Steps**: Replace the independently-resolved `repo_root`/`target_branch` in `cli/commands/agent/workflow.py` fix-mode with the canonical context.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py`.

### Subtask T017 – Mode-correct target branch + mainline guard
- **Steps**: Ensure `resolve_action_context` returns the mode-correct `target_branch` (coordination/direct-to-target/worktree); refuse to resolve mainline as a write target without explicit operator authorization.
- **Files**: `src/mission_runtime/resolution.py`, callers.

### Subtask T018 – Keep the ratchet green
- **Steps**: Run WP01 ratchet across all three modes.

## Test Strategy

- `pytest tests/architectural/test_execution_context_parity.py -q` green incl. direct-to-target; add focused unit tests for the mainline-refusal guard.

## Risks & Mitigations

- Large blast radius; mode-branch logic must honor C-001. Coordinate the runtime_bridge edits with WP11 (same file).

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm both surfaces now go through the single resolver, no duplicated path-builder remains in them, and the mainline guard is enforced. Reject any residual independent derivation.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
