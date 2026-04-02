---
work_package_id: WP02
title: Fix Terminology and Assertion Mismatches
dependencies: []
requirement_refs:
- FR-002
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: tests/
execution_mode: code_change
lane: planned
owned_files:
- tests/missions/test_feature_lifecycle_unit.py
- tests/sync/test_emitter_origin.py
task_type: implement
---

# Work Package Prompt: WP02 -- Fix Terminology and Assertion Mismatches

## Objectives & Success Criteria

- Fix 2 test files asserting old terminology (`"Feature"` vs `"Mission"`, `feature=` vs `mission=`)
- Both test files pass with zero failures

## Context & Constraints

- **Root cause**: The codebase renamed `Feature` to `Mission` terminology (commit `1c5a7927` for aggregate_type, broader refactor for parameter names)
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md`

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP02`

## Subtasks & Detailed Guidance

### Subtask T006 -- Fix test_emitter_origin.py aggregate_type assertion

- **Purpose**: Test asserts `aggregate_type == "Feature"` but production code now emits `"Mission"`.
- **File**: `tests/sync/test_emitter_origin.py`
- **Line**: 203
- **Current code**:
  ```python
  assert event["aggregate_type"] == "Feature"
  ```
- **Fix**:
  ```python
  assert event["aggregate_type"] == "Mission"
  ```
- **Verification**: Before fixing, confirm the production code emits `"Mission"` by reading `src/specify_cli/tracker/origin.py` or `src/specify_cli/sync/emitter.py` to find where `aggregate_type` is set.
- **Parallel?**: Yes -- independent file

### Subtask T007 -- Fix test_feature_lifecycle_unit.py parameter name

- **Purpose**: Test mock asserts `feature=None` but the function now accepts `mission=None`.
- **File**: `tests/missions/test_feature_lifecycle_unit.py`
- **Line**: 117 (and potentially other `assert_called_once_with` calls)
- **Steps**:
  1. Read `src/specify_cli/cli/commands/agent/feature.py` to find `accept_feature()` function signature
  2. Read `src/specify_cli/accept.py` (or wherever `top_level_accept` lives) to confirm parameter name
  3. Update all `mock_accept.assert_called_once_with(feature=...)` to use the correct parameter name
  4. Check if there are similar assertions in `test_merge_command_*` tests in the same file
- **Parallel?**: Yes -- independent file
- **Note**: There are likely multiple test functions in this file (accept + merge). Check ALL mock assertions.

### Subtask T008 -- Verify both files pass

- **Command**:
  ```bash
  pytest tests/sync/test_emitter_origin.py \
         tests/missions/test_feature_lifecycle_unit.py -v
  ```
- **Expected**: All tests pass, zero errors.

## Risks & Mitigations

- The parameter rename may affect more assertions than identified → grep the test file for `feature=` to catch all instances
- The `top_level_accept` function may have been renamed too → read the import in the test file and follow the chain

## Review Guidance

- Verify the assertions match the actual production function signatures
- Check no other test files in the suite assert old terminology

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
