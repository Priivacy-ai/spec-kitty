---
work_package_id: WP06
title: Add Dashboard API Contract Test
dependencies: [WP05]
requirement_refs:
- FR-010
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: tests/test_dashboard/
execution_mode: code_change
lane: planned
owned_files:
- tests/test_dashboard/test_api_contract.py
task_type: implement
---

# Work Package Prompt: WP06 -- Add Dashboard API Contract Test

## Objectives & Success Criteria

- New test file `tests/test_dashboard/test_api_contract.py` validates JS reads the same keys Python API emits
- Test is marked `pytest.mark.fast` (no server needed)
- Test would have caught the original `data.features` vs `data.missions` bug
- References Priivacy-ai/spec-kitty#361 for future TypedDict codegen approach

## Context & Constraints

- The dashboard is vanilla JS -- no TypeScript, no build step
- The Python API is a `BaseHTTP` handler with inline dict responses
- This test is a pragmatic stop-gap: parse JS as text, assert key presence
- Long-term solution: TypedDict codegen (documented in issue #361)
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md`

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP06 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T019 -- Extract canonical response keys from Python handlers

- **Purpose**: Identify the response keys each API endpoint emits.
- **Files to read**:
  - `src/specify_cli/dashboard/handlers/missions.py` -- `handle_missions_list()` (line 108), `handle_kanban()` (line 130)
  - `src/specify_cli/dashboard/handlers/api.py` -- `handle_health()`, `handle_constitution()`
- **Output**: A Python dict mapping endpoint name to set of response keys:
  ```python
  MISSIONS_LIST_KEYS = {"missions", "active_mission_id", "project_path", "worktrees_root", "active_worktree", "active_mission"}
  KANBAN_KEYS = {"lanes", "is_legacy", "upgrade_needed"}
  ```

### Subtask T020 -- Create test_api_contract.py

- **Purpose**: The contract test that prevents key drift.
- **File**: `tests/test_dashboard/test_api_contract.py`
- **Implementation**:
  ```python
  """Contract test: dashboard JS must reference the keys the Python API emits."""
  from __future__ import annotations

  from pathlib import Path

  import pytest

  pytestmark = pytest.mark.fast

  DASHBOARD_JS = Path("src/specify_cli/dashboard/static/dashboard/dashboard.js")

  # Keys emitted by handle_missions_list() in handlers/missions.py
  MISSIONS_LIST_RESPONSE_KEYS = {
      "missions",
      "active_mission_id",
      "project_path",
      "worktrees_root",
      "active_worktree",
      "active_mission",
  }

  def _js_references_key(js_content: str, key: str) -> bool:
      """Check if JS content references a response key in any common pattern."""
      return (
          f"data.{key}" in js_content
          or f'data["{key}"]' in js_content
          or f"data['{key}']" in js_content
          or f'.{key}' in js_content  # e.g., response.missions
      )

  def test_js_references_missions_list_response_keys():
      """Frontend must destructure the same keys the backend emits."""
      js_content = DASHBOARD_JS.read_text(encoding="utf-8")
      for key in MISSIONS_LIST_RESPONSE_KEYS:
          assert _js_references_key(js_content, key), (
              f"Dashboard JS does not reference API response key '{key}'. "
              f"If the backend renamed this key, update the JS to match."
          )
  ```
- **Notes**:
  - Use a helper function for the key-matching logic to keep assertions readable
  - The `.{key}` pattern catches both `data.missions` and `response.missions`

### Subtask T021 -- Add tests for kanban and constitution endpoints

- **Purpose**: Extend the contract test to cover other API endpoints.
- **Add to the same file**:
  ```python
  KANBAN_RESPONSE_KEYS = {"lanes", "is_legacy", "upgrade_needed"}

  def test_js_references_kanban_response_keys():
      js_content = DASHBOARD_JS.read_text(encoding="utf-8")
      for key in KANBAN_RESPONSE_KEYS:
          assert _js_references_key(js_content, key), (
              f"Dashboard JS does not reference kanban API key '{key}'."
          )
  ```
- **Note**: Only add tests for endpoints where the JS actively destructures the response. If an endpoint's response is passed through opaquely, skip it.

### Subtask T022 -- Verify contract test catches original bug

- **Purpose**: Confirm the test is effective by temporarily reverting the JS fix and checking the test fails.
- **Steps**:
  1. Run the test with current (fixed) JS: should pass
  2. Temporarily change `data.missions` back to `data.features` in the JS
  3. Run the test again: should fail with a clear error message
  4. Revert the temporary change
- **This is a validation step only** -- do not commit the temporary revert.

## Risks & Mitigations

- String matching is brittle if JS is minified or variable aliases are used → acceptable for vanilla JS; document in test docstring
- False positives from `.{key}` matching unrelated code → use more specific patterns if needed

## Review Guidance

- Verify the key sets match the actual Python handler response dicts exactly
- Verify the test would have caught the original bug (T022 validation)
- Check that no endpoint is missing from the contract test

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
