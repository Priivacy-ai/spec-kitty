---
work_package_id: WP10
title: Centralize Hardcoded Doctrine Paths in Compliance Guard Tests
dependencies: "[]"
requirement_refs:
- FR-013
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
history:
- at: '2026-04-03T20:00:00Z'
  actor: human
  action: WP added from WP08 architectural review follow-up item 1
agent_profile: python-implementer
authoritative_surface: tests/
execution_mode: code_change
lane: planned
owned_files:
- tests/doctrine/test_template_lane_guard.py
- tests/doctrine/test_lane_regression_guard.py
- tests/doctrine/test_template_compliance.py
task_type: implement
---

# Work Package Prompt: WP10 -- Centralize Hardcoded Doctrine Paths in Compliance Guard Tests

## Objectives & Success Criteria

- Extract duplicated `REPO_ROOT / "src" / "doctrine" / "missions"` path literals from 3 compliance guard test files into a shared constant
- All 3 test files import and use the shared constant instead of hardcoding the path
- All existing tests continue to pass with no regressions

## Context & Constraints

- **Origin**: WP08 architectural review finding T028
- The 3 compliance guard test files intentionally hardcode the doctrine source path to act as "layout canaries" — they should break if the directory moves
- The constant should still be a direct path (not routed through `MissionTemplateRepository`) to preserve the canary behavior
- The goal is DRY, not abstraction: one constant defined once, imported by all 3 files

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP10 --base WP08`

## Subtasks & Detailed Guidance

### Subtask T036 -- Define shared DOCTRINE_SOURCE_ROOT constant

- **Purpose**: Single source of truth for the doctrine missions path used in compliance tests.
- **Steps**:
  1. Determine the best location for the constant. Options:
     - `tests/doctrine/conftest.py` (if it exists, or create it)
     - A shared `tests/constants.py` or `tests/doctrine/constants.py`
  2. Define `DOCTRINE_SOURCE_ROOT = REPO_ROOT / "src" / "doctrine" / "missions"` (or equivalent)
  3. Ensure `REPO_ROOT` is resolved consistently with how the test files currently resolve it
- **Files**: New or existing conftest/constants module

### Subtask T037 -- Update compliance guard tests to use the constant

- **Purpose**: Replace hardcoded path literals with the shared constant.
- **Files**:
  - `tests/doctrine/test_template_lane_guard.py`
  - `tests/doctrine/test_lane_regression_guard.py`
  - `tests/doctrine/test_template_compliance.py`
- **Steps**:
  1. In each file, replace all instances of `REPO_ROOT / "src" / "doctrine" / "missions"` (or equivalent) with an import of the shared constant
  2. Verify no other hardcoded doctrine path variants remain in these files

### Subtask T038 -- Verify all tests pass

- **Purpose**: Confirm no regressions.
- **Steps**:
  1. Run the 3 affected test files: `pytest tests/doctrine/test_template_lane_guard.py tests/doctrine/test_lane_regression_guard.py tests/doctrine/test_template_compliance.py -v`
  2. Run the full doctrine test suite: `pytest tests/doctrine/ -v`
  3. Confirm zero failures

## Risks & Mitigations

- The test files may resolve `REPO_ROOT` differently (e.g., `Path(__file__).resolve().parents[N]`). Verify all 3 use the same resolution before extracting the constant.

## Review Guidance

- Verify the constant preserves the canary behavior (direct path, not abstracted through repository)
- Verify all 3 files import from the same location
- Confirm no duplicated path literals remain

## Activity Log

- 2026-04-03T20:00:00Z -- human -- WP created from WP08 review follow-up item 1.
- 2026-04-03T19:54:20Z – unknown – Moved to in_progress
- 2026-04-03T20:01:29Z – unknown – Done override: WP10 merged into feature branch; 1221 doctrine tests pass; CLI transition bug prevents normal for_review->approved->done flow
