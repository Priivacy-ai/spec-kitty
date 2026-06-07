---
work_package_id: WP09
title: Widen status boundary test repo-wide
dependencies:
- WP08
requirement_refs:
- FR-015
- FR-016
- NFR-003
- NFR-005
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T033
- T034
- T035
phase: Phase 4 - Facade
assignee: ''
agent: ''
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: 'tests/architectural/test_status_module_boundary.py'
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_status_module_boundary.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Widen status boundary test repo-wide

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below).

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Widen `tests/architectural/test_status_module_boundary.py` from the 6 WP03 packages to enforce all of `src/specify_cli`, locking in the WP08 migration.

- FR-015/016. NFR-003 (test bites), NFR-005 (≤15 s). SC-003.

## Context & Constraints

- Contract: [contracts/status_boundary.md](../contracts/status_boundary.md). Do this AFTER WP08 (else the test is red).
- Exemptions preserved: `coordination/status_transition.py`, `coordination/transaction.py` (C-004).

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T033 – Widen scope
- **Steps**: Change the pytestarch rule + AST scan from the WP03 package allowlist to all of `src/specify_cli` (excluding `status/` itself and the two exempt plumbing files).
- **Files**: `tests/architectural/test_status_module_boundary.py`.

### Subtask T034 – Exemptions + injection proof
- **Steps**: Keep the documented exemptions; retain/extend the SR-3 injection proof so the widened test is non-vacuous.

### Subtask T035 – Confirm zero + timing
- **Steps**: `pytest` green with zero non-exempt violations; assert scan ≤15 s.

## Test Strategy

- `pytest tests/architectural/test_status_module_boundary.py -q` green; `grep -rn "from specify_cli\.status\." src/ --include="*.py" | grep -v "src/specify_cli/status/"` → only the two exempt lines.

## Risks & Mitigations

- Test must bite → keep the injection proof. Performance → AST scan, not per-file subprocess.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm the widened scope is real (not an allowlist that re-exempts the migrated packages) and the test fails on an injected violation.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
