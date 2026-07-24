---
work_package_id: WP16
title: Retire new_checkout_paths (IC-07f)
dependencies:
- WP09
- WP10
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T079
- T080
- T081
- T082
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP16 – Retire new_checkout_paths (IC-07f)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Retire `new_checkout_paths` "preserved without cleanup" across ~10 sites (`:1115-1632`) in `tasks_move_task.py` — a parameter threaded through four function signatures and a dataclass field, not a console block. The byproduct is enrolled in the owner instead. Sibling-gate CLEARED (#2888).

**Done** = `new_checkout_paths` absent from `src/`; the "preserved without cleanup" byproduct is enrolled in the owner; behaviour preserved (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry row #6). Plan IC-07(f); research/sibling-mission-coordination.md (re-diff DONE).
- **Single file (grep-confirmed)**: `cli/commands/agent/tasks_move_task.py`. Genuinely parallel.
- **Re-confirm line numbers at implement time** — the sibling (#2888) refactored this file: `_TransitionGateInputs` moved to `:1172`, `dirty_before` to `:1182`, `new_checkout_paths` at `:1076/:1494/:1545`. Further landing folds may have shifted them again.
- `review/pre_review_gate.py` remains **out of scope** entirely.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T079 – Re-confirm line numbers

- **Steps**: Re-locate `_TransitionGateInputs`, its `dirty_before` field, and the `new_checkout_paths` sites before editing.

### Subtask T080 – Retire across ~10 sites

- **Steps**: Remove `new_checkout_paths` — the parameter threaded through four signatures + the dataclass field + the JSON metadata emit + the docstring + the dirty-set capture and threading + the console emit + the `dirty_after - dirty_before` computation. Enrol the byproduct in the owner.

### Subtask T081 – Delete the registry row

- **Steps**: Delete this mechanism's row in the WP10 registry.

### Subtask T082 – Migrate tests; preserve behaviour

- **Steps**: Migrate mechanism-asserting tests; no previously-succeeding operation now fails.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/specify_cli/cli/commands/agent/ -q`.

## Risks & Mitigations

- Owns `tasks_move_task.py` only. Size for the ~10-site footprint, not the console block.

## Review Guidance

- Confirm the parameter is gone from all four signatures + the dataclass field, and the byproduct is enrolled in the owner (not "preserved without cleanup").

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
