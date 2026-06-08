---
work_package_id: WP03
title: ExecutionContext relocation façade (Stage C)
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Relocation
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "2604776"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: 'src/mission_runtime/context.py'
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/resolution.py
- src/specify_cli/core/execution_context.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – ExecutionContext relocation façade (Stage C)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter. Then load the semantic-compression doctrine via `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer (semantic compression)

This WP is a **behavior-preserving relocation**, not a rewrite. Map what must not change first (the parity ratchet is the behavioral envelope), then relocate. **No parallel resolver may survive** — the façade is the single path; the old location becomes a thin shim, not a second implementation. Evidence over intuition: ratchet green before and after.

## Objectives & Success Criteria

Relocate `resolve_action_context` + the context value object into `mission_runtime/` as a Stage-C façade that delegates to today's resolver; leave a thin re-export shim at the old path.

- FR-003/004. NFR-001 (behavior-preserving), NFR-002 (no duplication). SC-001.

## Context & Constraints

- Contract: [contracts/mission_runtime_api.md](../contracts/mission_runtime_api.md). Data model: [data-model.md](../data-model.md). Research R-2/R-5. Plan IC-02.
- Today's resolver: `src/specify_cli/core/execution_context.py:230` (`resolve_action_context`) + `ActionContext` (line ~44).
- Keep the WP01 ratchet green throughout.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T011 – Move the context value object
- **Steps**: Move `ActionContext`/`ExecutionContext` into `src/mission_runtime/context.py` as an immutable value object with the fields in data-model.md (mode, target_branch, read/write dirs, …).
- **Files**: `src/mission_runtime/context.py`, `src/specify_cli/core/execution_context.py`.

### Subtask T012 – Relocate the resolver as a Stage-C façade
- **Steps**: Move `resolve_action_context` into `src/mission_runtime/resolution.py`; internally delegate to the existing resolution logic (Stage C). Export both from `mission_runtime/__init__.py`.
- **Files**: `src/mission_runtime/resolution.py`, `src/mission_runtime/__init__.py`.

### Subtask T013 – Thin shim at the old path
- **Steps**: Replace `core/execution_context.py` body with `from mission_runtime import resolve_action_context, ExecutionContext  # transitional shim` (no logic). Remove entirely if nothing imports it.
- **Files**: `src/specify_cli/core/execution_context.py`.

### Subtask T014 – Update internal references; keep ratchet green
- **Steps**: Point first-party callers at `mission_runtime`; run the ratchet.
- **Files**: importers of the old path.

## Test Strategy

- `pytest tests/architectural/test_execution_context_parity.py tests/architectural/test_mission_runtime_surface.py -q` green; `mypy src/mission_runtime` clean.

## Risks & Mitigations

- Import cycles (`mission_runtime` ↔ `specify_cli`): keep the façade dependency-light; respect the layer spine. No second resolver retained.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm exactly one resolver exists, the shim has no logic, and no boundary leak was introduced. Reject any retained parallel path.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T04:48:30Z – claude:opus:randy-reducer:implementer – shell_pid=2604776 – Started implementation via action command
