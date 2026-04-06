---
work_package_id: WP08
title: End-to-End Audit + Cleanup
dependencies: [WP07]
requirement_refs:
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main.
subtasks:
- T045
- T046
- T047
- T048
phase: Phase D - Validation
assignee: ''
agent: ''
shell_pid: ''
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/064-complete-mission-identity-cutover/
execution_mode: code_change
owned_files:
- kitty-specs/064-complete-mission-identity-cutover/audit-results.md
---

# Work Package Prompt: WP08 – End-to-End Audit + Cleanup

## Objective

Perform a comprehensive grep-based audit of the entire codebase for leaked feature-era surfaces. Fix anything found. Document the audit results.

## Context

Success criterion 5: "No grep for `feature_slug` across live runtime paths (excluding test fixtures and explicit migration/upgrade modules) returns results."

This is the final verification that the cutover is complete. Previous WPs should have removed all feature-era surfaces, but the failed first attempt proved that secondary paths hide leaks. This audit catches anything missed.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T045: Grep Audit — feature_slug

**Purpose**: No live runtime path may reference `feature_slug`.

**Steps**:
1. Run: `grep -rn "feature_slug" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/" | grep -v "migrate"`
2. Expected: zero results
3. If results found: classify each as:
   - **Bug**: live runtime path still using feature_slug → FIX
   - **Migration-only**: in upgrade/migration code → VERIFY it's unreachable from runtime
   - **Comment/docstring**: remove or update the comment
4. Record findings

### T046: Grep Audit — Forbidden Event Types and Error Codes

**Purpose**: No live path may reference legacy event types or error codes.

**Steps**:
1. `grep -rn "FEATURE_NOT_FOUND\|FEATURE_NOT_READY" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → must be zero
2. `grep -rn "FeatureCreated\|FeatureCompleted" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → must be zero
3. `grep -rn "create.feature\|create_feature" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → check each result
4. Fix any leaks found

### T047: Grep Audit — aggregate_type and mission_key

**Purpose**: No live path may emit `aggregate_type: "Feature"` or use `mission_key`.

**Steps**:
1. `grep -rn 'aggregate_type.*Feature' src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → must be zero
2. `grep -rn "mission_key" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → must be zero
3. `grep -rn "feature_number" src/specify_cli/ --include="*.py" | grep -v "upgrade/" | grep -v "migration/"` → check each result (may appear in meta.json reading for migration)
4. Fix any leaks found

### T048: Document Audit Results

**Purpose**: Record the audit outcome for acceptance review.

**Steps**:
1. Create `kitty-specs/064-complete-mission-identity-cutover/audit-results.md`
2. Document:
   - Date of audit
   - Grep commands executed
   - Results (zero or list of findings with disposition)
   - Fixes applied (if any)
   - Final pass/fail status for each success criterion
3. Run full test suite one final time: `pytest tests/ -v`
4. Record test suite pass/fail

## Definition of Done

- [ ] All 4 grep audits pass (zero results on live paths)
- [ ] Any leaks found are fixed and re-audited
- [ ] Audit results documented
- [ ] Full test suite passes
- [ ] Success criteria 5, 7 verified

## Risks

- Grep patterns may miss non-obvious references (e.g., string concatenation) — also search for partial matches like `feature_` and `_feature`
