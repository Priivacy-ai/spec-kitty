---
work_package_id: WP04
title: 'Close-out verification and #557 closure'
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane-based worktree allocated by finalize-tasks. Branch from planning_base_branch, merge into merge_target_branch.
subtasks:
- T018
- T019
- T020
history:
- at: '2026-04-13T04:59:36Z'
  by: spec-kitty.tasks
  note: WP created during task generation
authoritative_surface: kitty-specs/retire-mission-identity-drift-window-01KP2JNZ/
execution_mode: planning_artifact
owned_files:
- kitty-specs/retire-mission-identity-drift-window-01KP2JNZ/closeout.md
tags: []
---

# WP04: Close-out verification and #557 closure

## Objective

Perform a final verification sweep to confirm complete shim removal, run the full test suite, and prepare the closure comment for GitHub issue #557.

## Context

This is the final WP in the mission. WP01-WP03 performed the actual code and test changes. This WP verifies the changes are complete and prepares the administrative closure of issue #557.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Implementation

### Subtask T018: Grep audit

**Purpose**: Confirm that `legacy_aggregate_id` and the `effective_aggregate_id` slug fallback are completely absent from production source code.

**Steps**:
1. Run: `grep -r legacy_aggregate_id src/specify_cli/`
   - **Expected**: Zero results
   - If any results found: document them and flag as missed by WP01/WP02

2. Run: `grep -r effective_aggregate_id src/specify_cli/`
   - **Expected**: Zero results
   - If any results found: document them and flag as missed by WP02

3. Run: `grep -r "drift.window\|drift_window" src/specify_cli/` (case-insensitive)
   - **Expected**: Zero results (or only unrelated drift references in status/doctor.py, status/reconcile.py which are about *status drift*, not *identity drift window*)
   - If identity-drift-window references found: flag for T019

4. Document results in `closeout.md`.

### Subtask T019: Sweep remaining drift-window references

**Purpose**: Remove any remaining identity-drift-window comments or docstrings found by the grep audit.

**Steps**:
1. If T018 found zero identity-drift-window references: mark this subtask as N/A
2. If references found:
   - Evaluate each one — is it about the identity drift window (remove) or status drift detection (keep)?
   - Remove identity-drift-window references
   - Do NOT modify files outside this WP's ownership. If a straggler is in a file owned by WP01/WP02, document it and flag for the reviewer.

### Subtask T020: Prepare close-out comment for GitHub issue #557

**Purpose**: Draft the closure comment that will be posted to #557 when the PR merges.

**Steps**:
1. Create `kitty-specs/retire-mission-identity-drift-window-01KP2JNZ/closeout.md` with:

   ```markdown
   # Close-out: Issue #557

   ## What was removed
   - `legacy_aggregate_id` field from `StatusEvent.to_dict()` serialization
   - `effective_aggregate_id` slug fallback from `emit_mission_created`, `emit_mission_closed`, `emit_mission_origin_bound`
   - `mission_id` changed from optional to mandatory on all sync emitter methods

   ## What was preserved
   - `mission_id: str | None` on `StatusEvent` dataclass (legacy event read tolerance)
   - `mission_slug` as human-readable display field in events and payloads
   - Legacy event deserialization (events written pre-migration)

   ## Verification
   - `grep -r legacy_aggregate_id src/` → 0 results
   - `grep -r effective_aggregate_id src/` → 0 results
   - Full test suite: PASS
   - mypy --strict: PASS

   ## Cross-repo dependency
   - spec-kitty-saas#66: [CONFIRMED COMPLETE]

   ## Closure
   This PR completes the final CLI cleanup for the mission-identity migration
   (ADR 2026-04-09-1). All drift-window compatibility shims have been retired.
   Closing #557.
   ```

2. Fill in actual grep counts and test results from T018.

## Definition of Done

- [ ] Grep audit confirms zero `legacy_aggregate_id` in `src/`
- [ ] Grep audit confirms zero `effective_aggregate_id` fallback in `src/`
- [ ] Any straggler drift-window references documented or removed
- [ ] `closeout.md` written with verification results
- [ ] Close-out comment draft ready for #557

## Risks

- **Very low**: This is verification and documentation only. No production code changes.

## Reviewer Guidance

- Verify the grep audit was actually run (check closeout.md for specific counts)
- Verify the closeout comment accurately reflects what was changed
- Confirm the close-out comment references `spec-kitty-saas#66` completion
