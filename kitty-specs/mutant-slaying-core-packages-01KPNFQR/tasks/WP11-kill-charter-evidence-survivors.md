---
work_package_id: WP11
title: Kill charter.evidence survivors
dependencies:
- WP07
requirement_refs:
- FR-012
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
- T054
- T055
- T056
- T057
- T058
phase: Phase 3 - Charter core
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/evidence/
execution_mode: code_change
owned_files:
- tests/charter/evidence/**
tags: []
task_type: implement
---

# Work Package Prompt: WP11 – Kill charter.evidence survivors

## Objectives & Success Criteria

- Drive mutation score on `charter.evidence` to **≥ 60 %** (FR-012, NFR-002). Current baseline: 61 survivors. Fresh re-sample required.
- Closes the mission.

## Context & Constraints

- **Source under test**: `src/charter/evidence/` — `code_reader`, `corpus_loader`, `orchestrator`, evidence hashing.
- **Test files**: `tests/charter/evidence/` (including `test_orchestrator.py` which carries `non_sandbox`).
- **Precondition**: Re-sample `uv run mutmut run "charter.evidence*"`.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP11 --base WP07`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T054 – Kill `code_reader` collector survivors

- `CodeReadingCollector` walks source files and extracts evidence signals.
- Test with: empty directory, single-file directory, multi-file directory. Assert evidence count matches.
- Test language detection: Python file, TypeScript file, unknown extension. Each should route correctly.

### Subtask T055 – Kill `corpus_loader` survivors

- `CorpusLoader` builds a `CorpusSnapshot` from a profile directory.
- **Non-Identity Inputs**: use distinct corpus entries in the fixture; assert the snapshot preserves order (or hash, depending on the contract).
- **Parallel?**: `[P]` with T056, T057.

### Subtask T056 – Kill `orchestrator` invariant survivors

- Orchestrator invariants: `inputs_hash` changes when inputs change; `inputs_hash` stable when inputs are semantically identical.
- Test both directions: mutate input → assert hash changes; reconstruct input with same semantic content → assert hash unchanged.
- **Note**: `tests/charter/evidence/test_orchestrator.py` carries `non_sandbox` — new tests added there inherit the marker. Do not remove it.
- **Parallel?**: `[P]` with T055, T057.

### Subtask T057 – Kill hash-computation survivors

- Hash computation may have field-ordering or timestamp-inclusion mutations.
- **Boundary Pair**: assert specific fields ARE in the hash (changing them changes hash) and specific fields are NOT (changing them doesn't change hash — timestamps are often the canonical excluded field).
- **Parallel?**: `[P]` with T055, T056.

### Subtask T058 – Rescope mutmut, verify ≥ 60 %, append findings residuals

- `rm -rf mutants/src/charter/evidence/*.meta`
- `uv run mutmut run "charter.evidence*"` → ≥ 60 %.
- Append residuals. **This closes the mission** — update the findings doc's mission-completion summary with per-phase kill rates and total survivor reduction.

## Risks & Mitigations

- **Risk**: `test_orchestrator.py` already carries `non_sandbox` — new tests there will also be sandbox-skipped.
  - **Mitigation**: That's intended (the original reason was subprocess invocation). New assertion-strength tests that don't subprocess can live in a new `test_orchestrator_unit.py` without the marker, if that produces better coverage.
- **Risk**: Hash-computation tests are order-sensitive (dict iteration order, etc.).
  - **Mitigation**: Use deterministic fixture construction; verify hashes computed repeatedly are stable.

## Review Guidance

- Scoped mutmut score ≥ 60 %.
- Mission-completion summary added to findings doc: per-phase kill rates, total survivor reduction across 11 WPs.
- New unit-level evidence tests (if any) are NOT marked `non_sandbox` unless they truly are.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T18:28:57Z – unknown – Descoped: Phase 3 charter.* modules deferred to future mission
