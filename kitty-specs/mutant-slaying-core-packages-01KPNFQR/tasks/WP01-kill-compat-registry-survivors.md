---
work_package_id: WP01
title: Kill specify_cli.compat.registry validator survivors
dependencies: []
requirement_refs:
- FR-001
- FR-013
- FR-014
- FR-015
- NFR-001
- NFR-003
- NFR-004
- NFR-005
- NFR-006
planning_base_branch: feature/711-mutant-slaying
merge_target_branch: feature/711-mutant-slaying
branch_strategy: Planning artifacts for this feature were generated on feature/711-mutant-slaying. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/711-mutant-slaying unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Narrow-surface foundation
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/specify_cli/compat/
execution_mode: code_change
owned_files:
- tests/specify_cli/compat/test_registry.py
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Kill specify_cli.compat.registry validator survivors

## Objectives & Success Criteria

- Drive mutation score on `specify_cli.compat.registry` from ~0 % (20 survivors out of ~40 tested mutants) to **≥ 80 %**, equivalent to **≤ 4 surviving mutants**.
- Every new test applies one of the named patterns from `src/doctrine/styleguides/shipped/mutation-aware-test-design.styleguide.yaml`. No bespoke assertion styles.
- Commit message lists the killed mutant IDs and names the applied pattern (per FR-013).
- Any accepted-residual mutant is annotated `# pragma: no mutate` with a one-line reason **and** listed in `docs/development/mutation-testing-findings.md` under a new WP01 residuals subheading (per FR-014, FR-015).

## Context & Constraints

- **Spec**: `kitty-specs/mutant-slaying-core-packages-01KPNFQR/spec.md` (FR-001, NFR-001, NFR-003)
- **Plan**: `kitty-specs/mutant-slaying-core-packages-01KPNFQR/plan.md` (Project Structure → `tests/specify_cli/compat/`)
- **Doctrine load-bearing artefacts** (cite the relevant one in every commit):
  - `src/doctrine/tactics/shipped/mutation-testing-workflow.tactic.yaml` — 5-step workflow
  - `src/doctrine/styleguides/shipped/mutation-aware-test-design.styleguide.yaml` — pattern library
  - `src/doctrine/toolguides/shipped/PYTHON_MUTATION_TOOLS.md` — operator-to-strategy map
