---
work_package_id: WP04
title: Fix Migration Test Logic
dependencies: []
requirement_refs:
- FR-005
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
agent: "opencode"
role: "reviewer"
shell_pid: "194292"
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: tests/upgrade/
execution_mode: code_change
lane: planned
owned_files:
- tests/upgrade/test_m_0_12_0_documentation_mission_unit.py
task_type: implement
---

# Work Package Prompt: WP04 -- Fix Migration Test Logic

## Objectives & Success Criteria

- Determine whether the test or the migration is wrong regarding `command-templates/` directory copying
- Apply the correct fix
- Test passes with zero failures

## Context & Constraints

- **File under test**: `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py`
- **Test file**: `tests/upgrade/test_m_0_12_0_documentation_mission_unit.py`
- **Issue**: Test asserts `command-templates/` should NOT be copied by the migration, but the migration copies the full directory tree
- **Constraint C-001**: Prefer fixing the test. Only fix the migration if it's genuinely wrong (the test is asserting correct intended behavior).

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP04`

## Subtasks & Detailed Guidance

### Subtask T013 -- Investigate migration behavior

- **Purpose**: Understand whether `command-templates/` should or should not be copied.
- **Steps**:
  1. Read `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py` -- find the copy logic
  2. Look for comments or commit messages explaining the intent
  3. Check if `command-templates/` are deployed separately via a different mechanism (e.g., the agent template migration `m_0_9_1`)
  4. Check `src/doctrine/missions/documentation/` to see if `command-templates/` exists there
- **Decision criteria**:
  - If `command-templates/` are deployed by the general agent template migration: the doc migration should NOT copy them (test is correct, fix migration)
  - If `command-templates/` are mission-specific and must be deployed by this migration: the test is wrong (fix test)

### Subtask T014 -- Apply the fix

- **If test is wrong**: Update the assertion to expect `command-templates/` to exist after migration
- **If migration is wrong**: Add filtering to skip `command-templates/` directory during the copy. This is an exception to C-001 (production code change), documented in the plan.
- **Whichever you change, add a comment explaining WHY** so the next person doesn't repeat this investigation.

### Subtask T015 -- Verify test passes

- **Command**:
  ```bash
  pytest tests/upgrade/test_m_0_12_0_documentation_mission_unit.py -v
  ```
- **Expected**: All tests pass, zero errors.
- **Also run**: `pytest tests/upgrade/ -v` to ensure no other migration tests broke.

## Risks & Mitigations

- Changing migration behavior could affect existing projects that already ran the migration → check if the migration is idempotent and whether re-running it would cause issues
- Other migration tests may depend on the same behavior → run the full `tests/upgrade/` suite

## Review Guidance

- Verify the decision rationale is documented in a code comment
- If migration was changed, verify it's still idempotent
- Check that the fix doesn't break the general agent template deployment flow

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
- 2026-04-03T14:39:20Z – opencode – Already resolved by upstream 8842ffa7. 21/21 target tests pass, 335/335 upgrade tests pass. No code changes needed.
- 2026-04-03T14:39:26Z – opencode:unknown:generic:unknown – shell_pid=194292 – Started review via workflow command
- 2026-04-03T14:39:31Z – opencode – shell_pid=194292 – Review passed: No code changes needed — already resolved by upstream 8842ffa7. 21/21 target tests pass, 335/335 upgrade tests pass.
- 2026-04-03T16:47:46Z – opencode – shell_pid=194292 – Moved to done
