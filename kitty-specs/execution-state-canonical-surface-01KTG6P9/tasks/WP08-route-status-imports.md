---
work_package_id: WP08
title: Route status bypass imports (bulk-edit)
dependencies:
- WP07
requirement_refs:
- FR-014
- C-004
- C-007
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T029
- T030
- T031
- T032
phase: Phase 4 - Facade
assignee: ''
agent: "claude:opus:python-pedro:implementer"
shell_pid: "2867679"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Route status bypass imports (bulk-edit)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below). This WP is a **bulk edit** — also load `/spk-doctrine-bulk-edit` and consult the occurrence map before any change.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Rewrite the ~225 deep `status.*` submodule imports outside `status/` to the facade or `MissionStatus`, per the finalized occurrence map.

- FR-014. C-004 (exemptions), C-007 (bulk-edit). Enables WP09.

## Context & Constraints

- **Bulk-edit guardrail (DIRECTIVE_035)**: `meta.json::change_mode == bulk_edit`; [occurrence_map.yaml](../occurrence_map.yaml) is authoritative. Consult it before touching any `specify_cli.status.*` import.
- Exemptions (do NOT change): `coordination/status_transition.py`, `coordination/transaction.py`.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T029 – Rewrite PROMOTE imports to the facade [P]
- **Steps**: For PROMOTE submodules (e.g. `models`, `transitions`, `progress`, `views`, `validate`), rewrite `from specify_cli.status.<sub> import X` → `from specify_cli.status import X`.

### Subtask T030 – Rewrite ROUTE imports to MissionStatus
- **Steps**: For ROUTE submodules (`store`, `reducer`, `lane_reader`, `emit`, `lifecycle_events`, …), replace mission-level read/write usage with `MissionStatus.load()/.claim()/.transition()` calls (coordinate with WP10).

### Subtask T031 – Handle REVIEW/PRIVATE
- **Steps**: Apply the WP07 final decision per submodule.

### Subtask T032 – Preserve plumbing exemptions
- **Steps**: Leave the two `coordination/` plumbing files untouched.

## Test Strategy

- After each package batch: `pytest` for that package green; WP01 ratchet green.

## Risks & Mitigations

- Bulk-edit silent breakage → occurrence-map-driven, batch by package, ratchet between batches.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm ROUTE sites genuinely use `MissionStatus` (not a facade re-export of the same internal), exemptions intact, and no behavior change. Diff against the occurrence map.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T09:22:55Z – claude:opus:python-pedro:implementer – shell_pid=2867679 – Started implementation via action command