- **Source under test**: `src/specify_cli/compat/registry.py` (unchanged — do not edit source except for rare `# pragma: no mutate` annotations).
- **Test file**: `tests/specify_cli/compat/test_registry.py` (existing; extend don't replace).
- **Test annotation conventions**: module docstring → `from __future__ import annotations` → isort-grouped imports → `pytestmark = pytest.mark.fast` → helpers → tests. See `spec.md` for full convention list; copy the existing style in this file.

## Branch Strategy

- **Strategy**: lane-per-WP (worktree created on `implement WP01 --agent <name>`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T001 – Kill `_validate_entry` survivors (7 mutants)

- **Purpose**: `_validate_entry` is the per-row validator called by `validate_registry` for each shim entry. 7 surviving mutants across the function indicate that field-presence, type, and value checks are not being distinguished by assertions.
- **Mutant IDs in scope** (from 2026-04-20 baseline):
  - `specify_cli.compat.registry.x__validate_entry__mutmut_7`
  - `…__mutmut_8`
  - `…__mutmut_16`
  - `…__mutmut_34`
  - `…__mutmut_36`
  - `…__mutmut_53`
  - `…__mutmut_54`
- **Steps**:
  1. Inspect each mutant's diff with `uv run mutmut show <id>`. Group by mutation family (comparison flip, identity swap, missing-branch, etc.).
  2. For each family, apply the styleguide pattern:
     - **Comparison flips** (`==` → `!=`, `is` → `is not`) → **Boundary Pair**: test at the exact equality point and one step either side.
     - **Identity-value inputs** on field checks → **Non-Identity Inputs**: do not assert on empty strings alone; use non-default, non-trivial values.
     - **Logical branch mutations** → **Bi-Directional Logic**: one test per operand-configuration (both-present, one-missing each direction, both-missing).
  3. Add tests to `tests/specify_cli/compat/test_registry.py` under a dedicated `class TestValidateEntryMutationKills:` or equivalent grouping. Follow existing function-naming conventions (`test_validate_entry_<field>_<scenario>`).
- **Files**: `tests/specify_cli/compat/test_registry.py` (extend — ~100 new lines expected).
- **Parallel?**: Not with T002–T005 from this WP because commits modify the same file; serialise within the worktree.
- **Notes**: If a mutant turns out to be truly equivalent (e.g., swapping between two logically-identical dict-key lookups), annotate `# pragma: no mutate` on the source line with a one-line rationale. Do not exceed the NFR-003 ceiling (10 % annotation density).

### Subtask T002 – Kill `_validate_canonical_import` survivors (6 mutants)

- **Purpose**: `_validate_canonical_import` enforces dotted-path shape (module.submodule.ClassName). 6 survivors cluster in the path-component validation — likely boundary-flip mutations on component-count checks and regex guards.
- **Mutant IDs in scope**:
  - `…x__validate_canonical_import__mutmut_7` through `__mutmut_12` (6 consecutive IDs).
- **Steps**:
  1. Read the source: validator checks dotted path has ≥ 2 components, each component is a valid Python identifier, last component is a class name.
  2. Apply **Boundary Pair** to each component-count guard: test with exactly 1, exactly 2, exactly 3 components.
  3. Apply **Non-Identity Inputs** to identifier checks: use names with digits, underscores, leading underscores — not just simple `[a-z]+` cases.
  4. Extend existing tests or add new `test_validate_canonical_import_<scenario>` functions.
- **Files**: `tests/specify_cli/compat/test_registry.py`.
- **Parallel?**: `[P]` with T003, T005 (different test groupings in the same file — coordinate merge, but logic is independent).

### Subtask T003 – Kill `_validate_version_order` survivors (2 mutants)

- **Purpose**: `_validate_version_order` ensures `removal_target_release >= added_in_release`. The 2 surviving mutants are likely comparison-operator flips (`>=` → `>` and `<=` → `<`).
- **Mutant IDs in scope**:
  - `…x__validate_version_order__mutmut_10`
  - `…x__validate_version_order__mutmut_12`
- **Steps**:
  1. This is the canonical **Boundary Pair** case from the styleguide. Add three tests:
     - `test_validate_version_order_target_before_added` — strict `<` case.
     - `test_validate_version_order_target_equals_added` — exact equality (the boundary that kills `>=` vs `>`).
     - `test_validate_version_order_target_after_added` — strict `>` case.
  2. Use realistic PEP 440 version strings: `"1.0.0"`, `"1.0.0"`, `"1.0.1"` for the three tests respectively.
  3. Cite the styleguide's Boundary Pair pattern in the commit message.
- **Files**: `tests/specify_cli/compat/test_registry.py`.
- **Parallel?**: `[P]` with T002, T005.

### Subtask T004 – Kill top-level `validate_registry` survivors (3 mutants)

- **Purpose**: `validate_registry` orchestrates per-entry validation and accumulates errors. 3 survivors suggest the error-accumulation loop is under-asserted — tests probably check "an error was raised" rather than "all expected errors were raised".
- **Mutant IDs in scope**:
  - `…x_validate_registry__mutmut_7`
  - `…x_validate_registry__mutmut_11`
  - `…x_validate_registry__mutmut_18`
- **Steps**:
  1. Inspect each diff. If the mutation is `break` → `continue` (or vice versa), apply loop-control coverage: test with a multi-entry registry where both valid and invalid entries exist. Assert the list of errors is exactly the expected subset.
  2. If the mutation is on the initial empty-errors-list construction, assert the return value is an empty list on success (not just "did not raise").
  3. Verify that `RegistrySchemaError` is raised with all accumulated errors on failure — inspect `.errors` attribute, not just the class.
- **Files**: `tests/specify_cli/compat/test_registry.py`.

### Subtask T005 – Kill `load_registry` + `RegistrySchemaError` survivors (2 mutants)

- **Purpose**: `load_registry` wraps YAML parsing + validation. `RegistrySchemaError.__init__` is the custom exception class.
- **Mutant IDs in scope**:
  - `specify_cli.compat.registry.x_load_registry__mutmut_14`
  - `specify_cli.compat.registry.xǁRegistrySchemaErrorǁ__init____mutmut_4`
- **Steps**:
  1. For `load_registry` mutant 14 — inspect diff with `mutmut show`. Likely a fallback-path mutation (empty file handling or default-value substitution). Write a test that exercises the exact branch.
  2. For `RegistrySchemaError.__init__` mutant 4 — the class takes `message` + `errors: list[str]`. Test that constructing with both arguments preserves them faithfully (assert on `.message`, `.errors`, and `str(exception)`).
- **Files**: `tests/specify_cli/compat/test_registry.py`.
- **Parallel?**: `[P]` with T002, T003.

### Subtask T006 – Rescope mutmut, verify, append findings residuals

- **Purpose**: Verify the WP goal is met and publish the durable record.
- **Steps**:
  1. Invalidate the cached mutmut results for compat: `rm /home/stijn/Documents/_code/fork/spec-kitty/mutants/src/specify_cli/compat/*.meta`
  2. Scoped re-run: `uv run mutmut run "specify_cli.compat*"`. Budget: ≤ 15 minutes per NFR-004.
  3. Check results: `uv run mutmut results | grep "specify_cli.compat" | awk -F: '{print $NF}' | sort | uniq -c`. Expect `≤ 4 survived` and the remaining either accepted-equivalent (annotated) or in-scope for a residual list.
  4. Append a new subheading in `docs/development/mutation-testing-findings.md` under the 2026-04-20 snapshot:
     ```
     ### WP01 – compat.registry residuals (YYYY-MM-DD)
     - Kill rate: XX.X % (≥ 80 % target: met / not met)
     - Killed: <N> (IDs: …)
     - Accepted equivalent (≤ 10 % ceiling: met): <N> (IDs: …, reasons: …)
     - Open: <N> (follow-up ticket if any)
     ```
  5. If the score target is not met AND accepted-equivalent density exceeds NFR-003's 10 % ceiling, STOP and raise the issue in the WP's review feedback rather than forcing the merge.
- **Files**: `docs/development/mutation-testing-findings.md` (append only — do not edit the historical snapshot).

## Test Strategy

All work in this WP is itself test authoring. The meta-test is the mutmut scoped re-run in T006, which verifies that the new tests actually distinguish the surviving mutations. Do not add `@pytest.mark.non_sandbox` or `@pytest.mark.flaky` to any of these tests — they are structurally sandbox-compatible (no subprocesses, no whole-codebase walks).

## Risks & Mitigations

- **Risk**: A test appears to kill a mutant but actually passes both the original and the mutated code.
  - **Mitigation**: Always verify with a scoped `mutmut apply <id>` → pytest → confirm failure → `git checkout -- <source>`.
- **Risk**: Over-annotation with `# pragma: no mutate` — crossing the 10 % ceiling (NFR-003).
  - **Mitigation**: For each intended annotation, verify the mutation is truly observationally equivalent (would produce no different output in any realistic caller). If uncertain, write a test instead.
- **Risk**: The test file grows unwieldy (~100+ new tests).
  - **Mitigation**: Use `class Test…MutationKills` groupings per validator function. Parametrize where three or more tests share structure (per the spec's test-annotation conventions).

## Review Guidance

- Verify the commit message cites killed mutant IDs and names the styleguide pattern (FR-013).
- Spot-check three random kills by reading the new test's assertion and mentally re-applying the mutation.
- Confirm `mutmut-testing-findings.md` has the new WP01 residuals subheading (FR-015).
- Reject the PR if the equivalent-mutant density exceeds 10 % (NFR-003) without justification in the review thread.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.

---

### Updating Status

Use `spec-kitty agent tasks move-task WP01 --to <lane>` to move between lanes. This WP starts at `planned`; transitions through `claimed` → `in_progress` → `for_review` → `in_review` → `approved` → `done`.
