---
work_package_id: WP05
title: Kill doctrine.agent_profiles survivors
dependencies:
- WP04
requirement_refs:
- FR-006
- FR-013
- FR-014
- FR-015
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: feature/711-mutant-slaying
merge_target_branch: feature/711-mutant-slaying
branch_strategy: Planning artifacts for this feature were generated on feature/711-mutant-slaying. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/711-mutant-slaying unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - Doctrine core
agent: "claude"
shell_pid: "2524694"
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/doctrine/
execution_mode: code_change
owned_files:
- tests/doctrine/test_profile_repository.py
- tests/doctrine/agent_profiles/**
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Kill doctrine.agent_profiles survivors

## Objectives & Success Criteria

- Drive mutation score on `doctrine.agent_profiles` to **≥ 60 %** (FR-006, NFR-002). Current baseline: 97 survivors at 2026-04-20 partial snapshot. Fresh re-sample required before starting.

## Context & Constraints

- **Source under test**: `src/doctrine/agent_profiles/` — profile YAML loading, schema validation, shipped-vs-project precedence, invalid-profile warning path.
- **Test files**: `tests/doctrine/test_profile_repository.py` and any sibling test files under `tests/doctrine/agent_profiles/`.
- **Precondition**: Re-sample `uv run mutmut run "doctrine.agent_profiles*"` and pull the current survivor list.
- **WP04 dependency**: Phase-2 work inherits doctrine-test conventions from WP04's resolver kill — reuse fixtures and helpers where they exist.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP05 --base WP04`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T022 – Kill repository / loader survivors

- **Purpose**: `AgentProfileRepository` loads profiles from shipped + project directories. Loader mutations are typically directory-walk branch flips or file-pattern match mutations.
- **Steps**:
  1. Pull current survivor list for the loader class.
  2. **Boundary Pair** on pattern matching: test with a filename that matches (`*.agent.yaml`), one that nearly matches (`*.agent.yml`, one-letter difference), and one unrelated.
  3. **Non-Identity Inputs** on directory fallback: use distinct shipped/project paths; assert loaders inspect both independently.

### Subtask T023 – Kill precedence / merge survivors

- **Purpose**: Project profile overrides shipped profile. Mutation survivors suggest the override logic is not assertion-strength distinguished.
- **Steps**:
  1. Create test fixtures with the **same** profile ID in both shipped and project locations, with **different** field values. Assert the project version wins on every field (not just "overrides happened").
  2. **Boundary Pair** on field-level merge: test a profile with a partial override (only one field overridden) and assert the merged profile uses project-field for overridden, shipped-field for the rest.
- **Parallel?**: `[P]` with T024, T025.

### Subtask T024 – Kill validation / warning survivors

- **Purpose**: Invalid-profile YAML should emit a `UserWarning` and skip the profile.
- **Steps**:
  1. Already-present test `TestAgentProfileRepositoryExceptions::test_invalid_yaml_skipped_with_warning` is a starting point. Extend to cover the warning-emission count (`warnings.warn` should fire exactly once per invalid file, not per attempted access).
  2. For schema-validation survivors, assert specific field requirements: missing `identity`, missing `boundaries`, malformed `role` enum, etc.
- **Parallel?**: `[P]` with T023, T025.

### Subtask T025 – Kill YAML / frontmatter parsing survivors

- **Purpose**: Underlying YAML parse path mutations.
- **Steps**:
  1. For `ruamel.yaml` parse-error handling — use a fixture with syntactically invalid YAML (`key: : value`) and assert the specific exception type and message substring.
  2. For frontmatter-extraction mutations — test with a file that has `---` delimiters but empty content, vs. no delimiters at all.
- **Parallel?**: `[P]` with T023, T024.

### Subtask T026 – Rescope mutmut, verify ≥ 60 %, append findings residuals

- **Steps**:
  1. `rm -rf mutants/src/doctrine/agent_profiles/*.meta` (recursive — agent_profiles may have multiple source files)
  2. `uv run mutmut run "doctrine.agent_profiles*"` — expect ≥ 60 %.
  3. Append residuals subheading.

## Risks & Mitigations

- **Risk**: YAML loader caches profile objects; tests may see stale data.
  - **Mitigation**: Use fresh `AgentProfileRepository` instance per test; do not share across tests.
- **Risk**: Warning assertions leak from test to test.
  - **Mitigation**: Use `pytest.warns` context manager; never rely on module-level `warnings.filterwarnings` state.

## Review Guidance

- Scoped mutmut score ≥ 60 %.
- Tests do not share `AgentProfileRepository` instances across fixtures.
- `pytest.warns` used for every warning-emission assertion.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T17:23:56Z – claude – shell_pid=2513727 – Started implementation via action command
- 2026-04-20T17:38:16Z – claude – shell_pid=2513727 – 79.5% kill rate (424/533). 127 tests pass. Residuals documented.
- 2026-04-20T17:41:05Z – claude – shell_pid=2524694 – Started review via action command
- 2026-04-20T17:42:22Z – claude – shell_pid=2524694 – Review passed: 79.5% kill rate (424/533), 1104 tests pass, C-008 compliant, pytest.warns used throughout, no shared repo instances
