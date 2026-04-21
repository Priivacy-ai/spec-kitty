---
work_package_id: WP02
title: Kill kernel._safe_re survivors
dependencies: []
requirement_refs:
- FR-002
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
- T007
- T008
- T009
- T010
phase: Phase 1 - Narrow-surface foundation
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/kernel/
execution_mode: code_change
owned_files:
- tests/kernel/test__safe_re.py
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Kill kernel._safe_re survivors

## Objectives & Success Criteria

- Drive mutation score on `kernel._safe_re` to **≥ 80 %**. Current baseline: 26 surviving mutants. Target: ≤ 5 survivors.
- Every new test applies a named pattern from `mutation-aware-test-design.styleguide.yaml`.
- Commit cites mutant IDs and pattern.
- Residuals annotated inline + appended to findings doc (FR-014, FR-015).

## Context & Constraints

- **Source under test**: `src/kernel/_safe_re.py` — RE2-backed regex wrappers (`compile`, `_re2_compile`, `search`, `match`, `findall`, `finditer`, `fullmatch`, `split`, `sub`, `subn`, `_prepend_flags`).
- **Test file**: `tests/kernel/test__safe_re.py` (if not present, create; follow conventions from sibling `tests/kernel/test_atomic.py`).
- **Why this matters**: `_safe_re` wraps the RE2 engine to enforce linear-time regex (ReDoS prevention). A surviving mutation in a compile-flag assembly or a method dispatcher can silently disable the safety guarantees.
- **Known non-actionable**: `_prepend_flags` has 27 `no tests` entries but 0 survivors — that's a coverage gap, not a mutation-kill target. If addressing that helps (it likely will), add tests for `_prepend_flags` first to avoid deferred coverage later. Count those tests toward the WP's subtask work but do not claim them under FR-002 (they're coverage addition, not kill).

## Branch Strategy

- **Strategy**: lane-per-WP
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T007 – Kill compile / `_re2_compile` survivors

- **Purpose**: Regex compilation is the entry point for every other method. Mutations here cascade.
- **Mutant IDs in scope** (2026-04-20 baseline, ~8 mutants):
  - `kernel._safe_re.x__compile__mutmut_1`
  - `kernel._safe_re.x__re2_compile__mutmut_1`, `__mutmut_8`, `__mutmut_9`, `__mutmut_10`, `__mutmut_11`, `__mutmut_12`, `__mutmut_13`
- **Steps**:
  1. Inspect each diff with `uv run mutmut show <id>`. Common families: flag-value mutations, default-argument substitutions, and fallback-branch removals.
  2. For flag mutations (e.g., `re.IGNORECASE` → `re.MULTILINE`), apply **Non-Identity Inputs**: test with a pattern that matches only under one flag but not the other.
  3. For default-argument mutations, explicitly pass each argument value and assert the compiled-pattern observable behaviour.
  4. For `_re2_compile` fallback branches, use inputs that trigger RE2-incompatible syntax (e.g., backreferences) and assert the fallback path is taken correctly.
- **Files**: `tests/kernel/test__safe_re.py`.

### Subtask T008 – Kill search / match family survivors

- **Purpose**: Search/match dispatchers have ~10 survivors across `search`, `match`, `findall`, `finditer`, `fullmatch`.
- **Mutant IDs in scope** (representative):
  - `kernel._safe_re.x__search__mutmut_1`
  - `kernel._safe_re.x__fullmatch__mutmut_1`, `__mutmut_6`
  - `kernel._safe_re.x__finditer__mutmut_1`, `__mutmut_6`
  - `kernel._safe_re.x__findall__mutmut_1`, `__mutmut_6`
  - (see `uv run mutmut results | grep kernel._safe_re` for the full up-to-date list)
- **Steps**:
  1. Each method is a thin dispatcher over the compiled pattern's method. Mutations are likely argument-ordering, default-value swaps, or return-shape flips.
  2. Apply **Boundary Pair** for position arguments (`pos`, `endpos`): test with boundary positions (start of string, end of string, exact match position).
  3. For `findall` vs `finditer` — test that `findall` returns a list and `finditer` returns an iterator yielding match objects; don't treat them as equivalent.
  4. For `fullmatch` — include the canonical boundary case: a pattern that matches a prefix of the input (should fail fullmatch; should succeed for `match`).
- **Parallel?**: `[P]` with T007 — different test groupings.

### Subtask T009 – Kill split / sub / subn survivors

- **Purpose**: Mutation survivors in modification operations (~8 mutants).
- **Mutant IDs in scope**:
  - `kernel._safe_re.x__split__mutmut_1`, `__mutmut_2`, `__mutmut_6`, `__mutmut_11`
  - `kernel._safe_re.x__sub__mutmut_1`, `__mutmut_2`, `__mutmut_12`
  - `kernel._safe_re.x__subn__mutmut_1`, `__mutmut_2`, `__mutmut_8`, `__mutmut_12`
- **Steps**:
  1. `split`: **Boundary Pair** on `maxsplit` — test with 0, 1, exact-number-of-matches, and one-more.
  2. `sub` / `subn`: **Non-Identity Inputs** on the replacement — use a replacement string that is **different from the match** so mutations that skip the replacement are visible.
  3. `subn` returns a tuple (new_string, count). Assert both elements explicitly; the `count` is where replacement-count mutations hide.
- **Parallel?**: `[P]` with T007, T008.

### Subtask T010 – Rescope mutmut, verify, append findings residuals

- **Purpose**: Close WP02.
- **Steps**:
  1. `rm /home/stijn/Documents/_code/fork/spec-kitty/mutants/src/kernel/_safe_re.py.meta`
  2. `uv run mutmut run "kernel._safe_re*"` (budget ≤ 15 min).
  3. Verify results: `uv run mutmut results | grep kernel._safe_re | awk -F: '{print $NF}' | sort | uniq -c`. Expect `≤ 5 survived`.
  4. Append WP02 residuals subheading to `docs/development/mutation-testing-findings.md`. Same format as WP01.
- **Files**: `docs/development/mutation-testing-findings.md` (append only).

## Test Strategy

The mutmut scoped re-run in T010 is the acceptance test. All added tests are sandbox-compatible; do not introduce `non_sandbox` or `flaky` markers.

## Risks & Mitigations

- **Risk**: RE2 vs Python `re` behavioural divergence (e.g., backreferences) confounds test expectations.
  - **Mitigation**: Use only RE2-supported syntax in test patterns. When testing the fallback path, explicitly assert that Python `re` is called.
- **Risk**: Testing the internal `_re2_compile` helper with private API.
  - **Mitigation**: Import the function name directly; the module exposes it for testing purposes. If the import feels wrong, a public wrapper test may be equivalent.

## Review Guidance

- Verify scoped mutmut score ≥ 80 % on the new run.
- Check that flag-related tests use a pattern that is actually flag-sensitive (not a trivial `"abc"` that matches regardless).
- Confirm no new `non_sandbox` markers added (regex tests should never be sandbox-hostile).

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
