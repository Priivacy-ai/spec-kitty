---
work_package_id: WP06
title: Eliminate remaining path-builders
dependencies:
- WP05
requirement_refs:
- FR-009
- FR-011
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
- T022
- T023
- T024
- T025
phase: Phase 3 - Strangle
assignee: ''
agent: ''
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
- src/runtime/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Eliminate remaining path-builders

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive the residue to zero. Each raw `kitty-specs / mission_slug` construction is a parallel path to the canonical resolver — route it or delete it. Work in reviewable batches; the SC-004 grep is the burn-down meter.

## Objectives & Success Criteria

Route or delete the remaining ~125 raw `main_repo_root / "kitty-specs" / mission_slug`-class constructions across ~160 files.

- FR-009/011. NFR-002. SC-004 (zero outside the canonical module and `status/`).

## Context & Constraints

- Plan IC-04. Investigation grep (re-verify count at start):
  `grep -rn 'kitty-specs.*mission_slug\|main_repo_root.*kitty\|feature_dir.*slug' src/specify_cli --include='*.py' | grep -v 'status/' | grep -v 'mission_runtime/'`

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T022 – Enumerate
- **Steps**: Produce the current list of raw path-builder occurrences (the count will be lower than ~125 after WP04/WP05).

### Subtask T023 – Route through the canonical surface [P]
- **Steps**: Replace each with `resolve_action_context(...)`/the canonical feature-dir resolver. Batch by package for reviewability.

### Subtask T024 – Delete dead builders
- **Steps**: Remove path-builder helper functions made unreachable.

### Subtask T025 – Confirm zero
- **Steps**: Re-run the SC-004 grep; expect zero outside `mission_runtime/` and `status/`.

## Test Strategy

- WP01 ratchet green after each batch; `ruff`/`mypy` clean on touched modules.

## Risks & Mitigations

- Volume → reviewable batches; never let the ratchet go red between batches.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Spot-check that routed sites use the canonical context and no new boundary leak was introduced. Confirm the SC-004 grep is zero.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
