---
work_package_id: WP06
title: Kill doctrine.missions survivors
dependencies:
- WP04
requirement_refs:
- FR-007
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
- T027
- T028
- T029
- T030
- T031
phase: Phase 2 - Doctrine core
agent: "claude"
shell_pid: "2547402"
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/doctrine/
execution_mode: code_change
owned_files:
- tests/doctrine/test_mission_repository.py
- tests/doctrine/test_mission_schema.py
- tests/doctrine/test_mission_step_contracts.py
- tests/doctrine/missions/**
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Kill doctrine.missions survivors

## Objectives & Success Criteria

- Drive mutation score on `doctrine.missions` to **≥ 60 %** (FR-007, NFR-002). Current baseline: 87 survivors. Fresh re-sample required.

## Context & Constraints

- **Source under test**: `src/doctrine/missions/` — mission metadata loading, schema validation, step-contract reference resolution.
- **Test files**: `tests/doctrine/` files matching `test_mission_*.py` patterns.
- **Precondition**: Re-sample `uv run mutmut run "doctrine.missions*"`.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP06 --base WP04`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T027 – Kill schema-validation survivors

- Apply **Boundary Pair** on required-field checks: test with each required field **present**, **absent**, and **empty string**. Survivors around `if not field:` vs `if field is None:` are killed by the empty-string case.
- Apply **Non-Identity Inputs** on schema-version comparisons: use `3.0.0`, `3.0.1`, `3.1.0` — not just `"1"` and `"2"`.

### Subtask T028 – Kill step-contract reference survivors

- Mission YAML references step-contracts by ID. Mutation survivors around reference resolution suggest the reference graph is under-asserted.
- Test with: valid reference (happy path), missing reference (error path), circular reference (if supported — test the detection).
- **Parallel?**: `[P]` with T029, T030.

### Subtask T029 – Kill version / precedence survivors

- Mission schema has version fields. Apply **Boundary Pair** to version comparisons.
- If a precedence rule says "schema version ≥ 3.0.0 required", test with 2.9.9 (fails), 3.0.0 (passes boundary), 3.0.1 (passes).
- **Parallel?**: `[P]` with T028, T030.

### Subtask T030 – Kill error-formatting survivors

- Error message construction often has string-concatenation or f-string-expression mutations.
- Assert substring matches in error messages: `"Mission <slug>: schema version %s is too old (minimum: %s)"` — the `%s` substitution mutants are killed by asserting both the slug AND the version in the error.
- **Parallel?**: `[P]` with T028, T029.

### Subtask T031 – Rescope mutmut, verify ≥ 60 %, append findings residuals

- `rm -rf mutants/src/doctrine/missions/*.meta`
- `uv run mutmut run "doctrine.missions*"` → ≥ 60 %.
- Append residuals.

## Risks & Mitigations

- **Risk**: Mission schema files have many validators; tests may become very parametrized.
  - **Mitigation**: `@pytest.mark.parametrize` is acceptable (and recommended) for schema validation tests where 5+ test cases share structure.

## Review Guidance

- Scoped mutmut score ≥ 60 %.
- Parametrize used for schema-validation tests (≥ 3 structurally-similar cases).
- Error-message assertions use substring matching, not exact equality (prevents brittleness on formatting refactors).

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T17:42:33Z – claude – shell_pid=2525538 – Started implementation via action command
- 2026-04-20T18:00:01Z – claude – shell_pid=2525538 – Ready for review: 75.3% kill rate (290/385), 1181 tests pass, C-008 compliant
- 2026-04-20T18:26:35Z – claude – shell_pid=2547402 – Started review via action command
- 2026-04-20T18:27:35Z – claude – shell_pid=2547402 – Review passed: 75.3% kill rate (290/385), 1248 tests pass, C-008 compliant, value-object contract assertions appropriate
