---
work_package_id: WP04
title: Structured refusal errors, --json contract, and architectural fence reconciliation
dependencies:
- WP02
- WP03
requirement_refs:
- FR-011
- NFR-003
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: tests/architectural/test_no_production_worktree_guard_bypass.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_create.py
- tests/architectural/test_no_production_worktree_guard_bypass.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 - Structured refusal errors, --json contract, and architectural fence reconciliation

## Objective

Confirm and, if needed, extend the `--json` error-code contract from `contracts/checkout-ownership-cli-contract.md` is fully realized across both `mission create` (WP02) and `next` (WP03), and confirm the existing architectural fence (`tests/architectural/test_no_production_worktree_guard_bypass.py`) still holds for `allow_worktree_context` after WP02/WP03 land, per its own documented intent (research D-3: the fence's docstring anticipates exactly this kind of resolution-based replacement and says explicitly not to weaken it silently).

## Context

This WP is primarily a VERIFICATION and reconciliation pass across WP02+WP03's combined output, plus closing any gaps in FR-011's structured-error requirement that individual WPs didn't fully cover in isolation (e.g., confirming `error_code` values are IDENTICAL strings across both CLI surfaces, confirming `mission_create.py:_print_worktree_navigation_hint`'s substring match wasn't accidentally broadened to swallow the new error classes).

Read `contracts/checkout-ownership-cli-contract.md`'s "Error Taxonomy" table in full — it is the binding cross-surface contract this WP verifies.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T013 - Cross-surface refusal-envelope consistency audit

- **Purpose**: Prove `mission create` and `next` emit IDENTICAL `error_code` strings and the contract-required `"success": false` field for the same `OwnershipValidationResult`, satisfying FR-011's structured-refusal contract.
- **Steps**:
  1. Write a parametrized test in the owned architectural fence that drives both `mission create --owned-checkout <target> --json` and `next --owned-checkout <target> --json` against the same real-git fixture for `NESTED`, `FOREIGN_OR_MISMATCHED`, and `BROKEN_POINTER`.
  2. Assert both surfaces exit non-zero, emit byte-identical `error_code` values, and include `"success": false` in their JSON envelopes for all three refusal classes.
  3. Reconcile the discovered gap in `src/specify_cli/cli/commands/agent/mission_create.py` with the minimal refusal-envelope fix; do not alter refusal classification or default behavior.
- **Files**: `src/specify_cli/cli/commands/agent/mission_create.py`, `tests/architectural/test_no_production_worktree_guard_bypass.py`

### Subtask T014 - Architectural fence verification

- **Purpose**: Confirm NFR-003 holds.
- **Steps**:
  1. Run `tests/architectural/test_no_production_worktree_guard_bypass.py` after WP01-WP03 land. It must still pass — `allow_worktree_context=True` must still have zero production (`src/`) call sites.
  2. Read the fence's docstring (lines 1-19) again now that the feature exists: it explicitly anticipates "the cwd-vs-target guard... reshaped to validate the resolution target instead." Confirm WP01-WP03's design (a NEW parameter, `owned_checkout`, validated independently) is consistent with that anticipated shape, OR document in this WP's Activity Log why it deliberately diverges.
  3. If the fence's own test (`test_detector_bites_on_a_planted_bypass`) needs updating because the AST-scan target surface changed shape, update it narrowly — do not weaken the scan's coverage.
- **Files**: `tests/architectural/test_no_production_worktree_guard_bypass.py` (0-20 line diff, likely none needed — this subtask may conclude "no change required")

### Subtask T015 - `_print_worktree_navigation_hint` regression check

- **Purpose**: Confirm WP02's Risk (plan.md IC-04) didn't materialize.
- **Steps**:
  1. Re-read `mission_create.py:_print_worktree_navigation_hint` (lines 228-247) as it stands after WP02. Confirm its `"worktree" not in error_msg.lower()` guard only fires for the UNCHANGED, existing `MissionCreationError` path, and does NOT accidentally also match the new `NESTED`/`FOREIGN_OR_MISMATCHED`/`BROKEN_POINTER` error messages (which may also legitimately contain the word "worktree").
  2. If it does incorrectly match, narrow the guard (e.g., check the exception TYPE rather than a message substring) as part of this WP.
- **Files**: `src/specify_cli/cli/commands/agent/mission_create.py` (0-15 line diff if a fix is needed — note: this file is NOT in this WP's `owned_files` list; if a fix is required here, it must be coordinated as a small follow-up commit attributed to WP02's surface, or this WP's `owned_files` should be updated via `wps.yaml` before making the edit — do not silently edit outside your declared ownership)

## Test Strategy

- `.venv/bin/pytest tests/architectural/test_no_production_worktree_guard_bypass.py tests/agent/ -q`

## Risks & Mitigations

- **Risk**: T015 may require editing a file outside this WP's `owned_files`. **Mitigation**: escalate via `wps.yaml` ownership update (add the file to WP04's `owned_files`, remove overlap with WP02) rather than silently crossing the ownership boundary — this preserves the "no two WPs may overlap" invariant `finalize-tasks` enforces.

## Definition of Done

- [ ] `error_code` values are byte-identical and both JSON envelopes contain `"success": false` across `mission create` and `next` for `NESTED`, `FOREIGN_OR_MISMATCHED`, and `BROKEN_POINTER`.
- [ ] `tests/architectural/test_no_production_worktree_guard_bypass.py` passes.
- [ ] `_print_worktree_navigation_hint` does not mis-fire on the new error classes (verified by test, not just inspection).

## Reviewer Guidance

- This WP is the cross-surface consistency gate — check it actually exercises BOTH CLI surfaces in the same test and asserts both the error code and `"success": false` envelope field, not two separate tests that could drift independently later.

**Implementation command**: `spec-kitty agent action implement WP04 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
- 2026-08-11T18:39:58Z – orchestrator – shell_pid=28365 – Carry-forward acceptance gate from WP03 Prime Op 01KZS0QVDFRH5S3DASD31YM4E0: real installed-CLI linked mission content and per-checkout runtime state must resolve from the same explicitly-owned root, with no primary content fallback. Prime's synthetic probe observed mission content reads anchoring primary while FR-007 runtime state routed linked. Reconcile error-contract/fence behavior; if real mission-create→next reproduces divergence, treat as blocking and repair under WP04/WP05/#3128 scope before mission acceptance.
- 2026-08-11T19:17:25Z – codex – shell_pid=28365 – RED corrected after PDB proved an underscore-bearing generated slug hit validation before ownership; harness now uses kebab-case. Intended contract RED: 3 failed/3 passed across real-git nested, foreign, broken-pointer targets. One-line mission-create JSON envelope fix then exact suite passed twice (6/6), post-format 6/6, prescribed architectural+agent gate 1483 passed/20 skipped, runtime/ownership gate 201 passed, Ruff clean/formatted, mypy --strict clean. Test locality: cross-surface refusal and navigation-hint probes remain in the sole owned architectural reconciliation surface.
