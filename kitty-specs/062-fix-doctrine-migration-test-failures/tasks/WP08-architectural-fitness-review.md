---
work_package_id: WP08
title: Architectural Fitness Review
dependencies: [WP07]
requirement_refs:
- FR-007
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
agent: "opencode"
shell_pid: "254171"
role: "reviewer"
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer
authoritative_surface: kitty-specs/062-fix-doctrine-migration-test-failures/
execution_mode: review
lane: planned
owned_files:
- kitty-specs/062-fix-doctrine-migration-test-failures/review.md
task_type: review
---

# Work Package Prompt: WP08 -- Architectural Fitness Review

## Objectives & Success Criteria

- Architect reviews all changes from WP01-07 for architectural alignment
- Produces a verdict: approve or request-changes with documented rationale
- Any systemic issues are documented as follow-up items (not fixed in this mission)

## Context & Constraints

- **Assigned to**: Architect Alphonso (`architect` profile)
- This is a review WP, not implementation. No code changes expected.
- **Doctrine package**: `src/doctrine/` is the new canonical location for mission assets
- **MissionTemplateRepository**: The abstraction layer tests should use instead of hardcoded paths
- **Related issue**: Priivacy-ai/spec-kitty#361 (TypedDict codegen for dashboard API)

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### Subtask T028 -- Review path convention consistency

- **Purpose**: Ensure all fixed tests use `MissionTemplateRepository` consistently, not a mix of hardcoded `src/doctrine/` paths.
- **Steps**:
  1. Grep all test files touched by WP01-04 for path patterns:
     ```bash
     grep -rn "src/doctrine/missions" tests/
     grep -rn "src/specify_cli/missions" tests/
     grep -rn "MissionTemplateRepository" tests/
     ```
  2. Flag any test that hardcodes `src/doctrine/missions/` directly instead of using the repository
  3. Document whether this is acceptable or should be standardized

### Subtask T029 -- Evaluate dashboard JS backward-compat approach

- **Purpose**: The JS fix uses `data.missions || data.features` -- is this the right pattern?
- **Questions to answer**:
  - Is there any scenario where the old `data.features` key would be served? (No -- the backend was changed)
  - Does the `||` pattern mask future bugs? (Yes, if someone renames `missions` again)
  - Should we do a clean break (just `data.missions`) or keep the fallback?
- **Recommendation format**: Approve current approach with rationale, or request clean break with migration path

### Subtask T030 -- Grep for remaining feature-to-mission rename gaps

- **Purpose**: The doctrine migration renamed many `feature` references to `mission`. Are there more lurking?
- **Steps**:
  1. Search for common patterns:
     ```bash
     grep -rn "feature_dir" src/specify_cli/ --include="*.py" | grep -v test | grep -v __pycache__
     grep -rn "active_feature" src/specify_cli/ --include="*.py" | grep -v test
     grep -rn "feature_id" src/specify_cli/ --include="*.py" | grep -v test | grep -v __pycache__
     ```
  2. For each hit, determine if it's:
     - A legitimate use of "feature" (e.g., spec-kitty features, Python language features)
     - A missed rename that should be `mission_dir` / `active_mission` / etc.
  3. Document any missed renames as follow-up items

### Subtask T031 -- Produce review verdict

- **Purpose**: Formal review output.
- **Output format**:
  ```markdown
  ## Architectural Review: Mission 062
  
  **Verdict**: [APPROVE / REQUEST CHANGES]
  **Reviewer**: Architect Alphonso
  **Date**: [date]
  
  ### Findings
  1. [Finding with rationale]
  2. [Finding with rationale]
  
  ### Follow-up Items
  - [Item for future mission]
  - [Item for future mission]
  
  ### Approval Conditions
  - [Any conditions for approval, or "None -- approved as-is"]
  ```
- Write this to `kitty-specs/062-fix-doctrine-migration-test-failures/review.md`

## Risks & Mitigations

- Architect may find issues requiring additional WPs → document as follow-up missions, do not expand scope of 062
- The grep for rename gaps may produce false positives → the architect should use judgment to filter

## Review Guidance

- This IS the review WP -- the architect is the reviewer
- Focus on architectural patterns, not line-level code review (that happens in PR review)
- The verdict should be actionable: either approve or list specific changes needed

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
- 2026-04-03T19:02:09Z – opencode:unknown:generic:unknown – shell_pid=254171 – Started implementation via workflow command
- 2026-04-03T19:13:45Z – opencode – shell_pid=254171 – Architectural review complete. Verdict: APPROVE with follow-up items. All subtasks T028-T031 done. Force-override: review.md is in WP08 owned_files allowlist.
- 2026-04-03T19:31:07Z – opencode:unknown:generic:unknown – shell_pid=254171 – Started review via workflow command
