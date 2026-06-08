---
work_package_id: WP05
title: Collapse duplicate feature-dir resolvers
dependencies:
- WP04
requirement_refs:
- FR-010
- NFR-002
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T019
- T020
- T021
phase: Phase 3 - Strangle
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "2755078"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/specify_cli/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Collapse duplicate feature-dir resolvers

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

The canonical example of semantic compression: 8 implementations of the same behavior → 1. Map the behavioral envelope of each copy first; only delete a copy once its callers use the canonical resolver and the ratchet proves equivalence.

## Objectives & Success Criteria

Collapse the 8 duplicate `_resolve_feature_dir`/feature-dir resolver implementations to a single canonical resolver and delete the rest.

- FR-010. NFR-002. SC-004 (partial), SC-007.

## Context & Constraints

- Known copies (verify current state): `workspace/context.py`, `task_utils/support.py`, `cli/commands/verify.py`, `cli/commands/agent/status.py` (×2), `dashboard/scanner.py`, `missions/feature_dir_resolver.py` (canonical candidate).
- Prefer routing through `mission_runtime.resolve_action_context` where callers actually need full context; use `missions/feature_dir_resolver.resolve_feature_dir_for_mission` where only the dir is needed.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T019 – Inventory + select canonical
- **Steps**: List all current feature-dir resolver implementations; diff their behavior; pick the canonical one.
- **Files**: the 8 sites above.

### Subtask T020 – Repoint call sites [P]
- **Steps**: Replace each redundant call with the canonical resolver.

### Subtask T021 – Delete redundant implementations
- **Steps**: Remove the now-unused copies; no dead code.

## Test Strategy

- Existing unit/integration tests for the affected commands green; WP01 ratchet green.

## Risks & Mitigations

- Subtle behavioral differences between copies → diff each against the canonical before deleting; add a unit test where behavior was ambiguous.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm exactly one resolver remains and no caller kept a local copy. Reject partial collapses.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T08:16:41Z – claude:opus:randy-reducer:implementer – shell_pid=2755078 – Started implementation via action command
