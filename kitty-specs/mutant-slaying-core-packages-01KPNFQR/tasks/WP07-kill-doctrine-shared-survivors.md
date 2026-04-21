---
work_package_id: WP07
title: Kill doctrine.shared survivors
dependencies:
- WP04
requirement_refs:
- FR-008
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
- T032
- T033
- T034
- T035
phase: Phase 2 - Doctrine core
agent: "claude"
shell_pid: "2536359"
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/doctrine/
execution_mode: code_change
owned_files:
- tests/doctrine/test_shared.py
- tests/doctrine/shared/**
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Kill doctrine.shared survivors

## Objectives & Success Criteria

- Drive mutation score on `doctrine.shared` to **≥ 60 %** (FR-008, NFR-002). Current baseline: 37 survivors. Fresh re-sample required.
- Closes Phase 2.

## Context & Constraints

- **Source under test**: `src/doctrine/shared/errors.py`, `src/doctrine/shared/exceptions.py`, `src/doctrine/shared/<other helpers>.py`.
- **Test files**: `tests/doctrine/` files matching shared-module patterns.
- **Precondition**: Re-sample `uv run mutmut run "doctrine.shared*"`.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP07 --base WP04`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T032 – Kill `doctrine.shared.errors` class-behaviour survivors

- Error classes have `__init__`, `__str__`, `__repr__` methods with field-assembly mutations.
- Test construction with all argument combinations (required only, all optional, mix).
- Assert `str(exception)` substring includes each argument's value.
- Test equality and hashability where applicable.

### Subtask T033 – Kill `doctrine.shared.exceptions` payload survivors

- `InlineReferenceRejectedError` (from the type-check log earlier) has optional field arguments that each need assertion coverage.
- **Non-Identity Inputs**: pass a non-default value for each optional argument, assert round-trip through `__init__` → attribute access.
- **Parallel?**: `[P]` with T032, T034.

### Subtask T034 – Kill inline-reference-check survivors

- Inline-reference checks validate that doctrine artefacts do not embed unauthorized cross-references.
- **Boundary Pair**: test with a reference to an authorized artefact, to an unauthorized artefact (the rejection case), and to a non-existent artefact (error case).
- **Parallel?**: `[P]` with T032, T033.

### Subtask T035 – Rescope mutmut, verify ≥ 60 %, append findings residuals

- `rm -rf mutants/src/doctrine/shared/*.meta`
- `uv run mutmut run "doctrine.shared*"` → ≥ 60 %.
- Append residuals. **This closes Phase 2** — update the findings doc's Phase 2 summary to note all four doctrine sub-modules passed target.

## Risks & Mitigations

- **Risk**: Shared exceptions may be over-mutated (the class-heavy surface produces many survivors of marginal semantic value).
  - **Mitigation**: After first-pass kills, assess residual composition. If residuals are > 30 % equivalent mutants (e.g., `self.field = value` vs `self.field = (value,)[0]`), annotate liberally but stay under the 10 % annotation ceiling.

## Review Guidance

- Scoped mutmut score ≥ 60 %.
- Phase 2 summary updated in findings doc.
- Annotation density checked against NFR-003 (10 % ceiling).

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T18:00:08Z – claude – shell_pid=2536359 – Started implementation via action command
- 2026-04-20T18:25:46Z – claude – shell_pid=2536359 – Ready for review: 74.6% kill rate (91/122), 1248 tests pass, Phase 2 complete
- 2026-04-20T18:27:36Z – claude – shell_pid=2536359 – Review passed: 74.6% kill rate (91/122), 1248 tests pass, Phase 2 summary in findings doc, no annotation debt
