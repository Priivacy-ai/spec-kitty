---
work_package_id: WP03
title: Repair Mock Targets and Missing Fixtures
dependencies: []
requirement_refs:
- FR-003
- FR-004
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
agent: "opencode"
role: "reviewer"
shell_pid: "191531"
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: tests/
execution_mode: code_change
lane: planned
owned_files:
- tests/init/test_worktree_topology.py
- tests/agent/cli/commands/test_workflow_profile_injection.py
- tests/init/test_feature_detection_integration.py
task_type: implement
---

# Work Package Prompt: WP03 -- Repair Mock Targets and Missing Fixtures

## Objectives & Success Criteria

- Fix 3 test files with broken mock targets, missing directories, or stale import assertions
- All 3 test files pass with zero failures and zero errors
- No production code changed

## Context & Constraints

- These failures are more complex than simple path swaps -- each requires investigation of the actual production code to find the correct fix.
- **Constraint**: Do not blindly swap paths. Read the production code, trace the import chain, then fix.
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md`

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP03`

## Subtasks & Detailed Guidance

### Subtask T009 -- Fix test_worktree_topology.py mock target

- **Purpose**: 4 tests in `TestMaterializeWorktreeTopology` fail because they mock `specify_cli.core.worktree_topology.read_frontmatter` but the function is no longer imported there.
- **File**: `tests/init/test_worktree_topology.py`
- **Investigation steps**:
  1. Read `src/specify_cli/core/worktree_topology.py` to find how `read_frontmatter` is used
  2. If it's imported: note the source module (e.g., `from specify_cli.frontmatter import read_frontmatter`)
  3. The mock must patch where it's looked up, not where it's defined. If `worktree_topology.py` imports it as `from specify_cli.frontmatter import read_frontmatter`, then mock `specify_cli.core.worktree_topology.read_frontmatter`
  4. If `read_frontmatter` was removed/renamed: find the replacement function and update both the mock target and the test logic
- **Failing tests** (all 4 in `TestMaterializeWorktreeTopology`):
  - `test_flat_mission_no_stacking`
  - `test_linear_chain_stacking`
  - `test_diamond_pattern`
  - `test_wp_without_context_gets_none_base`
- **Parallel?**: Yes -- independent file

### Subtask T010 -- Fix test_workflow_profile_injection.py

- **Purpose**: `test_human_in_charge_skips_injection` fails because it references `src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml` but the `_proposed/` directory doesn't exist under `agent_profiles/`.
- **File**: `tests/agent/cli/commands/test_workflow_profile_injection.py`
- **Investigation steps**:
  1. Check `src/doctrine/agent_profiles/` directory structure -- `shipped/` exists, `_proposed/` may not
  2. If `human-in-charge.agent.yaml` exists in `shipped/`: update the test path to use `shipped/`
  3. If the test intentionally uses `_proposed/` as a fixture (testing proposed profile behavior): create the directory and file as a test fixture using `tmp_path`
  4. Read the test to understand what it's actually testing -- the path may be constructed dynamically
- **Parallel?**: Yes -- independent file

### Subtask T011 -- Fix test_feature_detection_integration.py

- **Purpose**: 2 tests fail: `test_centralized_imports_used` and `test_acceptance_module_backward_compatible` -- both validate import structure against the refactored module.
- **File**: `tests/init/test_feature_detection_integration.py`
- **Investigation steps**:
  1. Read the failing test assertions to understand what imports they expect
  2. Read `src/specify_cli/cli/commands/implement.py` (or the module they validate) to see current import structure
  3. Update test assertions to match the actual imports
  4. If the test validates backward compatibility: check if the old import paths still work via shims
- **Parallel?**: Yes -- independent file

### Subtask T012 -- Verify all 3 files pass

- **Command**:
  ```bash
  pytest tests/init/test_worktree_topology.py \
         tests/agent/cli/commands/test_workflow_profile_injection.py \
         tests/init/test_feature_detection_integration.py -v
  ```
- **Expected**: All tests pass, zero errors.

## Risks & Mitigations

- T009: If `read_frontmatter` was entirely removed, the test logic needs rewriting -- not just a mock target fix. If this happens, document the scope increase and proceed with the rewrite.
- T010: The `_proposed/` directory pattern may be intentional for other doctrine modules but simply not created for agent_profiles yet. Check if a migration or CLI command is supposed to create it.
- T011: The import validation tests may be testing a contract that's genuinely broken in the refactored code -- in that case, the test is correct and the production code needs a shim.

## Review Guidance

- For each fix, verify the mock target matches the actual import chain (not just the definition site)
- Check that fixture files are realistic (not empty placeholders)
- Verify no production code was changed

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
- 2026-04-03T14:37:33Z – opencode – T010 fixed (_proposed/ → shipped/), T009/T011 already passing, T012 all 43 tests pass
- 2026-04-03T14:38:03Z – opencode:unknown:generic:unknown – shell_pid=191531 – Started review via workflow command
- 2026-04-03T14:38:16Z – opencode – shell_pid=191531 – Review passed: Implementation committed directly to base branch (single-file path fix). _PROPOSED_DIR→_SHIPPED_DIR matches actual filesystem. T009/T011 non-issues. 43/43 pass.
- 2026-04-03T16:47:45Z – opencode – shell_pid=191531 – Moved to done
