---
work_package_id: WP10
title: Kill charter.synthesizer survivors
dependencies:
- WP07
requirement_refs:
- FR-010
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
- T047
- T048
- T049
- T050
- T051
- T052
- T053
phase: Phase 3 - Charter core
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/synthesizer/**
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Kill charter.synthesizer survivors

## Objectives & Success Criteria

- Drive mutation score on `charter.synthesizer` to **≥ 60 %** (FR-010, NFR-002). Current baseline: 528 survivors (largest concentration in mission). Fresh re-sample required.
- **Sizing caveat**: this WP is at the maximum recommended size (7 subtasks). T052 assesses residuals and may trigger a follow-up WP.

## Context & Constraints

- **Source under test**: `src/charter/synthesizer/` — the pipeline for generating charter artefacts from evidence. Sub-sub-modules include `evidence`, `neutrality`, `request`, `orchestrator`, `bundle`.
- **Test files**: `tests/charter/synthesizer/` and related `tests/charter/` files (e.g., `tests/charter/evidence/test_orchestrator.py` carries `pytestmark = pytest.mark.non_sandbox` — respect it).
- **Precondition**: Re-sample `uv run mutmut run "charter.synthesizer*"` (likely takes 30+ min; budget accordingly).

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP10 --base WP07`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T047 – Kill `evidence` bundle-hash / corpus-snapshot survivors

- **Non-Identity Inputs** on evidence-hash tests: use distinct bundles that differ in one field, assert hashes differ.
- For corpus-snapshot equality, test with distinct snapshots, assert distinct hashes; test with structurally-equal snapshots from distinct construction paths, assert equal hashes.

### Subtask T048 – Kill `neutrality` lint-gate survivors

- The neutrality lint gate enforces generic-language scoping. Mutations likely around `_is_generic_scoped` checks.
- **Bi-Directional Logic**: test with scoped phrase (accepted), unscoped phrase (rejected), both present (rejected or accepted per rule).
- **Parallel?**: `[P]` with T049–T051.

### Subtask T049 – Kill `request` threading survivors

- `SynthesisRequest` / `SynthesisTarget` carry evidence forward to the synthesizer. Mutations around field-assembly.
- Test construction with each field set independently; assert round-trip via `dataclasses.asdict` or equivalent.
- **Parallel?**: `[P]` with T048, T050, T051.

### Subtask T050 – Kill `orchestrator` pipeline survivors

- Pipeline orchestration glues evidence → neutrality → synthesis.
- Test the short-circuit on neutrality failure (no synthesis attempted).
- Test the full-pipeline success path with minimal evidence.
- **Parallel?**: `[P]` with T048, T049, T051.

### Subtask T051 – Kill `bundle` packaging survivors

- Charter bundle packaging collects artefacts for distribution.
- Test with empty bundle, single-artefact bundle, multi-artefact bundle — assert metadata counts match.
- **Parallel?**: `[P]` with T048, T049, T050.

### Subtask T052 – Assess residual count; decide WP split

- After T047–T051, run scoped mutmut and check residuals.
- **Decision gate**:
  - If residuals > 100: open a follow-up WP (`WP10b-charter-synthesizer-deep-kills`) before merging this one. The follow-up inherits this WP's post-state as its starting point.
  - If residuals 50–100: document them in findings doc; this WP closes as-is at "best-effort".
  - If residuals < 50: proceed to T053.

### Subtask T053 – Rescope mutmut, verify, append findings residuals

- `rm -rf mutants/src/charter/synthesizer/*.meta`
- `uv run mutmut run "charter.synthesizer*"` → ≥ 60 % (or documented residual list per T052 outcome).
- Append residuals subheading; call out the sub-sub-module split explicitly.

## Risks & Mitigations

- **Risk**: Synthesizer has the deepest test dependency graph in the charter package. Changes may break existing tests.
  - **Mitigation**: Run `pytest tests/charter/ -m "not non_sandbox" -x` after every test addition; stop and triage any non-target failure immediately.
- **Risk**: The 15-min per-rerun budget (NFR-004) is tight for the full synthesizer surface.
  - **Mitigation**: Scope reruns per sub-sub-module; accept that the final all-synthesizer run may take 30–45 min and run it at end-of-WP only.
- **Risk**: WP is at max size (7 subtasks) — risk of overwhelming the implementer.
  - **Mitigation**: T052 explicitly allows splitting. Do not feel obligated to kill every survivor in one pass.

## Review Guidance

- Scoped mutmut score ≥ 60 %, OR documented residual list with follow-up WP.
- No regressions in `tests/charter/synthesizer/` other tests.
- `non_sandbox` marker on `test_orchestrator.py` preserved.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T18:28:55Z – unknown – Descoped: Phase 3 charter.* modules deferred to future mission
